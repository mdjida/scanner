import sys
import os
import socket

# Ensure the backend folder is on the path for imports.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from pathlib import Path

from app.models import Base, engine, get_db, Card, PricePoint
from app.routers import cards, identify, admin
from app.config import HOST, PORT, BASE_DIR
from app.models import Card
from sqlalchemy.orm import Session
from app.models.database import SessionLocal


def _get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup.
    Base.metadata.create_all(bind=engine)

    ip = _get_lan_ip()
    url = f"http://{ip}:{PORT}"
    print("=" * 60)
    print(" Live Comp Overlay backend running")
    print(f"   Health check: {url}/health")
    print(f"   Mobile scan:  {url}/mobile.html")
    print(f"   Admin info:   {url}/admin/info")
    print("=" * 60, flush=True)
    yield


app = FastAPI(title="Live Comp Overlay Backend", version="0.1.0", lifespan=lifespan)

# Allow browsers (including phones on the same Wi-Fi) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cards.router)
app.include_router(identify.router)
app.include_router(admin.router)


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


# Serve known web files explicitly as a catch-all. Must be LAST so API routes
# like /health and /identify are matched first.
WEB_DIR = BASE_DIR.parent / "web"
web_files = {
    "mobile.html", "mobile.js", "mobile.css",
    "pair.html", "mobile-pair.css",
}

@app.get("/{path:path}")
def static_web_fallback(request: Request, path: str):
    file_name = path.split("/")[-1] if path else "index.html"
    if file_name in web_files:
        target = WEB_DIR / file_name
        if target.exists():
            return FileResponse(str(target))
    raise HTTPException(status_code=404, detail="Not Found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
