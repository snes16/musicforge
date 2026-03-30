# GPU Farm Architecture

## Overview

MusicForge supports horizontal GPU scaling via a Celery-based distributed queue. Each GPU runs its own ACE-Step API instance and Celery worker, all connected through Redis.

---

## Architecture Diagram

```
                    ┌──────────────────────────┐
                    │      FastAPI Gateway      │
                    │      (port 8000)          │
                    │  POST /api/generate       │
                    └────────────┬─────────────┘
                                 │  Enqueue task
                    ┌────────────▼─────────────┐
                    │        Redis Queue        │
                    │     (Celery broker)       │
                    │   redis://redis:6379/0    │
                    └──────┬───────────┬────────┘
                           │           │
              ┌────────────▼───┐   ┌───▼────────────┐
              │  Worker GPU0   │   │  Worker GPU1   │
              │  RTX 5070      │   │  RTX 5060 Ti   │
              │  queue: gpu0   │   │  queue: gpu1   │
              │                │   │                │
              │  ACE-Step      │   │  ACE-Step      │
              │  :8001         │   │  :8002         │
              └────────────────┘   └────────────────┘
```

---

## Components

### FastAPI Gateway (port 8000)

- Receives REST requests from clients
- Stores task metadata in Redis
- Routes tasks to appropriate Celery queues via `GPU Manager`
- Serves audio files as static files from `./audio_output/`

### Redis (port 6379)

- Celery message broker and result backend
- Task metadata storage (`musicforge:task:{id}`)
- Task list index (`musicforge:tasks`)
- TTL: 24 hours per task

### Celery Workers

Each worker:
- Consumes from a dedicated queue (`gpu0`, `gpu1`, ...)
- Calls its own ACE-Step instance via HTTP
- Writes audio output to shared `./audio_output/` volume
- Updates task status in Redis

### ACE-Step Instances

- One per GPU
- Ports: 8001, 8002, ...
- GPU isolation via `CUDA_VISIBLE_DEVICES`

---

## GPU Manager

File: `backend/core/gpu_manager.py`

### Mock Mode (`MOCK_GPU=true`)

Returns fake GPU stats. Used for development without GPU hardware.

```python
from core.gpu_manager import gpu_manager

# Get worker with minimum VRAM usage
worker = gpu_manager.get_available_worker()

# Get all worker stats
workers = gpu_manager.get_all_stats()
```

### Real Mode (`MOCK_GPU=false`)

Uses `nvidia-smi` subprocess to query real GPU stats:

```bash
nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu \
  --format=csv,noheader,nounits
```

---

## Scaling: Adding a New GPU

1. Add a new worker service in `docker-compose.yml`:

```yaml
worker-gpu1:
  build:
    context: ./worker
    dockerfile: Dockerfile
  environment:
    - CUDA_VISIBLE_DEVICES=1
    - REDIS_URL=redis://redis:6379/0
    - ACESTEP_API_URL=http://acestep-gpu1:8002
  command: celery -A tasks worker --loglevel=info -Q gpu1 --concurrency=1
  volumes:
    - ./audio_output:/app/audio_output

acestep-gpu1:
  build:
    context: ./acestep
  ports:
    - "8002:8001"
  environment:
    - CUDA_VISIBLE_DEVICES=1
  volumes:
    - ./checkpoints:/app/checkpoints
    - ./acestep/lora:/app/lora
```

2. Register the new queue in `backend/core/queue.py`:

```python
task_routes={
    "worker.tasks.generate_music_gpu0": {"queue": "gpu0"},
    "worker.tasks.generate_music_gpu1": {"queue": "gpu1"},
}
```

3. Update `gpu_manager.py` to route tasks based on load:

```python
def get_available_worker(self) -> WorkerInfo:
    workers = self.get_all_stats()
    return min(workers, key=lambda w: w.vram_used)
```

---

## Task Lifecycle

```
POST /api/generate
        │
        ▼
[Redis] task.status = "queued"
        │
        ▼
[Celery] generate_music task enqueued → queue: gpu0
        │
        ▼
[Worker] task.status = "processing", progress = 0%
        │
        ▼
[ACE-Step] POST /generate
        │
        ▼
[Worker] Poll ACE-Step status → progress = 50%
        │
        ▼
[ACE-Step] status = "completed"
        │
        ▼
[Worker] Download audio → save to /audio_output/{task_id}.wav
        │
        ▼
[Redis] task.status = "completed", audio_url = "/audio/{task_id}.wav"
        │
        ▼
[Frontend] polls GET /api/generate/{task_id} every 2s
        │
        ▼
[Audio player] loads audio from GET /audio/{task_id}.wav
```

---

## Performance Estimates

| GPU | VRAM | Generation time (60s track) |
|-----|------|------------------------------|
| RTX 5070 | 16 GB | ~8–12 seconds |
| RTX 5060 Ti | 16 GB | ~12–18 seconds |
| RTX 4090 | 24 GB | ~6–8 seconds |
| RTX 3090 | 24 GB | ~15–25 seconds |

---

## Monitoring

- **Flower** (port 5555): Celery task monitor — `http://localhost:5555`
- **GPU Dashboard**: Live VRAM stats at `http://localhost:3000`
- **Health endpoint**: `GET http://localhost:8000/health`
- **Metrics endpoint**: `GET http://localhost:8000/metrics`
