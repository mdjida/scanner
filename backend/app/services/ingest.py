from datetime import datetime
from typing import List, Optional, Tuple
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from PIL import Image
from app.models import Card, PricePoint
from app.services import tcgdex, embeddings, index, image_cache
from app.config import TCGDEX_LANGUAGE

MAX_METADATA_WORKERS = 6
MAX_IMAGE_WORKERS = 8
EMBED_BATCH_SIZE = 32
PROGRESS_INTERVAL = 100

_resume_lock = threading.Lock()
_resume_counts: dict[str, int] = {}  # set_code -> count of distinct card ids already in DB


class IngestProgress:
    def __init__(self):
        self.running = False
        self.cancel_requested = False
        self.sets_total = 0
        self.sets_done = 0
        self.cards_total = 0
        self.cards_done = 0
        self.cards_skipped = 0
        self.cards_failed = 0
        self.current_set = ""
        self.current_set_index = 0
        self.started_at = None
        self.finished_at = None
        self.error = None
        self.lock = threading.Lock()

    def to_dict(self) -> dict:
        with self.lock:
            return {
                "running": self.running,
                "cancel_requested": self.cancel_requested,
                "sets_total": self.sets_total,
                "sets_done": self.sets_done,
                "cards_total": self.cards_total,
                "cards_done": self.cards_done,
                "cards_skipped": self.cards_skipped,
                "cards_failed": self.cards_failed,
                "current_set": self.current_set,
                "current_set_index": self.current_set_index,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "finished_at": self.finished_at.isoformat() if self.finished_at else None,
                "error": self.error,
            }


PROGRESS = IngestProgress()


def reset_resume_state():
    global _resume_counts
    with _resume_lock:
        _resume_counts = {}


def _load_resume_state(db: Session) -> dict:
    """Return {set_code: distinct_card_id_count} already present in the DB."""
    global _resume_counts
    if _resume_counts:
        return _resume_counts
    with _resume_lock:
        if not _resume_counts:
            rows = (
                db.query(Card.set_code, Card.id)
                .filter(Card.set_code.isnot(None))
                .distinct()
                .all()
            )
            counts: dict[str, int] = {}
            for set_code, _card_id in rows:
                counts[set_code] = counts.get(set_code, 0) + 1
            _resume_counts = counts
    return _resume_counts


