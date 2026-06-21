"""
Celery application instance.

Configured to use Redis as both broker and result backend
(with separate Redis databases to avoid key collisions).
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

# Use Redis DB 0 for broker, DB 1 for result backend
_broker_url: str = settings.redis_url
_backend_url: str = settings.redis_url.replace("/0", "/1")

celery_app = Celery(
    "news_bot",
    broker=_broker_url,
    backend=_backend_url,
    include=["app.scheduler.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Route tasks to a dedicated queue by default
    task_default_queue="news_bot",
    # Acknowledge tasks after they complete (not before)
    task_acks_late=True,
    # Don't prefetch more than 1 task per worker process
    worker_prefetch_multiplier=1,
    # Persist beat schedule in Redis (survives container restarts/redeploys)
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=_broker_url,
    redbeat_key_prefix="newspulse:beat:",
)

# Register beat schedule
import app.scheduler.beat_schedule  # noqa: E402, F401
