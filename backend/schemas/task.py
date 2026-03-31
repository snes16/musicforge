from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from enum import Enum


class TaskStatusEnum(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaskMetadata(BaseModel):
    model: Optional[str] = "acestep-v15-turbo"
    lora: Optional[str] = None
    generation_time: Optional[float] = None
    gpu: Optional[str] = None
    prompt: Optional[str] = None
    duration: Optional[int] = None


class TaskResult(BaseModel):
    task_id: str
    status: TaskStatusEnum
    progress: int = 0
    audio_url: Optional[str] = None
    duration: Optional[int] = None
    metadata: Optional[TaskMetadata] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskListResponse(BaseModel):
    tasks: List[TaskResult]
    total: int
