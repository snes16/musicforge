"""
Celery worker tasks for MusicForge.
Handles music generation via ACE-Step API.
"""

import os
import time
import json
import struct
import math
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List
import httpx
import redis as redis_sync
from celery import Celery

logger = logging.getLogger(__name__)

# Configuration from environment
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
ACESTEP_API_URL = os.environ.get("ACESTEP_API_URL", "http://acestep:8001")
ACESTEP_API_KEY = os.environ.get("ACESTEP_API_KEY", "local-dev-key")
AUDIO_OUTPUT_DIR = os.environ.get("AUDIO_OUTPUT_DIR", "/app/audio_output")
MOCK_ACESTEP = os.environ.get("MOCK_ACESTEP", "true").lower() == "true"
ACESTEP_ADAPTER_MAP = os.environ.get("ACESTEP_ADAPTER_MAP", "")
ACESTEP_ADAPTER_DIRS = os.environ.get("ACESTEP_ADAPTER_DIRS", "")
ACESTEP_AUTO_UNLOAD_ON_BASE = os.environ.get("ACESTEP_AUTO_UNLOAD_ON_BASE", "true").lower() == "true"

TASK_PREFIX = "musicforge:task:"
CANCEL_PREFIX = "musicforge:cancel:"

# Timeout: 20 min (1200 polls × 1 s). ACE-Step can be slow on first run.
POLL_INTERVAL = 1        # seconds between /query_result calls
MAX_POLL_TIME = 1200     # seconds total before giving up
# After this many seconds, accept any recently-modified file in cache_dir
# (covers LoRA runs where the file may already exist or have a different name)
PARTIAL_TIMEOUT = int(os.environ.get("PARTIAL_TIMEOUT", "60"))

# Celery app
app = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


def _get_redis():
    return redis_sync.from_url(REDIS_URL, decode_responses=True)


def _update_task(task_id: str, r=None, **kwargs):
    if r is None:
        r = _get_redis()
    raw = r.get(f"{TASK_PREFIX}{task_id}")
    if not raw:
        return
    task = json.loads(raw)
    task.update(kwargs)
    task["updated_at"] = datetime.now(timezone.utc).isoformat()
    r.set(f"{TASK_PREFIX}{task_id}", json.dumps(task), ex=86400)


def _is_cancelled(task_id: str, r) -> bool:
    return bool(r.get(f"{CANCEL_PREFIX}{task_id}"))


def _safe_json_loads(value):
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return None
    try:
        return json.loads(value)
    except Exception:
        return None