def ingest_all(
    db: Session,
    limit_sets: int = None,
    limit_cards_per_set: int = None,
    smoke_test: bool = False,
    from_catalog: bool = False,
) -> int:
    """Fetch all TCGdex sets and cards, compute embeddings, store in DB, rebuild FAISS index.

    Resumable: sets whose `set_code` already exists in the DB are skipped unless
    the set has zero cards with embeddings (partial re-run).
    """
    if smoke_test:
        return _ingest_smoke_test(db)

    sets = tcgdex.fetch_sets()
    if limit_sets:
        sets = sets[:limit_sets]

    PROGRESS.sets_total = len(sets)
    PROGRESS.sets_done = 0
    PROGRESS.cards_total = 0
    PROGRESS.cards_done = 0
    PROGRESS.cards_skipped = 0
    PROGRESS.cards_failed = 0
    PROGRESS.running = True
    PROGRESS.cancel_requested = False
    PROGRESS.started_at = datetime.utcnow()
    PROGRESS.error = None

    resume_counts = _load_resume_state(db)
    # Diagnostics: sets already present (partial) will be re-ingested,
    # so clear the resume map to avoid counting freshly-added cards as "skipped".
    resume_counts = {k: v for k, v in resume_counts.items()}
    created_count = 0

    for set_index, s in enumerate(sets):
        if PROGRESS.cancel_requested:
            break
        set_id = s.get("id")
        PROGRESS.current_set = (s.get("name") or set_id) or ""
        PROGRESS.current_set_index = set_index + 1

        try:
            full_set = tcgdex.fetch_set(set_id)
        except Exception as e:
            print(f"  Failed to fetch set {set_id}: {e}")
            PROGRESS.cards_failed += 1
            continue

        light_cards = full_set.get("cards") or []
        if limit_cards_per_set:
            light_cards = light_cards[:limit_cards_per_set]

        set_name = full_set.get("name") or s.get("name") or PROGRESS.current_set

        # Skip only sets already fully present in the DB (resumable partial re-runs re-ingest).
        expected_cards = (full_set.get("cardCount") or {}).get("total") or len(light_cards)
        existing_cards = resume_counts.get(set_id, 0)
        if existing_cards >= expected_cards:
            PROGRESS.sets_done += 1
            PROGRESS.cards_skipped += len(light_cards)
            print(f"[{set_index + 1}/{len(sets)}] {PROGRESS.current_set}: skipped (already ingested, {existing_cards}/{expected_cards})")
            continue

        PROGRESS.cards_total += len(light_cards)
        print(f"[{set_index + 1}/{len(sets)}] {PROGRESS.current_set}: {len(light_cards)} cards")

        # Fetch full card metadata in parallel.
        full_cards: List[Tuple[dict, dict]] = []
        fetch_failures = 0
        with ThreadPoolExecutor(max_workers=MAX_METADATA_WORKERS) as mpool:
            futures = {mpool.submit(tcgdex.fetch_card, light.get("id")): light for light in light_cards}
            for future in as_completed(futures):
                light = futures[future]
                try:
                    full_card = future.result()
                    full_cards.append((light, full_card))
                except Exception as e:
                    fetch_failures += 1
                    PROGRESS.cards_failed += 1
                    print(f"  Failed to fetch metadata {light.get('id')}: {e}")

        full_cards.sort(key=lambda pair: pair[0].get("id") or "")

        # Resolve image URLs and download images in parallel.
        image_results = _resolve_and_download_images(full_cards)

        # Batch-embed all downloaded images.
        images_flat: List[Tuple[Tuple[int, Tuple], Image.Image]] = []
        for card_index, (light, full_card, image_url, image) in enumerate(image_results):
            if image_url is None or image is None:
                continue
            images_flat.append(((card_index, (light, full_card, image_url)), image))

        all_embeds = embeddings.embed_images_batch([img for _, img in images_flat], batch_size=EMBED_BATCH_SIZE) if images_flat else []

        # Map embeddings back to cards.
        emb_by_idx: dict[int, Optional] = {}
        for i, (meta, _img) in enumerate(images_flat):
            emb_by_idx[meta[0]] = all_embeds[i] if i < len(all_embeds) else None

        # Process each card.
        for i, (light, full_card, image_url, image) in enumerate(image_results):
            if image_url is None or image is None:
                continue
            card_id = light.get("id")
            set_code = full_card.get("set", {}).get("id") or set_id
            release_date = full_card.get("set", {}).get("releaseDate")

            variants = tcgdex.extract_variants(full_card)
            emb = emb_by_idx.get(i)

            for variant in variants:
                external_id = f"{card_id}_{variant['name']}"
                set_card_count = (full_card.get("set", {}) or {}).get("cardCount", {}).get("total")
                _upsert_card(db, external_id, card_id, full_card, set_code, set_name, release_date, variant, image_url, emb, set_card_count)
                created_count += 1
                PROGRESS.cards_done += 1

            if (i + 1) % PROGRESS_INTERVAL == 0:
                print(f"  ...processed {i + 1}/{len(image_results)} cards")

        db.commit()
        PROGRESS.sets_done += 1
        resume_counts[set_id] = expected_cards
        print(f"  Done with {set_name}. Total variants so far: {created_count}")

    print("Building FAISS index...")
    try:
        index.build_faiss_index(db, force=True)
    except ValueError as e:
        print(f"  Index build skipped: {e}")

    PROGRESS.running = False
    PROGRESS.finished_at = datetime.utcnow()
    print(f"Ingested {created_count} card variants.")
    return created_count


