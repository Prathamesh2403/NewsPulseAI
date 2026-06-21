from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from sqlalchemy import select
from app.db.session import SyncSessionLocal
from app.db.models import IngestionRun

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/ingestion/status")
async def get_ingestion_status():
    """Returns the last 5 IngestionRun rows ordered by started_at DESC."""
    with SyncSessionLocal() as session:
        stmt = select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(5)
        runs = session.scalars(stmt).all()
        return [
            {
                "id": run.id,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "status": run.status,
                "new_articles": run.new_articles,
                "community_items": run.community_items,
                "duration_seconds": run.duration_seconds,
            }
            for run in runs
        ]

@router.post("/ingestion/trigger")
async def trigger_ingestion():
    """Manually triggers the ingestion pipeline immediately."""
    from app.scheduler.tasks import run_ingestion_pipeline
    task = run_ingestion_pipeline.delay()
    return {"task_id": task.id, "status": "triggered"}

