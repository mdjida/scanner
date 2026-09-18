from typing import List, Tuple
import numpy as np
from sqlalchemy.orm import Session
from app.models import Card
from app.services import embeddings, index


def identify_image(image_bytes: bytes, db: Session, k: int = 5, min_score: float = 0.85) -> List[Tuple[Card, float]]:
    """
    Identify a card from raw image bytes.
    Returns ranked list of (Card, similarity_score).
    Score is cosine similarity (0-1, higher is better).
    """
    query_embedding = embeddings.embed_image(image_bytes)
    matches = index.search(query_embedding, k=k)

    results = []
    for external_id, score in matches:
        card = db.query(Card).filter(Card.external_id == external_id).first()
        if not card:
            continue
        results.append((card, score))

    return results


def format_candidates(results: List[Tuple[Card, float]]) -> dict:
    """Group candidates into 'high confidence' (>= min_score) and 'possible matches'."""
    if not results:
        return {"best_match": None, "candidates": []}

    best_score = results[0][1]
    best_match = results[0][0]

    candidates = [
        {
            "external_id": card.external_id,
            "name": card.name,
            "set_code": card.set_code,
            "set_name": card.set_name,
            "local_id": card.local_id,
            "variant": card.variant,
            "score": score,
        }
        for card, score in results
    ]

    return {
        "best_match": {
            "external_id": best_match.external_id,
            "name": best_match.name,
            "set_code": best_match.set_code,
            "set_name": best_match.set_name,
            "local_id": best_match.local_id,
            "variant": best_match.variant,
            "score": best_score,
        },
        "candidates": candidates,
    }
