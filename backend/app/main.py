import sys
import os

# Ensure the backend folder is on the path for imports.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from app.models import Base, engine, get_db, Card, PricePoint
from app.routers import cards, identify
from app.config import HOST, PORT
from app.models import Card
from sqlalchemy.orm import Session
from app.models.database import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Live Comp Overlay Backend", version="0.1.0", lifespan=lifespan)
app.include_router(cards.router)
app.include_router(identify.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/catalog/status")
def catalog_status():
    db = SessionLocal()
    try:
        count = db.query(Card).count()
        has_index = False
        try:
            from app.services import index
            index.load_faiss_index()
            has_index = True
        except Exception:
            pass
        return {
            "cards_in_db": count,
            "faiss_index_ready": has_index,
        }
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
