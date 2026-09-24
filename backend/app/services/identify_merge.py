from dataclasses import dataclass
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Card
from app.services.textmatcher import QueryType, normalize


@dataclass
class MergeContext:
    query_type: QueryType = QueryType.UNKNOWN
    has_collector: bool = False


def _same_name_group(name: str) -> str:
    """Return a loose name grouping for cross-set ambiguity detection.

    e.g. 'Team Magma's Rhyhorn' and 'Rhyhorn' both contain 'rhyhorn' -> group 'rhyhorn'.
    Energy/Trainer cards are grouped by their full normalized name.
    """
    n = normalize(name)
    # Strip trainer/energy suffixes that don't affect base name matching.
    n = n.replace("'s", " ").replace("team", "")
    words = [w for w in n.split() if len(w) > 2]
    if not words:
        return n
    # Use the longest word as the base species/name.
    return max(words, key=len)


def merge(
    db: Session,
    text_external_ids: List[str],
    text_score_map: dict,
    collector_aligned_ids: Optional[List[str]],
    collector_possible_ids: Optional[List[str]],
    card_name: Optional[str],
    visual: List[Tuple[Card, float]],
    prefer_visual: bool = False,
    ctx: Optional[MergeContext] = None,
) -> Optional[dict]:
    """Blend text + collector + visual evidence into a ranked decision.

    text_external_ids:      external ids produced by name matching (best-first)
    text_score_map:         external_id -> fuzzy score (0-100)
    collector_aligned_ids:  exact set-size collector pins (usually 1 card)
    collector_possible_ids: other cards sharing the same collector number but a
        different (or unknown) set size — weak pins
    ctx:                    context for type bias and ambiguity handling
    """
    if not text_external_ids and not collector_aligned_ids and not collector_possible_ids and not visual:
        return None

    ctx = ctx or MergeContext()
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

    # Type-based deprioritization: if the query is clearly an energy/trainer,
    # pure Pokémon cards get a small score penalty.
    def type_penalty(card: Card) -> float:
        name = normalize(card.name or "")
        if ctx.query_type == QueryType.ENERGY and "energy" not in name:
            return 0.12
        if ctx.query_type == QueryType.TRAINER and not ({"trainer", "supporter", "stadium", "item"} & set(name.split())):
            return 0.10
        return 0.0

    scored: dict[str, Tuple[float, str]] = {}
    for ext, card in combined.items():
        t = text_component(ext)
        v = visual_map.get(ext, 0.0)
        is_aligned = ext in aligned_set
        is_possible = ext in possible_set
        penalty = type_penalty(card)

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
            score = 0.38 + 0.30 * t + 0.32 * v - penalty
            reason = "collector"
        elif t >= 0.85 and v >= 0.80:
            score = 0.35 + 0.35 * t + 0.30 * v - penalty
            reason = "name_visual"
        elif t >= 0.85:
            score = 0.40 + 0.45 * t - penalty
            reason = "name"
        elif v >= 0.93:
            # Near-perfect visual match (text usually sparse for these cards:
            # plain energies, promos, holofoil). Let CLIP carry it.
            score = 0.45 + 0.55 * v - penalty
            reason = "visual_strong"
        elif v >= 0.90:
            score = 0.85 * v - penalty
            reason = "visual"
        elif prefer_visual:
            score = 0.60 * v + 0.40 * t - penalty
            reason = "weak"
        else:
            score = 0.40 * v + 0.60 * t - penalty
            reason = "weak"
        scored[ext] = (max(0.0, min(1.0, score)), reason)

    ranked = sorted(scored.items(), key=lambda kv: -kv[1][0])
    best_ext, (best_score, reason) = ranked[0]
    best_card = combined[best_ext]

    # Cross-set ambiguity: if no collector and the top two candidates share the
    # same base name, don't claim high confidence unless visual margin is large.
    ambiguous = False
    if not ctx.has_collector and len(ranked) >= 2:
        second_ext, (second_score, _) = ranked[1]
        if _same_name_group(best_card.name) == _same_name_group(combined[second_ext].name):
            if best_score - second_score < 0.18:
                ambiguous = True
        # Energy cards look alike: without a readable type word or collector,
        # a near-tie between different energy types is genuinely uncertain.
        elif ctx.query_type == QueryType.ENERGY and best_score - second_score < 0.10:
            b_name = normalize(best_card.name)
            s_name = normalize(combined[second_ext].name)
            if "energy" in b_name and "energy" in s_name:
                ambiguous = True

    # Confidence label.
    if ambiguous:
        confidence = "uncertain"
    elif reason in ("collector_verified", "collector_set_exact", "name_visual") and best_score >= 0.65:
        confidence = "high"
    elif reason == "collector" and best_score >= 0.60:
        # A 'possible' (non-set-count-aligned) collector is a weak pin: never
        # claim high confidence from it, only medium.
        confidence = "medium"
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
    if reason == "visual" or reason == "visual_strong":
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