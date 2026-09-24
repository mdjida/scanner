from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import threading
import socket

from app.models import get_db, Base, engine, Card
from app.services import ingest as ingest_service
from app.services.ingest import PROGRESS
from app.config import PORT

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_lan_ip() -> str:
    """Return the primary non-loopback IPv4 address, falling back to 127.0.0.1."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # This doesn't actually send traffic; it just resolves the interface.
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


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


@router.get("/info")
def admin_info(db: Session = Depends(get_db)):
    """Return details the Android app needs to connect to this backend."""
    ip = _get_lan_ip()
    has_index = False
    try:
        from app.services import index
        index.load_faiss_index()
        has_index = True
    except Exception:
        pass
    return {
        "version": "0.2.0",
        "lan_ip": ip,
        "backend_url": f"http://{ip}:{PORT}",
        "cards_in_db": db.query(Card).count(),
        "faiss_index_ready": has_index,
    }