def _ingest_smoke_test(db: Session) -> int:
    """Ingest exactly one well-known card so the iOS app can be tested immediately."""
    print("Running smoke-test ingestion (Base Set Charizard)...")
    card_id = "base1-4"
    full_card = tcgdex.fetch_card(card_id)
    set_id = full_card.get("set", {}).get("id") or "base1"
    set_name = full_card.get("set", {}).get("name") or "Base Set"
    release_date = full_card.get("set", {}).get("releaseDate")
    variants = tcgdex.extract_variants(full_card)

    image_url = image_cache.resolve_image_url(f"https://assets.tcgdex.net/en/base/base1/4")
    if not image_url:
        raise RuntimeError("Could not resolve smoke-test image URL")

    image = image_cache.load_image(image_url)
    if not image:
        raise RuntimeError("Could not download smoke-test image")

    emb = embeddings.embed_image_pil(image)

    for variant in variants:
        external_id = f"{card_id}_{variant['name']}"
        set_card_count = (full_card.get("set", {}) or {}).get("cardCount", {}).get("total")
        _upsert_card(db, external_id, card_id, full_card, set_id, set_name, release_date, variant, image_url, emb, set_card_count)

    db.commit()
    index.build_faiss_index(db, force=True)
    print(f"Smoke-test complete. Ingested {len(variants)} variant(s) for {full_card.get('name')}.")
    return len(variants)


def _resolve_and_download_images(
    full_cards: List[Tuple[dict, dict]],
) -> List[Tuple[dict, dict, Optional[str], Optional[Image.Image]]]:
    """Resolve working image URLs and download images concurrently."""

    def resolve(card_pair: Tuple[dict, dict]) -> Tuple[dict, dict, Optional[str], Optional[Image.Image]]:
        light, full_card = card_pair
        card_id = light.get("id")
        base_url = light.get("image")
        if not base_url:
            return light, full_card, None, None

        image_url = image_cache.resolve_image_url(base_url)
        if not image_url:
            return light, full_card, None, None

        image = image_cache.load_image(image_url)
        return light, full_card, image_url, image

    results = []
    with ThreadPoolExecutor(max_workers=MAX_IMAGE_WORKERS) as executor:
        futures = {executor.submit(resolve, pair): pair for pair in full_cards}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                print(f"  Image download failed: {e}")

    results.sort(key=lambda r: r[0].get("id") or "")
    return results


def _upsert_card(
    db: Session,
    external_id: str,
    card_id: str,
    full_card: dict,
    set_code: str,
    set_name: str,
    release_date: Optional[str],
    variant: dict,
    image_url: str,
    emb: Optional,
    set_card_count: Optional[int] = None,
):
    # Card.id is the TCGdex card ID shared by all variants; delete the whole
    # card first so re-ingesting any variant can't hit the PK constraint.
    existing = db.query(Card).filter(Card.id == card_id).all()
    for e in existing:
        db.delete(e)
    if existing:
        db.flush()

    card = Card(
        id=card_id,
        external_id=external_id,
        name=full_card.get("name"),
        local_id=full_card.get("localId"),
        set_code=set_code,
        set_name=set_name,
        set_card_count=set_card_count,
        rarity=full_card.get("rarity"),
        image_url=image_url,
        variant=variant["name"],
        language=TCGDEX_LANGUAGE,
        embedding=emb.tolist() if emb is not None else None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(card)
    db.flush()

    for price in variant["prices"]:
        db.add(PricePoint(
            card_external_id=external_id,
            price_source=price["price_source"],
            price_type=price["price_type"],
            condition=price["condition"],
            variant=price["variant"],
            currency=price["currency"],
            price=price["price"],
            updated_at=price["updated_at"] or datetime.utcnow(),
        ))