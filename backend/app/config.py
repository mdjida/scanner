import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'livecompoverlay.db'}")
FAISS_INDEX_PATH = Path(os.getenv("FAISS_INDEX_PATH", str(BASE_DIR / "faiss.index")))
TCGDEX_LANGUAGE = os.getenv("TCGDEX_LANGUAGE", "en")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/clip-vit-base-patch32")
