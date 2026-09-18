from datetime import datetime
from typing import List, Optional, Tuple
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from PIL import Image
from app.models import Card, PricePoint
from app.services import tcgdex, embeddings, index, image_cache
from app.config import TCGDEX_LANGUAGE

REQUEST_DELAY = 0.1
MAX_IMAGE_WORKERS = 8
PROGRESS_INTERVAL = 25


def ingest_all(db: Session, limit_sets: int = None, limit_cards_per_set: int = None, smoke_test: bool = False) -> int:
    """Fetch all TCGdex sets and cards, compute embeddings, store in DB, rebuild FAISS index."""
    if smoke_test:
        return _ingest_smoke_test(db)

    sets = tcgdex.fetch_sets()
    if limit_sets:
        sets = sets[:limit_sets]

    # Extension cache per set.
    set_extensions: dict[str, Optional[str]] = {}
    created_count = 0

    for set_index, s in enumerate(sets):
        set_id = s.get("id")
        full_set = tcgdex.fetch_set(set_id)
        light_cards = full_set.get("cards") or []
        if limit_cards_per_set:
            light_cards = light_cards[:limit_cards_per_set]

        set_name = full_set.get("name") or s.get("name")
        print(f"[{set_index + 1}/{len(sets)}] {set_name}: {len(light_cards)} cards")

        # Fetch full card metadata serially.
        full_cards: List[Tuple[dict, dict]] = []
        for light in light_cards:
            card_id = light.get("id")
            try:
                full_card = tcgdex.fetch_card(card_id)
                full_cards.append((light, full_card))
            except Exception as e:
                print(f"  Failed to fetch metadata {card_id}: {e}")
            time.sleep(REQUEST_DELAY)

        # Resolve image URLs and download images in parallel.
        image_results = _resolve_and_download_images(full_cards, set_extensions)

        # Process each card.
        for i, (light, full_card, image_url, image) in enumerate(image_results):
            if image_url is None or image is None:
                continue

            card_id = light.get("id")
            variants = tcgdex.extract_variants(full_card)
            set_code = full_card.get("set", {}).get("id") or set_id
            release_date = full_card.get("set", {}).get("releaseDate")

            try:
                emb = embeddings.embed_image_pil(image)
            except Exception as e:
                print(f"  Failed to embed {card_id}: {e}")
                emb = None

            for variant in variants:
                external_id = f"{card_id}_{variant['name']}"
                _upsert_card(db, external_id, card_id, full_card, set_code, set_name, release_date, variant, image_url, emb)
                created_count += 1

            if (i + 1) % PROGRESS_INTERVAL == 0:
                print(f"  ...processed {i + 1}/{len(image_results)} cards")

        db.commit()
        print(f"  Done with {set_name}. Total variants so far: {created_count}")

    print("Building FAISS index...")
    index.build_faiss_index(db, force=True)
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
        _upsert_card(db, external_id, card_id, full_card, set_id, set_name, release_date, variant, image_url, emb)

    db.commit()
    index.build_faiss_index(db, force=True)
    print(f"Smoke-test complete. Ingested {len(variants)} variant(s) for {full_card.get('name')}.")
    return len(variants)


def _resolve_and_download_images(
    full_cards: List[Tuple[dict, dict]],
    set_extensions: dict[str, Optional[str]]
) -> List[Tuple[dict, dict, Optional[str], Optional[Image.Image]]]:
    """Resolve working image URLs and download images concurrently."""

    def resolve(card_pair: Tuple[dict, dict]) -> Tuple[dict, dict, Optional[str], Optional[Image.Image]]:
        light, full_card = card_pair
        card_id = light.get("id")
        base_url = light.get("image")
        if not base_url:
            return light, full_card, None, None

        set_id = full_card.get("set", {}).get("id") or "unknown"
        cached_ext = set_extensions.get(set_id)

        image_url = image_cache.resolve_image_url(base_url, preferred_extension=cached_ext)
        if not image_url:
            return light, full_card, None, None

        # Cache discovered extension for this set.
        ext = image_url.split("?")[0].split(".")[-1]
        if ext in ("png", "jpg", "jpeg", "webp"):
            set_extensions[set_id] = ext

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
    emb: Optional
):
    existing = db.query(Card).filter(Card.external_id == external_id).first()
    if existing:
        db.delete(existing)
        db.flush()

    card = Card(
        id=card_id,
        external_id=external_id,
        name=full_card.get("name"),
        local_id=full_card.get("localId"),
        set_code=set_code,
        set_name=set_name,
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
