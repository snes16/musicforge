from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class TaskStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000, description="Music style description")
    lyrics: Optional[str] = Field(None, max_length=5000, description="Optional song lyrics")
    duration: int = Field(60, ge=30, le=300, description="Duration in seconds")
    lora_name: Optional[str] = Field(None, description="LoRA adapter name, null = base model")
    style_preset: Optional[str] = Field(None, description="Style preset name")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "indie pop, female vocals, dreamy atmosphere",
                "lyrics": "[verse]\nOptional lyrics here\n[chorus]\nChorus text",
                "duration": 60,
                "lora_name": "artist_lora_v1",
                "style_preset": "indie_pop"
            }
        }
    }


class GenerateResponse(BaseModel):
    task_id: str
    status: TaskStatus
    estimated_seconds: int
    position_in_queue: int
