import io
import re
from typing import List, Optional, Tuple

from PIL import Image
from sqlalchemy.orm import Session

from app.models import Card
from app.services import embeddings, index, ocr
from app.services.textmatcher import (
    match_name_fuzzy,
    normalize,
    extract_card_name_candidates,
    match_collector_split,
)
from app.services import identify_merge

CONFIDENCE_LABELS = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "uncertain": "uncertain",
}


def identify_image(
    image_bytes: bytes,
    db: Session,
    k: int = 8,
    min_score: float = 0.0,
    use_ocr: bool = True,
    prefer_visual: bool = False,
) -> dict:
    """Identify a card from raw image bytes using CLIP + OCR + text matching.

    Returns a dict matching the API response shape:
      {best_match, candidates, confidence, verified_by, collector, ocr_name}
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # 1) Fast CLIP path.
    query_embedding = embeddings.embed_image_pil(image)
    visual_matches = index.search(query_embedding, k=max(k, 4))  # (external_id, score)

    visual = []
    for external_id, score in visual_matches:
        card = db.query(Card).filter(Card.external_id == external_id).first()
        if card:
            visual.append((card, float(score)))

    # 2) OCR + text path (expensive; only when requested or when visual is ambiguous).
    result = {
        "best_match": None,
        "candidates": [],
        "confidence": "medium",
        "verified_by": [],
        "collector": None,
        "ocr_name": None,
    }

    ocr_lines: list = []
    text_external_ids: List[str] = []
    text_score_map: dict = {}
    collector: Optional[str] = None
    ocr_name: Optional[str] = None

    if use_ocr and ocr.available():
        try:
            ocr_lines = ocr.ocr_text_lines(image)
        except Exception as e:
            print(f"  OCR failed: {e}")
            ocr_lines = []

        name_cands = extract_card_name_candidates(ocr_lines)
        best_name_score = 0.0
        for tok, _sc in name_cands[:6]:
            matches = match_name_fuzzy(tok, db, limit=6)
            if not matches:
                continue
            top_score = max(sc for _, sc in matches)
            if top_score > best_name_score:
                best_name_score = top_score
                ocr_name = tok
                text_external_ids = [ext for ext, sc in matches if sc >= 68]
                text_score_map = {ext: max(text_score_map.get(ext, 0.0), sc) for ext, sc in matches if sc >= 68}
        if best_name_score <= 0:
            ocr_name = None

        for _txt, _c, _bbox, _region in ocr_lines:
            collector = ocr.find_collector(_txt)
            if collector:
                break

    # 3) Merge textual + visual evidence.
    collector_aligned, collector_possible = [], []
    if collector:
        collector_aligned, collector_possible = match_collector_split(collector, None, db)

    if text_external_ids or collector_aligned or collector_possible:
        merged = identify_merge.merge(
            db=db,
            text_external_ids=text_external_ids,
            text_score_map=text_score_map,
            collector_aligned_ids=collector_aligned,
            collector_possible_ids=collector_possible,
            card_name=ocr_name,
            visual=visual,
            prefer_visual=prefer_visual,
        )
        if merged:
            result["best_match"] = merged["best"]
            result["candidates"] = merged["candidates"]
            result["confidence"] = merged["confidence"]
            result["verified_by"] = merged["verified_by"]
            result["collector"] = collector
            result["ocr_name"] = ocr_name
            return result

    # 4) Fall back to pure visual.
    if visual:
        best, best_score = visual[0]
        result["best_match"] = {"card": best, "score": best_score}
        result["candidates"] = [{"card": card, "score": score} for card, score in visual[1:k]]
        result["confidence"] = _visual_confidence(best_score, visual)
        result["collector"] = collector
        result["ocr_name"] = ocr_name
        result["verified_by"] = ["visual"]
        return result

    return result


def _visual_confidence(best_score: float, visual: List[Tuple[Card, float]]) -> str:
    if not visual:
        return "uncertain"
    if best_score >= 0.93:
        return "high"
    if best_score >= 0.86:
        return "medium"
    if best_score >= 0.78:
        return "low"
    return "uncertain"