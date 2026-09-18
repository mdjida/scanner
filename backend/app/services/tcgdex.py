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


def _first(d: dict, *keys):
    for k in keys:
        if d.get(k):
            return d[k]
    return None


def _variant_label(detail: dict) -> str:
    """Build a stable, human-readable variant label from TCGdex detail."""
    vtype = (detail.get("type") or "normal").capitalize()
    subtype = detail.get("subtype")
    stamp = detail.get("stamp") or []
    label = vtype
    if subtype:
        label += " " + subtype.replace("-", " ").capitalize()
    if "1st-edition" in stamp or "1st-edition" in str(stamp).lower():
        label += " 1st Edition"
    elif "first-edition" in str(stamp).lower():
        label += " 1st Edition"
    return label


def _price_points_for_detail(detail: dict, variant_label: str) -> List[dict]:
    prices = []
    pricing = detail.get("pricing") or detail.get("price") or {}
    if pricing.get("tcgplayer"):
        prices.extend(price_points_from_tcgplayer(pricing["tcgplayer"], variant_label))
    if pricing.get("cardmarket"):
        prices.extend(price_points_from_cardmarket(pricing["cardmarket"], variant_label))
    return prices


def extract_variants(card: dict) -> List[dict]:
    """Return a list of variants with prices for a TCGdex full card object.

    TCGdex returns snake_case keys: variants_detailed / variantsDetailed,
    third_party / thirdParty, pricing / prices. Read both forms defensively.
    """
    details = _first(card, "variants_detailed", "variantsDetailed") or []
    output = []
    seen_labels = set()
    for detail in details:
        variant_label = _variant_label(detail)
        if variant_label in seen_labels:
            continue  # avoid duplicate physical variants (e.g. shadowless duplicates)
        seen_labels.add(variant_label)
        prices = _price_points_for_detail(detail, variant_label)
        if not prices:
            # Try the card-level pricing block as a fallback.
            top_pricing = _first(card, "pricing", "prices") or {}
            prices = _price_points_for_detail({"pricing": top_pricing}, variant_label)
        output.append({
            "name": variant_label,
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
