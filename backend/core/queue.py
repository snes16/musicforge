from celery import Celery
from config import settings

celery_app = Celery(
    "musicforge",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_routes={
        "worker.tasks.generate_music": {"queue": "gpu0"},
    },
)
