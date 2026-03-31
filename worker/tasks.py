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


def _update_task(task_id: str, **kwargs):
    r = _get_redis()
    raw = r.get(f"{TASK_PREFIX}{task_id}")
    if not raw:
        return
    task = json.loads(raw)
    task.update(kwargs)
    r.set(f"{TASK_PREFIX}{task_id}", json.dumps(task), ex=86400)


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


@app.task(bind=True, name="worker.tasks.generate_music", max_retries=3)
def generate_music(self, task_id: str, request: dict):
    """
    Main generation task.

    Steps:
    1. Update status → processing, progress=0
    2. Call ACE-Step API or mock
    3. Poll/wait for completion, update progress=50
    4. Save audio file
    5. Update status → completed, progress=100
    """
    start_time = time.time()
    logger.info(f"[{task_id}] Starting music generation: {request.get('prompt', '')[:60]}")

    try:
        _update_task(task_id, status="processing", progress=0)

        prompt = request.get("prompt", "")
        lyrics = request.get("lyrics", "")
        duration = int(request.get("duration", 60))
        lora_name = request.get("lora_name", "")
        style_preset = request.get("style_preset", "")  # kept for backward compat, not sent to ACE-Step v1.5

        os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
        audio_filename = f"{task_id}.wav"
        audio_path = os.path.join(AUDIO_OUTPUT_DIR, audio_filename)

        if MOCK_ACESTEP:
            # Simulate generation with sleep
            logger.info(f"[{task_id}] Mock mode: simulating generation...")
            time.sleep(2)
            _update_task(task_id, progress=25)
            time.sleep(2)
            _update_task(task_id, progress=50)
            time.sleep(2)
            _update_task(task_id, progress=75)

            mock_dur = min(duration, 10)  # mock: generate short file
            _write_mock_wav(audio_path, duration_seconds=mock_dur)
            _update_task(task_id, progress=90)

        else:
            # Real ACE-Step API (v1.5 endpoints)
            headers = {"Authorization": f"Bearer {ACESTEP_API_KEY}"}
            payload = {"prompt": prompt, "duration": duration}
            if lyrics:
                payload["lyrics"] = lyrics
            if lora_name:
                payload["lora_name"] = lora_name

            with httpx.Client(base_url=ACESTEP_API_URL, headers=headers, timeout=300.0) as client:
                # 1. Submit task
                resp = client.post("/release_task", json=payload)
                resp.raise_for_status()
                acestep_task_id = resp.json().get("task_id")
                logger.info(f"[{task_id}] ACE-Step task_id: {acestep_task_id}")

                # 2. Poll via /query_result
                # statuses: 0=pending, 1=success, 2=failed
                max_polls = 180  # 6 minutes at 2s interval
                for poll in range(max_polls):
                    time.sleep(2)
                    qr = client.post("/query_result", json={"task_id_list": [acestep_task_id]})
                    qr.raise_for_status()
                    items = qr.json().get("data", [])
                    if not items:
                        continue

                    item = items[0]
                    acestep_status = item.get("status", 0)

                    progress = min(90, int((poll / max_polls) * 90))
                    _update_task(task_id, progress=progress)

                    if acestep_status == 1:
                        # result is a JSON-encoded string; parse twice to get list
                        try:
                            result_obj = json.loads(item.get("result", "[]"))
                            if isinstance(result_obj, list) and result_obj:
                                remote_path = result_obj[0].get("file", "")
                            elif isinstance(result_obj, dict):
                                remote_path = result_obj.get("file", "")
                            else:
                                remote_path = ""
                        except (ValueError, TypeError):
                            remote_path = ""

                        # remote_path looks like "/v1/audio?path=..." — use full URL
                        audio_url = f"{ACESTEP_API_URL.rstrip('/')}{remote_path}"
                        logger.info(f"[{task_id}] Downloading audio from {audio_url}")
                        audio_resp = client.get(audio_url)
                        audio_resp.raise_for_status()
                        os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
                        with open(audio_path, "wb") as f:
                            f.write(audio_resp.content)
                        break
                    elif acestep_status == 2:
                        raise RuntimeError(f"ACE-Step generation failed for task {acestep_task_id}")
                else:
                    raise TimeoutError("ACE-Step generation timed out after 6 minutes")

        generation_time = round(time.time() - start_time, 2)

        _update_task(
            task_id,
            status="completed",
            progress=100,
            audio_url=f"/audio/{audio_filename}",
            generation_time=str(generation_time),
            gpu="RTX 5070 (Mock)" if MOCK_ACESTEP else "GPU",
        )

        logger.info(f"[{task_id}] Completed in {generation_time}s. Audio: {audio_path}")
        return {"task_id": task_id, "status": "completed", "audio_url": f"/audio/{audio_filename}"}

    except Exception as exc:
        logger.exception(f"[{task_id}] Generation failed: {exc}")
        _update_task(task_id, status="failed", progress=0, error=str(exc))
        raise self.retry(exc=exc, countdown=5) if self.request.retries < self.max_retries else exc
