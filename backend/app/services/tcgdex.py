import httpx
from typing import List, Optional
from datetime import datetime
from app.config import TCGDEX_LANGUAGE, BASE_DIR

BASE_URL = f"https://api.tcgdex.net/v2/{TCGDEX_LANGUAGE}"

client = httpx.Client(timeout=60.0, headers={"User-Agent": "LiveCompOverlay-Backend/0.1.0"})
MAX_RETRIES = 3
REQUEST_DELAY_SECONDS = 0.25


def _get_with_retry(url: str, params: dict = None) -> dict:
    last_exception = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_exception = e
            if attempt < MAX_RETRIES:
                import time
                time.sleep(REQUEST_DELAY_SECONDS * attempt)
    raise last_exception


def fetch_sets() -> List[dict]:
    return _get_with_retry(f"{BASE_URL}/sets")


def fetch_set(set_id: str) -> dict:
    return _get_with_retry(f"{BASE_URL}/sets/{set_id}")


def fetch_card(card_id: str) -> dict:
    return _get_with_retry(f"{BASE_URL}/cards/{card_id}")


def search_cards(name: str, set_code: Optional[str] = None, local_id: Optional[str] = None) -> List[dict]:
    params = {"name": name}
    if set_code:
        params["set"] = set_code
    if local_id:
        params["localId"] = local_id
    return _get_with_retry(f"{BASE_URL}/cards", params)


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def price_points_from_cardmarket(cm: dict, variant: str) -> List[dict]:
    out = []
    pairs = [
        ("avg", cm.get("avg")),
        ("low", cm.get("low")),
        ("trend", cm.get("trend")),
        ("avg1", cm.get("avg1")),
        ("avg7", cm.get("avg7")),
        ("avg30", cm.get("avg30")),
    ]
    updated = parse_iso(cm.get("updated"))
    for price_type, price in pairs:
        if price is None:
            continue
        out.append({
            "price_source": "TCGdex/Cardmarket",
            "price_type": price_type,
            "condition": "Near Mint",
            "variant": variant,
            "currency": cm.get("unit") or "EUR",
            "price": float(price),
            "updated_at": updated,
        })
    return out


def price_points_from_tcgplayer(tcg: dict, variant_name: str) -> List[dict]:
    out = []
    updated = parse_iso(tcg.get("updated"))
    variant_map = {
        "Normal": tcg.get("normal"),
        "Holofoil": tcg.get("holofoil"),
        "ReverseHolofoil": tcg.get("reverseHolofoil"),
        "FirstEdition": tcg.get("firstEdition"),
        "FirstEditionHolofoil": tcg.get("firstEditionHolofoil"),
        "Unlimited": tcg.get("unlimited"),
    }
    for mapped_variant, variant_prices in variant_map.items():
        if not variant_prices:
            continue
        pairs = [
            ("market", variant_prices.get("marketPrice")),
            ("low", variant_prices.get("lowPrice")),
            ("mid", variant_prices.get("midPrice")),
            ("high", variant_prices.get("highPrice")),
            ("directLow", variant_prices.get("directLowPrice")),
        ]
        for price_type, price in pairs:
            if price is None:
                continue
            out.append({
                "price_source": "TCGdex/TCGplayer",
                "price_type": price_type,
                "condition": "Near Mint",
                "variant": mapped_variant,
                "currency": tcg.get("unit") or "USD",
                "price": float(price),
                "updated_at": updated,
            })
    return out


def extract_variants(card: dict) -> List[dict]:
    """Return a list of variants with prices for a TCGdex full card object."""
    details = card.get("variantsDetailed") or []
    output = []
    for detail in details:
        variant_name = (detail.get("type") or "normal").capitalize()
        prices = []
        pricing = detail.get("pricing") or {}
        if pricing.get("tcgplayer"):
            prices.extend(price_points_from_tcgplayer(pricing["tcgplayer"], variant_name))
        if pricing.get("cardmarket"):
            prices.extend(price_points_from_cardmarket(pricing["cardmarket"], variant_name))
        output.append({
            "name": variant_name,
            "type": detail.get("type"),
            "size": detail.get("size"),
            "prices": prices,
        })
    if not output:
        output.append({
            "name": "Normal",
            "type": "normal",
            "size": None,
            "prices": [],
        })
    return output
