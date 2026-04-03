# MusicForge REST API Documentation

Base URL: `http://localhost:8000`

Swagger UI: `http://localhost:8000/docs`

## Endpoints

### POST /api/generate
Create an async generation task and return `task_id` immediately.

Request body:

```json
{
  "prompt": "indie pop, female vocals, dreamy atmosphere",
  "lyrics": "[verse]\nLine 1\nLine 2\n\n[chorus]\nHook line\nHook line",
  "duration": 60,
  "lora_name": "artist_lora_v1",
  "style_preset": "indie_pop"
}
```

Field rules:
- `prompt` (required): 1-1000 chars
- `lyrics` (required): 20-5000 chars, must contain `[verse]` and `[chorus]`
- `duration` (optional): 30-300 seconds, default `60`
- `lora_name` (optional): LoRA adapter id
- `style_preset` (optional): preset id from `/api/models`

Response `202`:

```json
{
  "task_id": "uuid",
  "status": "queued",
  "estimated_seconds": 15,
  "position_in_queue": 1
}
```

### GET /api/generate/{task_id}
Poll task status.

Response `200`:

```json
{
  "task_id": "uuid",
  "status": "completed",
  "progress": 100,
  "audio_url": "/audio/uuid.wav",
  "duration": 60,
  "metadata": {
    "model": "acestep-v15-turbo",
    "lora": "artist_lora_v1",
    "generation_time": 3.8,
    "gpu": "RTX 5070 (Mock)",
    "prompt": "indie pop, female vocals",
    "duration": 60
  },
  "error": null,
  "created_at": "2026-04-03T00:36:23.600Z",
  "updated_at": "2026-04-03T00:36:32.318Z"
}
```

Status values:
- `queued`
- `processing`
- `completed`
- `failed`
- `cancelled`

### GET /api/tasks
List tasks with pagination.

Query params:
- `limit` (default `50`, max `200`)
- `offset` (default `0`)

### DELETE /api/tasks/{task_id}
- If task is `queued` or `processing`: marks it as `cancelled`.
- If task is finished (`completed` / `failed` / `cancelled`): removes task record.

### GET /api/models
List base model, LoRA adapters, and style presets.

### GET /api/workers
GPU workers list.

Alias for backward compatibility:
- `GET /workers`

### GET /health
Service health status.

### GET /metrics
Basic task and worker metrics.

## Audio Files
Generated files are served from static endpoint:

- `GET /audio/{task_id}.wav` in mock mode
- `GET /audio/{task_id}.mp3` in real ACE-Step mode (if model output is MP3)

## Typical Errors
- `422` request validation error
- `404` task not found
- `500` internal server error
