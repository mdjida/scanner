from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Card


def merge(
    db: Session,
    text_external_ids: List[str],
    text_score_map: dict,
    collector_aligned_ids: Optional[List[str]],
    collector_possible_ids: Optional[List[str]],
    card_name: Optional[str],
    visual: List[Tuple[Card, float]],
    prefer_visual: bool = False,
) -> Optional[dict]:
    """Blend text + collector + visual evidence into a ranked decision.

    text_external_ids:      external ids produced by name matching (best-first)
    text_score_map:         external_id -> fuzzy score (0-100)
    collector_aligned_ids:  exact set-size collector pins (usually 1 card)
    collector_possible_ids: other cards sharing the same collector number but a
        different (or unknown) set size — weak pins
    """
    if not text_external_ids and not collector_aligned_ids and not collector_possible_ids and not visual:
        return None

    aligned_set = set(collector_aligned_ids or [])
    possible_set = set(collector_possible_ids or [])

    # Gather all candidate cards.
    combined: dict[str, Card] = {}
    for ext in list(text_external_ids) + list(aligned_set) + list(possible_set):
        if ext in combined:
            continue
        card = db.query(Card).filter(Card.external_id == ext).first()
        if card:
            combined[ext] = card
    for card, _score in visual:
        combined.setdefault(card.external_id, card)

    if not combined:
        return None

    # Normalized text score: the closest name match gets 1.0, others scale.
    max_text_score = max((text_score_map.get(ext, 0.0) for ext in text_external_ids), default=0.0)
    if max_text_score <= 0:
        max_text_score = 1.0

    def text_component(ext: str) -> float:
        raw = text_score_map.get(ext, 0.0)
        if raw <= 0:
            return 0.0
        return max(0.0, min(1.0, raw / max_text_score))

    visual_map = {card.external_id: score for card, score in visual}

    scored: dict[str, Tuple[float, str]] = {}
    for ext, card in combined.items():
        t = text_component(ext)
        v = visual_map.get(ext, 0.0)
        is_aligned = ext in aligned_set
        is_possible = ext in possible_set

        if is_aligned:
            # Exact set-size collector pin. When the OCR name also agrees, this is
            # two independent strong signals -> near-certain, outranks name+visual.
            if t >= 0.85:
                score = 0.97 + 0.03 * v
                reason = "collector_verified"
            else:
                score = 0.62 + 0.25 * t + 0.13 * v
                reason = "collector_set_exact"
        elif is_possible:
            score = 0.38 + 0.30 * t + 0.32 * v
            reason = "collector"
        elif t >= 0.85 and v >= 0.80:
            score = 0.35 + 0.35 * t + 0.30 * v
            reason = "name_visual"
        elif t >= 0.85:
            score = 0.40 + 0.45 * t
            reason = "name"
        elif v >= 0.90:
            score = 0.85 * v
            reason = "visual"
        elif prefer_visual:
            score = 0.60 * v + 0.40 * t
            reason = "weak"
        else:
            score = 0.40 * v + 0.60 * t
            reason = "weak"
        scored[ext] = (max(0.0, min(1.0, score)), reason)

    ranked = sorted(scored.items(), key=lambda kv: -kv[1][0])
    best_ext, (best_score, reason) = ranked[0]
    best_card = combined[best_ext]

    # Confidence label.
    if reason in ("collector_verified", "collector_set_exact", "name_visual") and best_score >= 0.65:
        confidence = "high"
    elif reason == "collector" and best_score >= 0.60:
        confidence = "high"
    elif best_score >= 0.78:
        confidence = "high"
    elif best_score >= 0.58:
        confidence = "medium"
    elif best_score >= 0.38:
        confidence = "low"
    else:
        confidence = "uncertain"

    verified_by = []
    if is_verified_by(reason, "collector"):
        verified_by.append("collector")
    if is_verified_by(reason, "name"):
        verified_by.append("ocr_name")
    if reason == "visual":
        verified_by.append("visual")
    if not verified_by:
        verified_by.append("weak")

    candidates = [
        {"card": combined[ext], "score": round(score, 4)}
        for ext, (score, _r) in ranked[1:5]
    ]
    return {
        "best": {"card": best_card, "score": round(best_score, 4)},
        "candidates": candidates,
        "confidence": confidence,
        "verified_by": verified_by,
    }


def is_verified_by(reason: str, tag: str) -> bool:
    return (reason.startswith("collector") and tag == "collector") or (
        (reason.startswith("name") or reason == "name_visual") and tag == "name"
    )