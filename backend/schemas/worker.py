from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class WorkerStatus(str, Enum):
    idle = "idle"
    busy = "busy"
    offline = "offline"


class WorkerInfo(BaseModel):
    id: str
    gpu: str
    vram_total: int
    vram_used: int
    status: WorkerStatus
    tasks_completed: int
    temperature: Optional[float] = None
    current_task: Optional[str] = None


class GPUStats(BaseModel):
    workers: List[WorkerInfo]
    total_workers: int
    active_workers: int


class WorkersResponse(BaseModel):
    workers: List[WorkerInfo]
