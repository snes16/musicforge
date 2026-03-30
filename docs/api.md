# MusicForge REST API Documentation

Base URL: `http://localhost:8000`

Interactive Swagger UI: `http://localhost:8000/docs`

---

## Authentication

Currently no authentication required for local development.
Set `API_SECRET_KEY` in `.env` for production use.

---

## Endpoints

### POST /api/generate

Submit a new music generation request. Returns immediately with a `task_id`.

**Request Body**

```json
{
  "prompt": "indie pop, female vocals, dreamy atmosphere",
  "lyrics": "[verse]\nOptional lyrics\n[chorus]\nChorus text",
  "duration": 60,
  "lora_name": "artist_lora_v1",
  "style_preset": "indie_pop"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | Style description (1–1000 chars) |
| `lyrics` | string | No | Song lyrics with `[verse]`/`[chorus]` tags |
| `duration` | integer | No | Duration in seconds (30–300, default: 60) |
| `lora_name` | string | No | LoRA adapter name. `null` = base model |
| `style_preset` | string | No | Preset ID from `/api/models` |

**Response** `202 Accepted`

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "estimated_seconds": 15,
  "position_in_queue": 1
}
```

---

### GET /api/generate/{task_id}

Poll generation status for a given task.

**Response** `200 OK`

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "audio_url": "/audio/550e8400.wav",
  "duration": 60,
  "metadata": {
    "model": "acestep-v15-turbo",
    "lora": "artist_lora_v1",
    "generation_time": 9.2,
    "gpu": "RTX 5070",
    "prompt": "indie pop, female vocals"
  },
  "created_at": "2026-03-31T12:00:00Z",
  "updated_at": "2026-03-31T12:00:09Z"
}
```

**Status values:**

| Status | Description |
|--------|-------------|
| `queued` | Waiting in queue |
| `processing` | Generation in progress |
| `completed` | Audio ready for download |
| `failed` | Error occurred (see `error` field) |

---

### GET /api/tasks

List all tasks (most recent first).

**Query Parameters**

| Param | Default | Description |
|-------|---------|-------------|
| `limit` | 50 | Max results (1–200) |
| `offset` | 0 | Pagination offset |

**Response** `200 OK`

```json
{
  "tasks": [...],
  "total": 12
}
```

---

### DELETE /api/tasks/{task_id}

Cancel and delete a task. Cannot delete tasks in `processing` state.

**Response** `200 OK`

```json
{"message": "Task abc123 deleted successfully"}
```

---

### GET /api/models

List available LoRA adapters and style presets.

**Response** `200 OK`

```json
{
  "base_model": "acestep-v1.5",
  "loras": [
    {
      "name": "artist_lora_v1",
      "description": "Demo artist LoRA",
      "file_size_mb": 48.5
    }
  ],
  "style_presets": [
    {
      "id": "indie_pop",
      "label": "Indie Pop",
      "prompt_hint": "indie pop, dreamy, lo-fi"
    }
  ]
}
```

---

### GET /api/workers

GPU worker status.

**Response** `200 OK`

```json
{
  "workers": [
    {
      "id": "worker-gpu0",
      "gpu": "RTX 5070",
      "vram_total": 16384,
      "vram_used": 3800,
      "status": "idle",
      "tasks_completed": 42,
      "temperature": 65.0,
      "current_task": null
    }
  ]
}
```

**Worker status values:** `idle` | `busy` | `offline`

---

### GET /health

Health check.

**Response** `200 OK`

```json
{
  "status": "ok",
  "redis": "connected",
  "mock_gpu": true,
  "mock_acestep": true,
  "uptime_seconds": 342.1
}
```

---

### GET /metrics

Platform metrics.

**Response** `200 OK`

```json
{
  "tasks": {
    "queued": 2,
    "processing": 1,
    "completed": 47,
    "failed": 3
  },
  "total_tasks": 53,
  "workers": [...],
  "uptime_seconds": 3600.0
}
```

---

## Serving Audio Files

Generated audio files are served as static files:

```
GET /audio/{task_id}.wav
```

Example: `http://localhost:8000/audio/550e8400-e29b-41d4-a716-446655440000.wav`

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Human readable message"
}
```

Common HTTP status codes:
- `202` — Task accepted
- `400` — Invalid request
- `404` — Task not found
- `409` — Conflict (e.g., deleting a processing task)
- `500` — Internal server error
