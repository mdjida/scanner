from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import threading

from app.models import get_db
from app.services import ingest as ingest_service
from app.services.ingest import PROGRESS

router = APIRouter(prefix="/admin", tags=["admin"])


def _run_ingest(limit_sets, limit_cards_per_set, from_catalog):
    db = next(get_db())
    try:
        ingest_service.ingest_all(
            db,
            limit_sets=limit_sets,
            limit_cards_per_set=limit_cards_per_set,
            from_catalog=from_catalog,
        )
    finally:
        db.close()


@router.post("/ingest/start")
def start_ingest(
    limit_sets: int = None,
    limit_cards_per_set: int = None,
    from_catalog: bool = True,
):
    if PROGRESS.running:
        raise HTTPException(status_code=409, detail="Ingest already running")

    t = threading.Thread(
        target=_run_ingest,
        kwargs={
            "limit_sets": limit_sets,
            "limit_cards_per_set": limit_cards_per_set,
            "from_catalog": from_catalog,
        },
        daemon=True,
    )
    t.start()
    return {"started": True, "status": PROGRESS.to_dict()}


@router.post("/ingest/stop")
def stop_ingest():
    PROGRESS.cancel_requested = True
    return {"cancel_requested": True, "status": PROGRESS.to_dict()}


@router.get("/ingest/status")
def ingest_status():
    return PROGRESS.to_dict()