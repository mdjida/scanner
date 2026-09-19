from typing import Optional

from app.models import Card, PricePoint

# Real TCGplayer data gives one ungraded (Near Mint) price per variant.
# Condition tiers are estimated from the market price using standard multipliers,
# labeled "estimated" until a condition-tier source is available.
CONDITION_MULTIPLIERS = {
    "nm": 1.00,
    "lp": 0.72,
    "mp": 0.50,
    "hp": 0.35,
}


def _best_market_price(card: Card) -> Optional[PricePoint]:
    """Return the most authoritative single market price for a card."""
    prices = sorted(card.prices, key=lambda p: (p.price_source, p.price_type))
    if not prices:
        return None
    for p in prices:
        if p.price_type == "market":
            return p
    for p in prices:
        if p.price_type == "mid":
            return p
    for p in prices:
        if p.price_type == "avg":
            return p
    return prices[0]


def build_prices_by_condition(card: Card) -> Optional[dict]:
    """Build {nm, lp, mp, hp: {price, currency, source, estimated}} from market price."""
    market = _best_market_price(card)
    if not market or market.price is None:
        return None

    out = {}
    for cond, mult in CONDITION_MULTIPLIERS.items():
        out[cond] = {
            "price": round(market.price * mult, 2),
            "currency": market.currency or "USD",
            "source": market.price_source or "TCGdex/TCGplayer",
            "estimated": mult < 1.0,
        }
    return out