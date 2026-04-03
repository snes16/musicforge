import time
from fastapi import APIRouter
from core.gpu_manager import gpu_manager
from core.storage import list_tasks, get_redis
from config import settings

router = APIRouter()

_start_time = time.time()


@router.get("/health")
async def health_check():
    """Service health check."""
    redis_ok = False
    try:
        r = get_redis()
        r.ping()
        redis_ok = True
    except Exception:
        pass

    return {
        "status": "ok",
        "redis": "connected" if redis_ok else "disconnected",
        "mock_gpu": settings.mock_gpu,
        "mock_acestep": settings.mock_acestep,
        "uptime_seconds": round(time.time() - _start_time, 1),
    }


@router.get("/metrics")
async def get_metrics():
    """Basic platform metrics."""
    tasks = list_tasks(limit=1000)
    status_counts: dict = {"queued": 0, "processing": 0, "completed": 0, "failed": 0}
    for t in tasks:
        s = t.get("status", "unknown")
        if s in status_counts:
            status_counts[s] += 1

    workers = gpu_manager.get_all_stats()
    worker_stats = [
        {
            "id": w.id,
            "gpu": w.gpu,
            "status": w.status,
            "vram_used": w.vram_used,
            "vram_total": w.vram_total,
        }
        for w in workers
    ]

    return {
        "tasks": status_counts,
        "total_tasks": len(tasks),
        "workers": worker_stats,
        "uptime_seconds": round(time.time() - _start_time, 1),
    }


@router.get("/workers")
@router.get("/api/workers")
async def get_workers():
    """Get current GPU worker status."""
    workers = gpu_manager.get_all_stats()
    return {"workers": [w.model_dump() for w in workers]}
