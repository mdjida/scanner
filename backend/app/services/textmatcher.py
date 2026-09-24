import re
import unicodedata
from enum import Enum
from typing import List, Optional, Tuple

from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from app.models import Card


class QueryType(Enum):
    POKEMON = "pokemon"
    TRAINER = "trainer"
    ENERGY = "energy"
    UNKNOWN = "unknown"


TRAINER_KEYWORDS = {"trainer", "supporter", "stadium", "item", "tool", "technical machine"}
ENERGY_KEYWORDS = {"energy", "basic energy", "special energy"}
ENERGY_SINGLE = ("energy",)
ENERGY_MULTI = ("basic energy", "special energy")
TRAINER_SINGLE = ("trainer", "supporter", "stadium", "item", "tool")
TRAINER_MULTI = ("pokemon tool", "technical machine")


def _fuzzy_hit(text: str, single_terms, multi_terms) -> bool:
    """True when any OCR token is close to one of the given terms (tolerant of
    OCR typos like 'enerey' -> energy). Multi-word terms must match a token pair
    (tight threshold), and single terms require a length-proportional match, so
    bare 'basic', 'pokemon', 'to' or 'on' lines never classify as energy/trainer."""
    words = text.split()
    for w in words:
        for t in single_terms:
            if len(w) < max(3, len(t) - 2):
                continue
            try:
                if fuzz.WRatio(w, t) >= 80:
                    return True
            except Exception:
                continue
    for i in range(len(words) - 1):
        gram = words[i] + " " + words[i + 1]
        for t in multi_terms:
            try:
                if fuzz.WRatio(gram, t) >= 90:
                    return True
            except Exception:
                continue
    return False


def classify_query_type(name_query: Optional[str], lines: Optional[List[Tuple[str, float, object, str]]] = None) -> QueryType:
    """Classify what kind of card the OCR is describing (also tolerant of
    OCR typos in the type words, e.g. 'enerey' -> energy)."""
    text = normalize(name_query or "")
    for item in lines or []:
        if not isinstance(item, (tuple, list)) or len(item) < 4:
            continue
        try:
            text += " " + normalize(str(item[0]))
        except Exception:
            continue
    words = set(text.split())
    if words & ENERGY_KEYWORDS or _fuzzy_hit(text, ENERGY_SINGLE, ENERGY_MULTI):
        return QueryType.ENERGY
    if words & TRAINER_KEYWORDS or _fuzzy_hit(text, TRAINER_SINGLE, TRAINER_MULTI):
        return QueryType.TRAINER
    return QueryType.POKEMON


def _type_boost(external_id: str, query_type: QueryType, db: Session) -> float:
    """Return a small score bonus for cards whose name matches the query type."""
    if query_type == QueryType.UNKNOWN:
        return 0.0
    card = db.query(Card).filter(Card.external_id == external_id).first()
    if not card:
        return 0.0
    name = normalize(card.name or "")
    if query_type == QueryType.ENERGY and "energy" in name:
        return 0.06
    if query_type == QueryType.TRAINER and (TRAINER_KEYWORDS & set(name.split())):
        return 0.06
    if query_type == QueryType.POKEMON and not (TRAINER_KEYWORDS | ENERGY_KEYWORDS) & set(name.split()):
        return 0.02
    return 0.0

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


def _strip_junk_suffix(q: str) -> str:
    """Drop trailing OCR junk like 'cw.62' / '.62' / '62' appended to a card name.

    Keeps the leading letter where the junk glued onto it, e.g. 'Garchomp Cw.62'
    -> 'garchomp c' (the 'C' is part of the real name).
    """
    n = (q or "").strip()
    n = re.sub(r"(?i)\s+([a-z])[a-z]{0,3}\.?[0-9]{1,3}$", lambda m: " " + m.group(1), n).strip()
    n = re.sub(r"(?i)\s*\.?[0-9]{1,3}$", "", n).strip()
    return n or (q or "").strip()


def match_name_fuzzy(
    name_query: str,
    db: Session,
    limit: int = 12,
    query_type: QueryType = QueryType.UNKNOWN,
    extra_tokens=(),
) -> List[Tuple[str, float]]:
    """Fuzzy-match a name string against all card names in the DB.

    Returns list of (external_id, score 0-100+). Scores >= ~80 are strong.
    When query_type is trainer/energy, cards of that type get a small boost.
    extra_tokens: additional title-region OCR tokens (e.g. a 'team magmas'
    prefix) used as a cross-set disambiguation signature: cards whose name
    contains every observed token get a bonus, so 'Team Magma's Rhyhorn'
    beats plain 'Rhyhorn' when both are close.
    """
    if not name_query:
        return []
    cleaned = _strip_junk_suffix(str(name_query))
    q = normalize(cleaned)
    if len(q) < 2:
        return []

    sig: List[str] = []
    for t in list(extra_tokens or ()) + [cleaned]:
        try:
            sig.append(re.sub(r"[^\w]", "", normalize(_strip_junk_suffix(str(t)))))
        except Exception:
            continue
    sig = list(dict.fromkeys(w for w in sig if w and len(w) >= 2))

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
        limit=min(limit * 3, len(names)) if names else 0,
    )
    out = []
    seen = set()
    for matched_name, score, _ in results:
        for external_id in name_map[matched_name]:
            if external_id in seen:
                continue
            seen.add(external_id)
            type_bonus = _type_boost(external_id, query_type, db)
            raw = max(0.0, min(100.0, float(score) + type_bonus * 100))
            # Cross-set/prefix tiebreak: prefer cards whose full name contains
            # every token the OCR actually saw in the title region.
            if sig:
                name_col = re.sub(r"[^\w]", "", normalize(matched_name))
                present = sum(1 for w in sig if w in name_col)
                raw = raw + 20.0 * present
            out.append((external_id, raw))
    out.sort(key=lambda kv: -kv[1])
    return out[:limit]


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
    for item in lines:
        if not isinstance(item, (tuple, list)) or len(item) < 4:
            continue
        text, conf, _bbox, region = item[:4]
        try:
            conf = float(conf)
        except Exception:
            continue
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