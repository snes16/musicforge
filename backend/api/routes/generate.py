from fastapi import APIRouter, HTTPException
from schemas.generate import GenerateRequest, GenerateResponse, TaskStatus
from schemas.task import TaskResult, TaskMetadata, TaskStatusEnum
from core.storage import create_task, get_task, get_queue_position
import sys
import os

router = APIRouter()


def _submit_celery_task(task_id: str, request: GenerateRequest):
    """Submit task to Celery queue."""
    try:
        from celery import Celery
        from config import settings

        app = Celery(broker=settings.redis_url, backend=settings.redis_url)
        app.send_task(
            "worker.tasks.generate_music",
            args=[task_id, request.model_dump()],
            queue="gpu0",
        )
    except Exception as e:
        # Log but don't fail — task is already stored in Redis
        print(f"Warning: could not submit to Celery: {e}", file=sys.stderr)


@router.post("/generate", response_model=GenerateResponse, status_code=202)
async def create_generation(request: GenerateRequest):
    """Submit a new music generation request. Returns task_id immediately."""
    # Persist task
    task = create_task(
        prompt=request.prompt,
        lyrics=request.lyrics,
        duration=request.duration,
        lora_name=request.lora_name,
        style_preset=request.style_preset,
    )
    task_id = task["task_id"]

    # Queue in Celery
    _submit_celery_task(task_id, request)

    position = get_queue_position(task_id)
    estimated = max(10, request.duration // 4)  # rough estimate

    return GenerateResponse(
        task_id=task_id,
        status=TaskStatus.queued,
        estimated_seconds=estimated,
        position_in_queue=position,
    )


@router.get("/generate/{task_id}", response_model=TaskResult)
async def get_generation_status(task_id: str):
    """Poll generation status by task_id."""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    metadata = None
    if task.get("status") == "completed":
        metadata = TaskMetadata(
            model="acestep-v15-turbo",
            lora=task.get("lora_name") or None,
            generation_time=float(task["generation_time"]) if task.get("generation_time") else None,
            gpu=task.get("gpu") or None,
            prompt=task.get("prompt"),
            duration=int(task["duration"]) if task.get("duration") else None,
        )

    return TaskResult(
        task_id=task["task_id"],
        status=TaskStatusEnum(task["status"]),
        progress=int(task.get("progress", 0)),
        audio_url=task.get("audio_url") or None,
        duration=int(task["duration"]) if task.get("duration") else None,
        metadata=metadata,
        error=task.get("error") or None,
        created_at=task.get("created_at"),
        updated_at=task.get("updated_at"),
    )
