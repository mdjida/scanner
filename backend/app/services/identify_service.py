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
    classify_query_type,
    QueryType,
)
from app.services.identify_merge import MergeContext
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
    collector_candidates: List[str] = []
    collector: Optional[str] = None
    ocr_name: Optional[str] = None

    if use_ocr and ocr.available():
        try:
            ocr_lines = ocr.ocr_text_lines(image)
        except Exception as e:
            print(f"  OCR failed: {e}")
            ocr_lines = []

        # Sparse reads (e.g. Basic Energy cards) miss the title and collector
        # lines entirely; run a second pass on enlarged top/bottom bands.
        if len(ocr_lines) < 4:
            try:
                ocr_lines += ocr.ocr_crop_pass(image, "top")
                ocr_lines += ocr.ocr_crop_pass(image, "bottom")
            except Exception as e:
                print(f"  sparse OCR failed: {e}")

        # On low-RAM machines, unload the ONNX OCR session after each scan so
        # multiple back-to-back scans from a phone don't OOM the PC. The next
        # scan will reload it (~1-2s).
        if os.getenv("LCO_UNLOAD_OCR_AFTER_SCAN", "1") == "1":
            try:
                ocr._reset_engine()
            except Exception as e:
                print(f"  OCR unload failed: {e}")

        name_cands = extract_card_name_candidates(ocr_lines)
        query_type = classify_query_type(None, ocr_lines)
        top_tokens = [tok for tok, _sc in name_cands[:3]]
        text_score_map: dict = {}
        best_name_score = 0.0
        for tok in top_tokens:
            matches = match_name_fuzzy(tok, db, limit=8, query_type=query_type, extra_tokens=top_tokens)
            if not matches:
                continue
            top_score = max(sc for _, sc in matches)
            if top_score > best_name_score:
                best_name_score = top_score
                ocr_name = tok
            for ext, sc in matches:
                if sc >= 68 and sc > text_score_map.get(ext, 0.0):
                    text_score_map[ext] = sc
        text_external_ids = [ext for ext, sc in sorted(text_score_map.items(), key=lambda kv: -kv[1])]
        if best_name_score <= 0:
            ocr_name = None

        # Collector candidates: prefer plain 'N/DD', tolerate merged/slash-missed
        # digit runs ('38795' -> '38/95'). Exact set-size alignment happens below.
        collector_candidates = ocr.find_collector_in_lines(ocr_lines)
        collector_candidates = [
            cc for cc in collector_candidates
            if _plausible_collector(cc)
        ]
        collector = collector_candidates[0] if collector_candidates else None

    # 3) Merge textual + visual evidence.
    collector_aligned, collector_possible = [], []
    if collector_candidates:
        for cc in collector_candidates:
            try:
                a, p = match_collector_split(cc, None, db)
            except Exception:
                continue
            collector_aligned.extend(a)
            collector_possible.extend(p)
        collector_aligned = list(dict.fromkeys(collector_aligned))
        collector_possible = list(dict.fromkeys(collector_possible))

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
            ctx=MergeContext(query_type=query_type, has_collector=bool(collector_aligned)),
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


def _plausible_collector(collector: str) -> bool:
    """Only treat a collector string as usable when its shape is plausible."""
    try:
        n, d = collector.split('/')
        num, den = int(n), int(d)
        return 1 <= num <= den and 30 <= den <= 400
    except Exception:
        return False