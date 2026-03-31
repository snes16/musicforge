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

TASK_PREFIX = "musicforge:task:"
CANCEL_PREFIX = "musicforge:cancel:"

# Timeout: 20 min (1200 polls × 1 s). ACE-Step can be slow on first run.
POLL_INTERVAL = 1        # seconds between /query_result calls
MAX_POLL_TIME = 1200     # seconds total before giving up

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
    r.set(f"{TASK_PREFIX}{task_id}", json.dumps(task), ex=86400)


def _is_cancelled(task_id: str, r) -> bool:
    return bool(r.get(f"{CANCEL_PREFIX}{task_id}"))


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
        audio_filename = f"{task_id}.wav"
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
            if lora_name:
                payload["lora_name"] = lora_name

            with httpx.Client(base_url=ACESTEP_API_URL, headers=headers, timeout=60.0) as client:
                # 1. Submit
                resp = client.post("/release_task", json=payload)
                resp.raise_for_status()
                acestep_task_id = resp.json().get("task_id")
                logger.info(f"[{task_id}] ACE-Step task_id: {acestep_task_id}")

                # 2. Poll — statuses: 0=pending, 1=success, 2=failed
                deadline = start_time + MAX_POLL_TIME
                poll = 0
                while time.time() < deadline:
                    # Check cancel before AND after sleep so we react within ~1s
                    if _is_cancelled(task_id, r):
                        raise _TaskCancelled()

                    time.sleep(POLL_INTERVAL)
                    poll += 1

                    if _is_cancelled(task_id, r):
                        raise _TaskCancelled()

                    qr = client.post(
                        "/query_result",
                        json={"task_id_list": [acestep_task_id]},
                    )
                    qr.raise_for_status()
                    raw_response = qr.json()
                    items = raw_response.get("data", [])
                    if not items:
                        logger.info(f"[{task_id}] poll={poll} empty data: {raw_response}")
                        continue

                    item = items[0]
                    acestep_status = item.get("status", 0)
                    # Log every poll — need to see the raw value to debug
                    logger.warning(f"[POLL] poll={poll} status={acestep_status!r} type={type(acestep_status).__name__} keys={list(item.keys())} result_preview={str(item.get('result',''))[:200]}")

                    # Asymptotic progress: approaches 98, never reaches it.
                    elapsed = time.time() - start_time
                    half_life = max(duration / 4, 10)
                    progress = int(98 * (1 - 0.5 ** (elapsed / half_life)))
                    _update_task(task_id, r=r, progress=progress)

                    # Accept status 1 (int) or "1" / "success" / "completed" (str)
                    is_success = acestep_status == 1 or str(acestep_status) in ("1", "success", "completed", "done")
                    is_failed  = acestep_status == 2 or str(acestep_status) in ("2", "failed", "error")

                    if is_success:
                        # One last cancel check before we commit to "completed"
                        if _is_cancelled(task_id, r):
                            raise _TaskCancelled()

                        # result is a JSON-encoded string → list of objects
                        raw_result = item.get("result", "")
                        logger.info(f"[{task_id}] status=1 raw result: {raw_result}")
                        try:
                            result_obj = json.loads(raw_result)
                            logger.info(f"[{task_id}] parsed result_obj type={type(result_obj).__name__}: {result_obj}")
                            if isinstance(result_obj, list) and result_obj:
                                remote_path = result_obj[0].get("file", "")
                            elif isinstance(result_obj, dict):
                                remote_path = result_obj.get("file", "")
                            else:
                                remote_path = ""
                        except (ValueError, TypeError) as e:
                            logger.error(f"[{task_id}] failed to parse result: {e!r}, raw={raw_result!r}")
                            remote_path = ""

                        logger.info(f"[{task_id}] remote_path={remote_path!r}")
                        if not remote_path:
                            raise RuntimeError(f"ACE-Step status=1 but could not extract file path. raw_result={raw_result!r}")

                        audio_url = f"{ACESTEP_API_URL.rstrip('/')}{remote_path}"
                        logger.info(f"[{task_id}] Downloading audio from {audio_url}")
                        audio_resp = client.get(audio_url, timeout=120.0)
                        audio_resp.raise_for_status()
                        with open(audio_path, "wb") as f:
                            f.write(audio_resp.content)
                        break

                    elif is_failed:
                        raise RuntimeError(
                            f"ACE-Step generation failed for task {acestep_task_id}"
                        )
                else:
                    raise TimeoutError(
                        f"ACE-Step timed out after {MAX_POLL_TIME // 60} minutes"
                    )

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