def _parse_adapter_map(raw: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for chunk in raw.split(";"):
        item = chunk.strip()
        if not item or "=" not in item:
            continue
        name, path = item.split("=", 1)
        name = name.strip()
        path = path.strip().strip('"').strip("'")
        if name and path:
            mapping[name] = path
    return mapping


def _parse_adapter_dirs(raw: str) -> List[str]:
    dirs: List[str] = []
    for chunk in raw.split(";"):
        path = chunk.strip().strip('"').strip("'")
        if path:
            dirs.append(path)
    return dirs


ADAPTER_PATH_MAP = _parse_adapter_map(ACESTEP_ADAPTER_MAP)
ADAPTER_BASE_DIRS = _parse_adapter_dirs(ACESTEP_ADAPTER_DIRS)


def _looks_like_path(value: str) -> bool:
    if not value:
        return False
    if value.startswith(("/", "\\\\")):
        return True
    if len(value) > 2 and value[1] == ":" and value[2] in ("\\", "/"):
        return True
    return ("/" in value) or ("\\" in value)


def _dedupe_keep_order(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _resolve_adapter_candidates(lora_name: str) -> List[str]:
    key = (lora_name or "").strip()
    if not key:
        return []

    candidates: List[str] = []

    mapped = ADAPTER_PATH_MAP.get(key)
    if mapped:
        candidates.append(mapped)

    if _looks_like_path(key):
        candidates.append(key)

    for base in ADAPTER_BASE_DIRS:
        root = base.rstrip("/\\")
        candidates.append(f"{root}/{key}")
        candidates.append(f"{root}/{key}/lokr_weights.safetensors")
        candidates.append(f"{root}/{key}.safetensors")

    return _dedupe_keep_order(candidates)


def _unwrap_acestep_response(payload):
    if isinstance(payload, dict):
        code = payload.get("code")
        error = payload.get("error")
        if code is not None and int(code) != 200:
            raise RuntimeError(error or f"ACE-Step API returned code={code}")
        if error:
            raise RuntimeError(str(error))
        if "data" in payload:
            return payload["data"]
    return payload


def _acestep_json(client: httpx.Client, method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    return _unwrap_acestep_response(response.json())


def _ensure_base_model(client: httpx.Client, task_id: str):
    try:
        status = _acestep_json(client, "GET", "/v1/lora/status")
    except Exception as exc:
        logger.warning(f"[{task_id}] Could not query LoRA status; assuming base model: {exc}")
        return

    if status.get("lora_loaded"):
        logger.info(f"[{task_id}] Unloading active adapter to run base model")
        _acestep_json(client, "POST", "/v1/lora/unload", json={})


def _ensure_requested_adapter(client: httpx.Client, task_id: str, lora_name: str) -> str:
    requested = (lora_name or "").strip()
    if not requested:
        raise RuntimeError("Requested adapter name is empty")

    status = _acestep_json(client, "GET", "/v1/lora/status")
    loaded = bool(status.get("lora_loaded"))
    active_adapter = status.get("active_adapter")
    use_lora = bool(status.get("use_lora"))

    if loaded and active_adapter == requested:
        if not use_lora:
            _acestep_json(client, "POST", "/v1/lora/toggle", json={"use_lora": True})
        return f"active:{requested}"

    if loaded:
        logger.info(f"[{task_id}] Switching adapter: unloading '{active_adapter}' before '{requested}'")
        _acestep_json(client, "POST", "/v1/lora/unload", json={})

    attempts = _resolve_adapter_candidates(requested)
    if not attempts:
        attempts = [requested]

    errors: List[str] = []
    for candidate in attempts:
        try:
            _acestep_json(
                client,
                "POST",
                "/v1/lora/load",
                json={"lora_path": candidate, "adapter_name": requested},
            )
            _acestep_json(client, "POST", "/v1/lora/toggle", json={"use_lora": True})
            return candidate
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")

    raise RuntimeError(
        f"Failed to load adapter '{requested}'. Tried: {attempts}. Errors: {' | '.join(errors)}"
    )


def _extract_query_audio(query_payload):
    """
    Parse ACE-Step /query_result payload and return:
    - file path/url (if present)
    - normalized stage/status
    """
    parsed = _safe_json_loads(query_payload)
    if isinstance(parsed, list):
        items = parsed
    elif isinstance(parsed, dict):
        data = parsed.get("data")
        if isinstance(data, dict):
            items = [data]
        elif isinstance(data, list):
            items = data
        else:
            items = []
    else:
        return None, None

    last_stage = None

    for item in reversed(items):
        if not isinstance(item, dict):
            continue

        stage = str(item.get("stage") or item.get("status") or "").lower() or None
        if stage:
            last_stage = stage

        direct_file = item.get("file") or item.get("audio_url") or item.get("url")
        if isinstance(direct_file, str) and direct_file.strip():
            return direct_file.strip(), stage

        raw_result = _safe_json_loads(item.get("result"))
        if isinstance(raw_result, dict):
            nested_items = [raw_result]
        elif isinstance(raw_result, list):
            nested_items = raw_result
        else:
            nested_items = []

        for nested in reversed(nested_items):
            if not isinstance(nested, dict):
                continue
            nested_stage = str(nested.get("stage") or nested.get("status") or stage or "").lower() or None
            if nested_stage:
                last_stage = nested_stage

            nested_file = nested.get("file") or nested.get("audio_url") or nested.get("url")
            if isinstance(nested_file, str) and nested_file.strip():
                return nested_file.strip(), nested_stage

    return None, last_stage


def _list_cache_audio(cache_dir: str):
    if not cache_dir or not os.path.isdir(cache_dir):
        return []

    entries = []
    for name in os.listdir(cache_dir):
        if not name.lower().endswith((".mp3", ".wav")):
            continue
        path = os.path.join(cache_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        entries.append((name, mtime))
    return entries


def _pick_cache_candidate(cache_dir: str, files_before: set, submit_time: float, allow_modified_existing: bool):
    entries = _list_cache_audio(cache_dir)
    if not entries:
        return None

    new_entries = [(name, mtime) for name, mtime in entries if name not in files_before]
    if new_entries:
        newest_name = max(new_entries, key=lambda item: item[1])[0]
        return os.path.join(cache_dir, newest_name)

    if allow_modified_existing:
        modified_entries = [(name, mtime) for name, mtime in entries if mtime >= submit_time]
        if modified_entries:
            newest_name = max(modified_entries, key=lambda item: item[1])[0]
            return os.path.join(cache_dir, newest_name)

    return None


def _write_mock_wav(dest_path: str, duration_seconds: int = 5, sample_rate: int = 44100):
    """Write a simple sine-wave WAV for mock/dev testing."""
    num_samples = sample_rate * duration_seconds
    num_channels = 2
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align
    chunk_size = 36 + data_size

    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)

    with open(dest_path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", chunk_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 1))
        f.write(struct.pack("<H", num_channels))
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", byte_rate))
        f.write(struct.pack("<H", block_align))
        f.write(struct.pack("<H", bits_per_sample))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        for i in range(num_samples):
            val = int(32767 * 0.3 * math.sin(2 * math.pi * 440 * i / sample_rate))
            sample = struct.pack("<h", val)
            f.write(sample * num_channels)


class _TaskCancelled(Exception):
    pass


@app.task(bind=True, name="worker.tasks.generate_music", max_retries=3)
def generate_music(self, task_id: str, request: dict):
    """
    Main generation task.

    Steps:
    1. Update status → processing, progress=0
    2. Submit to ACE-Step via POST /release_task (or mock)
    3. Poll POST /query_result every POLL_INTERVAL seconds
       — checks cancel flag on each iteration
    4. Download audio, save locally
    5. Update status → completed, progress=100
    """
    start_time = time.time()
    logger.info(f"[{task_id}] Starting music generation: {request.get('prompt', '')[:60]}")

    r = _get_redis()  # reuse one connection throughout the task

    try:
        _update_task(task_id, r=r, status="processing", progress=0)

        prompt = request.get("prompt", "")
        lyrics = request.get("lyrics", "")
        duration = int(request.get("duration", 60))
        lora_name = request.get("lora_name", "")

        os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
        audio_extension = "wav" if MOCK_ACESTEP else "mp3"
        audio_filename = f"{task_id}.{audio_extension}"
        audio_path = os.path.join(AUDIO_OUTPUT_DIR, audio_filename)

        if MOCK_ACESTEP:
            logger.info(f"[{task_id}] Mock mode: simulating generation...")
            steps = [(1, 25), (1, 50), (1, 75)]
            for sleep_s, prog in steps:
                if _is_cancelled(task_id, r):
                    raise _TaskCancelled()
                time.sleep(sleep_s)
                _update_task(task_id, r=r, progress=prog)

            if _is_cancelled(task_id, r):
                raise _TaskCancelled()

            mock_dur = min(duration, 10)
            _write_mock_wav(audio_path, duration_seconds=mock_dur)
            _update_task(task_id, r=r, progress=90)

        else:
            # Real ACE-Step API (v1.5)
            headers = {"Authorization": f"Bearer {ACESTEP_API_KEY}"}
            payload: dict = {"prompt": prompt, "duration": duration}
            if lyrics:
                payload["lyrics"] = lyrics

            with httpx.Client(base_url=ACESTEP_API_URL, headers=headers, timeout=300.0) as client:
                if lora_name:
                    loaded_from = _ensure_requested_adapter(client, task_id, lora_name)
                    logger.info(f"[{task_id}] Using adapter '{lora_name}' from '{loaded_from}'")
                elif ACESTEP_AUTO_UNLOAD_ON_BASE:
                    _ensure_base_model(client, task_id)

                # 1. Submit — response: {"data": {"task_id": "...", "status": "queued"}, "code": 200}
                data_obj = _acestep_json(client, "POST", "/release_task", json=payload)
                acestep_task_id = data_obj.get("task_id")
                logger.warning(f"[{task_id}] ACE-Step task_id: {acestep_task_id}")
                if not acestep_task_id:
                    raise RuntimeError(f"No task_id in /release_task response: {data_obj}")

                # 2. Track completion via two sources:
                # - mounted ACE-Step cache dir (new/updated artifacts)
                # - /query_result parsing (best-effort API signal)
                cache_dir = os.environ.get("ACESTEP_CACHE_DIR", "")
                submit_time = time.time()

                # Snapshot existing files before we start waiting
                files_before = {name for name, _ in _list_cache_audio(cache_dir)}
                logger.info(f"[{task_id}] cache_dir={cache_dir!r} files_before={len(files_before)}")

                deadline = start_time + MAX_POLL_TIME
                poll = 0
                found_file = None

                while time.time() < deadline:
                    if _is_cancelled(task_id, r):
                        raise _TaskCancelled()

                    time.sleep(POLL_INTERVAL)
                    poll += 1

                    if _is_cancelled(task_id, r):
                        raise _TaskCancelled()

                    # Asymptotic progress capped below 100 until artifact is confirmed.
                    elapsed = time.time() - start_time
                    half_life = max(duration / 4, 10)
                    progress = min(97, int(98 * (1 - 0.5 ** (elapsed / half_life))))
                    _update_task(task_id, r=r, progress=progress)

                    # 2a) Check filesystem for new or recently-updated output files.
                    if cache_dir and os.path.isdir(cache_dir):
                        allow_modified_existing = (time.time() - submit_time) >= PARTIAL_TIMEOUT
                        cache_candidate = _pick_cache_candidate(
                            cache_dir=cache_dir,
                            files_before=files_before,
                            submit_time=submit_time,
                            allow_modified_existing=allow_modified_existing,
                        )
                        if cache_candidate:
                            found_file = cache_candidate
                            logger.warning(f"[{task_id}] Cache file detected: {found_file}")
                            break
                    elif poll % 30 == 1:
                        logger.warning(f"[{task_id}] poll={poll} cache_dir is not mounted")

                    # 2b) Query ACE-Step status each loop (best-effort; API can be inconsistent).
                    try:
                        qr_data = _acestep_json(client, "POST", "/query_result", json={"task_id_list": [acestep_task_id]})
                        query_file, query_stage = _extract_query_audio(qr_data)
                        if query_file:
                            found_file = query_file
                            logger.warning(
                                f"[{task_id}] /query_result resolved output: stage={query_stage!r} file={query_file!r}"
                            )
                            break
                        if poll % 30 == 1:
                            logger.info(f"[{task_id}] poll={poll} waiting for output, stage={query_stage!r}")
                    except Exception as e:
                        if poll % 30 == 1:
                            logger.warning(f"[{task_id}] /query_result error: {e}")
                else:
                    raise TimeoutError(f"ACE-Step timed out after {MAX_POLL_TIME // 60} minutes")

                if _is_cancelled(task_id, r):
                    raise _TaskCancelled()

                if not found_file:
                    raise RuntimeError("Generation finished but no output file found")

                # If API returned only filename, resolve it against mounted cache dir.
                if isinstance(found_file, str) and cache_dir and os.path.isdir(cache_dir):
                    if not os.path.isabs(found_file) and not found_file.startswith(("http://", "https://", "/")):
                        cache_path = os.path.join(cache_dir, found_file)
                        if os.path.isfile(cache_path):
                            found_file = cache_path

                # Copy file to audio_output (or download if it's a URL path)
                if os.path.isfile(str(found_file)):
                    import shutil
                    shutil.copy2(found_file, audio_path)
                    logger.info(f"[{task_id}] Copied {found_file} → {audio_path}")
                else:
                    found_file_str = str(found_file)
                    if found_file_str.startswith(("http://", "https://")):
                        audio_url = found_file_str
                    elif found_file_str.startswith("/"):
                        audio_url = f"{ACESTEP_API_URL.rstrip('/')}{found_file_str}"
                    else:
                        audio_url = f"{ACESTEP_API_URL.rstrip('/')}/{found_file_str.lstrip('/')}"
                    logger.info(f"[{task_id}] Downloading {audio_url}")
                    audio_resp = client.get(audio_url, timeout=120.0)
                    audio_resp.raise_for_status()
                    with open(audio_path, "wb") as f:
                        f.write(audio_resp.content)

        generation_time = round(time.time() - start_time, 2)

        _update_task(
            task_id,
            r=r,
            status="completed",
            progress=100,
            audio_url=f"/audio/{audio_filename}",
            generation_time=str(generation_time),
            gpu="RTX 5070 (Mock)" if MOCK_ACESTEP else "GPU",
        )

        logger.info(f"[{task_id}] Completed in {generation_time}s. Audio: {audio_path}")
        return {"task_id": task_id, "status": "completed", "audio_url": f"/audio/{audio_filename}"}

    except _TaskCancelled:
        logger.info(f"[{task_id}] Cancelled by user request")
        _update_task(task_id, r=r, status="cancelled", progress=0)
        # Don't retry cancellations
        return {"task_id": task_id, "status": "cancelled"}

    except Exception as exc:
        logger.exception(f"[{task_id}] Generation failed: {exc}")
        _update_task(task_id, r=r, status="failed", progress=0, error=str(exc))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5)
        raise
