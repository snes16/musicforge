import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import redis as redis_sync
from config import settings


# Use Redis as the primary store for task metadata (fast, already a dep)
_redis_client: Optional[redis_sync.Redis] = None

TASK_PREFIX = "musicforge:task:"
TASK_LIST_KEY = "musicforge:tasks"


def get_redis() -> redis_sync.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_sync.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def create_task(
    prompt: str,
    lyrics: Optional[str],
    duration: int,
    lora_name: Optional[str],
    style_preset: Optional[str],
) -> Dict[str, Any]:
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    task = {
        "task_id": task_id,
        "status": "queued",
        "progress": 0,
        "prompt": prompt,
        "lyrics": lyrics or "",
        "duration": duration,
        "lora_name": lora_name or "",
        "style_preset": style_preset or "",
        "audio_url": "",
        "error": "",
        "created_at": now,
        "updated_at": now,
        "generation_time": "",
        "gpu": "",
    }
    r = get_redis()
    r.set(f"{TASK_PREFIX}{task_id}", json.dumps(task), ex=86400)  # 24h TTL
    r.lpush(TASK_LIST_KEY, task_id)
    r.ltrim(TASK_LIST_KEY, 0, 999)  # keep last 1000 tasks
    return task


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    r = get_redis()
    raw = r.get(f"{TASK_PREFIX}{task_id}")
    if not raw:
        return None
    return json.loads(raw)


def update_task(task_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    r = get_redis()
    task = get_task(task_id)
    if task is None:
        return None
    task.update(kwargs)
    task["updated_at"] = datetime.now(timezone.utc).isoformat()
    r.set(f"{TASK_PREFIX}{task_id}", json.dumps(task), ex=86400)
    return task


def delete_task(task_id: str) -> bool:
    r = get_redis()
    deleted = r.delete(f"{TASK_PREFIX}{task_id}")
    r.lrem(TASK_LIST_KEY, 0, task_id)
    return deleted > 0


def list_tasks(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    r = get_redis()
    task_ids = r.lrange(TASK_LIST_KEY, offset, offset + limit - 1)
    tasks = []
    for tid in task_ids:
        t = get_task(tid)
        if t:
            tasks.append(t)
    return tasks


def get_queue_position(task_id: str) -> int:
    r = get_redis()
    task_ids = r.lrange(TASK_LIST_KEY, 0, -1)
    queued = []
    for tid in task_ids:
        t = get_task(tid)
        if t and t.get("status") == "queued":
            queued.append(tid)
    try:
        return queued.index(task_id) + 1
    except ValueError:
        return 0


def save_audio_file(task_id: str, audio_bytes: bytes, extension: str = "wav") -> str:
    output_dir = settings.audio_output_dir
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{task_id}.{extension}"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "wb") as f:
        f.write(audio_bytes)
    return f"/audio/{filename}"
