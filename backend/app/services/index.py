import numpy as np
import faiss
from pathlib import Path
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from app.config import FAISS_INDEX_PATH
from app.models import Card

_DIMENSION = 512  # CLIP ViT-B/32 produces 512-dim embeddings


def build_faiss_index(db: Session, force: bool = False) -> Tuple[faiss.Index, List[str]]:
    """Build a FAISS index of all card embeddings in the database."""
    if not force and FAISS_INDEX_PATH.exists():
        return load_faiss_index()

    cards = db.query(Card).filter(Card.image_url.isnot(None)).all()
    external_ids = []
    vectors = []

    for card in cards:
        if not card.embedding:
            continue
        external_ids.append(card.external_id)
        vectors.append(np.array(card.embedding, dtype=np.float32))

    if not vectors:
        raise ValueError("No embeddings found. Run ingestion first.")

    matrix = np.vstack(vectors)
    index = faiss.IndexFlatIP(_DIMENSION)  # inner product = cosine similarity on normalized vectors
    index.add(matrix)

    FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FAISS_INDEX_PATH))
    np.save(str(FAISS_INDEX_PATH) + ".ids.npy", np.array(external_ids))

    return index, external_ids


def load_faiss_index() -> Tuple[faiss.Index, List[str]]:
    if not FAISS_INDEX_PATH.exists():
        raise FileNotFoundError(f"FAISS index not found at {FAISS_INDEX_PATH}")
    index = faiss.read_index(str(FAISS_INDEX_PATH))
    ids = np.load(str(FAISS_INDEX_PATH) + ".ids.npy", allow_pickle=True).tolist()
    return index, ids


def search(embedding: np.ndarray, k: int = 5) -> List[Tuple[str, float]]:
    index, ids = load_faiss_index()
    query = np.array([embedding], dtype=np.float32)
    scores, indices = index.search(query, k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(ids):
            continue
        results.append((ids[idx], float(score)))
    return results
