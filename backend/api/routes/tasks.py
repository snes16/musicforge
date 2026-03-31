from fastapi import APIRouter, HTTPException, Query
from schemas.task import TaskResult, TaskListResponse, TaskStatusEnum, TaskMetadata
from core.storage import list_tasks, get_task, delete_task, set_cancel_flag, update_task

router = APIRouter()


def _task_dict_to_model(task: dict) -> TaskResult:
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


@router.get("/tasks", response_model=TaskListResponse)
async def list_all_tasks(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all tasks with pagination."""
    tasks = list_tasks(limit=limit, offset=offset)
    return TaskListResponse(
        tasks=[_task_dict_to_model(t) for t in tasks],
        total=len(tasks),
    )


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a queued/processing task or delete a finished one."""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    status = task.get("status")

    if status in ("queued", "processing"):
        # Signal the worker to stop; it will notice on the next poll iteration.
        set_cancel_flag(task_id)
        # Mark immediately so the UI reflects the change without waiting for the
        # next worker poll.
        update_task(task_id, status="cancelled", progress=0)
        return {"message": f"Task {task_id} cancellation requested"}

    deleted = delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete task")

    return {"message": f"Task {task_id} deleted successfully"}
