"""
Celery Beat periodic schedule configuration.

Registers the ingestion pipeline to run at the interval specified by
``settings.ingestion_interval_hours`` (default: every 3 hours).
"""

from celery.schedules import crontab

from app.core.config import get_settings
from app.scheduler.celery_app import celery_app

settings = get_settings()

celery_app.conf.beat_schedule = {
    "run-ingestion-pipeline": {
        "task": "app.scheduler.tasks.run_ingestion_pipeline",
        "schedule": 120.0,  # 120 seconds = 2 minutes (testing only)
        "options": {"queue": "news_bot"},
    },
}
