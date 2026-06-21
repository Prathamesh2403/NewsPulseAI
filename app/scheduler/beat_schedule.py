"""
Celery Beat periodic schedule configuration.

Registers the ingestion pipeline to run twice daily (midnight + noon UTC).
Uses crontab for production-grade scheduling. The schedule is persisted in
Redis via redbeat so state survives container restarts and redeploys.
"""

from celery.schedules import crontab

from app.scheduler.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "run-ingestion-pipeline": {
        "task": "app.scheduler.tasks.run_ingestion_pipeline",
        "schedule": crontab(minute=0, hour="0,12"),  # midnight + noon UTC
        "options": {"queue": "news_bot"},
    },
}
