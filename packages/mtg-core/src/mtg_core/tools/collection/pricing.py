"""Collection pricing utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase

from .parser import ParsedCardInput


@dataclass
class PricedCard:
    """A card with pricing information."""

    card_name: str | None
    quantity: int
    foil: bool
    set_code: str | None
    collector_number: str | None
    price_usd: float | None
    price_usd_foil: float | None
    total_value: float  # price * quantity (uses foil price if foil=True)


@dataclass
class CollectionPriceResult:
    """Result of pricing a collection."""

    cards: list[PricedCard]
    total_value: float
    total_value_foil: float  # value if all cards were foil
    cards_with_prices: int
    cards_without_prices: int
    median_price: float
    top_cards: list[tuple[str, float]]  # (name, price) for top 5


def _price_key(card_name: str | None, set_code: str | None, collector_number: str | None) -> str:
    """Generate a unique key for price lookup."""
    name = card_name or ""
    if set_code and collector_number:
        return f"{name}|{set_code.upper()}|{collector_number}"
    return name


async def price_collection(
    db: UnifiedDatabase,
    cards: list[ParsedCardInput],
) -> CollectionPriceResult:
    """Price a collection of parsed cards.

    Uses optimized price-only queries that fetch just 4 columns instead of 40+.
    Cards with specific printings use get_prices_by_set_and_numbers(),
    cards without use get_prices_by_names().

    Prices in database are stored in cents, converted to dollars in output.

    Args:
        db: Database connection
        cards: List of parsed card inputs

    Returns:
        CollectionPriceResult with pricing data
    """
    if not cards:
        return CollectionPriceResult(
            cards=[],
            total_value=0.0,
            total_value_foil=0.0,
            cards_with_prices=0,
            cards_without_prices=0,
            median_price=0.0,
            top_cards=[],
        )

    # Separate cards by whether they have printing info
    cards_with_printing: list[ParsedCardInput] = []
    cards_without_printing: list[ParsedCardInput] = []

    for card in cards:
        if card.set_code and card.collector_number:
            cards_with_printing.append(card)
        elif card.card_name:
            cards_without_printing.append(card)

    # Build price lookup dict: key -> (usd, usd_foil) in dollars
    price_data: dict[str, tuple[float | None, float | None]] = {}

    # Fetch prices for cards with specific printings
    if cards_with_printing:
        printings_to_fetch = [
            (c.set_code, c.collector_number)
            for c in cards_with_printing
            if c.set_code and c.collector_number
        ]
        prices_by_printing = await db.get_prices_by_set_and_numbers(printings_to_fetch)

        for card in cards_with_printing:
            assert card.set_code is not None
            assert card.collector_number is not None
            lookup_key = (card.set_code.upper(), card.collector_number)
            price_tuple = prices_by_printing.get(lookup_key)
            if price_tuple:
                key = _price_key(card.card_name, card.set_code, card.collector_number)
                # Convert cents to dollars
                price_usd = price_tuple[0] / 100.0 if price_tuple[0] else None
                price_usd_foil = price_tuple[1] / 100.0 if price_tuple[1] else None
                price_data[key] = (price_usd, price_usd_foil)

    # Fetch prices for cards without specific printings (by name)
    if cards_without_printing:
        card_names = [c.card_name for c in cards_without_printing if c.card_name]
        prices_by_name = await db.get_prices_by_names(card_names)

        for card in cards_without_printing:
            if card.card_name:
                price_tuple = prices_by_name.get(card.card_name.lower())
                if price_tuple:
                    key = _price_key(card.card_name, card.set_code, card.collector_number)
                    price_usd = price_tuple[0] / 100.0 if price_tuple[0] else None
                    price_usd_foil = price_tuple[1] / 100.0 if price_tuple[1] else None
                    price_data[key] = (price_usd, price_usd_foil)

    # Build result
    priced_cards: list[PricedCard] = []
    total_value = 0.0
    total_value_foil = 0.0
    cards_with_prices = 0
    cards_without_prices = 0
    all_prices: list[float] = []
    card_prices: list[tuple[str, float]] = []

    for card in cards:
        key = _price_key(card.card_name, card.set_code, card.collector_number)
        prices = price_data.get(key)

        card_price_usd: float | None = None
        card_price_usd_foil: float | None = None
        card_total = 0.0

        if prices:
            card_price_usd, card_price_usd_foil = prices
            cards_with_prices += 1

            # Calculate value based on foil status
            if card.foil and card_price_usd_foil:
                card_total = card_price_usd_foil * card.quantity
            elif card_price_usd:
                card_total = card_price_usd * card.quantity

            total_value += card_total

            # Calculate foil total
            if card_price_usd_foil:
                total_value_foil += card_price_usd_foil * card.quantity
            elif card_price_usd:
                total_value_foil += card_price_usd * card.quantity

            # Track for stats
            single_price = card_price_usd or card_price_usd_foil or 0.0
            if single_price > 0:
                all_prices.append(single_price)
                name = card.card_name or f"{card.set_code} #{card.collector_number}"
                card_prices.append((name, single_price))
        else:
            cards_without_prices += 1

        priced_cards.append(
            PricedCard(
                card_name=card.card_name,
                quantity=card.quantity,
                foil=card.foil,
                set_code=card.set_code,
                collector_number=card.collector_number,
                price_usd=card_price_usd,
                price_usd_foil=card_price_usd_foil,
                total_value=card_total,
            )
        )

    # Calculate median
    median_price = 0.0
    if all_prices:
        all_prices.sort()
        mid = len(all_prices) // 2
        if len(all_prices) % 2 == 0:
            median_price = (all_prices[mid - 1] + all_prices[mid]) / 2
        else:
            median_price = all_prices[mid]

    # Top 5 cards by price
    card_prices.sort(key=lambda x: x[1], reverse=True)
    top_cards = card_prices[:5]

    return CollectionPriceResult(
        cards=priced_cards,
        total_value=total_value,
        total_value_foil=total_value_foil,
        cards_with_prices=cards_with_prices,
        cards_without_prices=cards_without_prices,
        median_price=median_price,
        top_cards=top_cards,
    )
