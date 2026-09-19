import re
import unicodedata
from typing import List, Optional, Tuple

from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from app.models import Card


def normalize(text: str) -> str:
    """Normalize a string for matching: strip accents, collapse spaces, drop noise."""
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"[^\w\s'.&/-]", " ", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def is_noise(text: str) -> bool:
    n = normalize(text)
    if not n or len(n) < 2:
        return True
    if re.fullmatch(r"(\d+/\d+|hp\d+|\d+hp|\d+)", n):
        return True
    if re.fullmatch(r"stage\d+", n):
        return True
    common = {
        "stage", "stage1", "stage2", "basicpokemon", "basic",
        "evolvesfrom", "put", "on", "the", "and", "your", "this",
        "card", "cards", "pokemon", "energy", "no", "of", "to",
    }
    return n in common


def _clean_name_token(text: str) -> Optional[str]:
    """Extract a clean human-readable card-name token from OCR text (best-effort)."""
    n = normalize(text)
    # Drop trailing set/era footers like '2005', 'nintendo', 'wizards', 'creatures'
    n = re.sub(r"\b(nintendo|creatures|gamefreak|wizards|pocketmonsters|(19|20)\d\d)\b.*$", "", n).strip()
    return n or None


def match_name_fuzzy(name_query: str, db: Session, limit: int = 12) -> List[Tuple[str, float]]:
    """Fuzzy-match a name string against all card names in the DB.

    Returns list of (external_id, score 0-100). Scores >= ~80 are strong.
    """
    if not name_query:
        return []
    q = normalize(name_query)
    if len(q) < 2:
        return []

    # Build a map name -> list of external_ids, then fuzzy match names once.
    name_map: dict[str, List[str]] = {}
    rows = db.query(Card.name, Card.external_id).all()
    for name, external_id in rows:
        key = normalize(name)
        name_map.setdefault(key, []).append(external_id)

    names = list(name_map.keys())
    results = process.extract(
        q,
        names,
        scorer=fuzz.WRatio,
        limit=min(limit * 2, len(names)) if names else 0,
    )
    out = []
    seen = set()
    for matched_name, score, _ in results:
        for external_id in name_map[matched_name]:
            if external_id in seen:
                continue
            seen.add(external_id)
            out.append((external_id, float(score)))
            if len(out) >= limit:
                return out
    return out


def best_name_match(name_query: str, db: Session) -> Optional[Tuple[str, float]]:
    matches = match_name_fuzzy(name_query, db, limit=5)
    if not matches:
        return None
    best_ext, best_score = matches[0]
    if best_score < 60:
        return None
    return best_ext, best_score


def extract_card_name_candidates(lines: List[Tuple[str, float, object, str]]) -> List[Tuple[str, float]]:
    """From OCR lines, return plausible card-name text + confidence, best first."""
    ranked = []
    for text, conf, _bbox, region in lines:
        if region not in ("top", "title"):
            continue
        t = _clean_name_token(text)
        if not t or is_noise(t):
            continue
        score = conf
        words = t.split()
        # A real Pokémon name is typically 1-3 words and starts with a capital.
        if 1 <= len(words) <= 3:
            score += 0.30  # strong prior
        elif len(words) <= 4:
            score += 0.10
        # Penalize noisy all-lowercase junk or pure numeric/HP-like tokens harder.
        if re.fullmatch(r"hp\d+", normalize(t)):
            score -= 1.0
        if re.fullmatch(r"stage\d*", normalize(t)):
            score -= 0.8
        ranked.append((t, round(score, 3)))
    ranked.sort(key=lambda x: -x[1])
    return ranked[:5]


def match_collector_to_cards(
    collector: Optional[str],
    setName: Optional[str],
    db: Session,
) -> List[str]:
    """Resolve a collector string like '4/102' (+ optional set hint) to external_ids.

    Returns strong (exact set size) pins first, then unknowns, then weak pins.
    Use match_collector_split for the aligned/possible breakdown.
    """
    strong, unknown, weak = _match_collector_split(collector, setName, db)
    return strong + unknown + weak


def match_collector_split(
    collector: Optional[str],
    setName: Optional[str],
    db: Session,
) -> Tuple[List[str], List[str]]:
    """Split collector matches into (aligned, possible).

    aligned: set-card-count exactly matches the collector denominator (strong pin).
    possible: cards with same localId but unknown or different set size (weak pin).
    """
    strong, unknown, weak = _match_collector_split(collector, setName, db)
    return strong + unknown, weak


def _match_collector_split(
    collector: Optional[str],
    setName: Optional[str],
    db: Session,
) -> Tuple[List[str], List[str], List[str]]:
    if not collector:
        return [], [], []
    m = re.fullmatch(r"(\d{1,3})/(\d{1,3})", collector)
    if not m:
        return [], [], []
    local_id = str(int(m.group(1)))
    set_total = int(m.group(2))
    query = db.query(Card).filter(Card.local_id == local_id)
    if setName:
        query = query.filter(Card.set_name == setName)
    rows = query.all()
    strong, weak, unknown = [], [], []
    for c in rows:
        if c.set_card_count is not None and abs(c.set_card_count - set_total) <= 2:
            strong.append(c.external_id)
        elif c.set_card_count is not None:
            weak.append(c.external_id)
        else:
            unknown.append(c.external_id)
    return strong, unknown, weak