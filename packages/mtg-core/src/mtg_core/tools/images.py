"""MCP tools for card images and pricing."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..cache import get_cached, set_cached
from ..data.models import (
    CardImageResponse,
    PriceResponse,
    PriceSearchResponse,
    PriceSearchResult,
    PrintingInfo,
    PrintingsResponse,
)
from ..exceptions import CardNotFoundError, DatabaseNotAvailableError, ValidationError

if TYPE_CHECKING:
    from ..data.database import MTGDatabase, ScryfallDatabase

logger = logging.getLogger(__name__)

# Cache namespace and TTL for printings
_PRINTINGS_CACHE_NS = "printings"
_PRINTINGS_TTL_DAYS = 7


def _require_scryfall(db: ScryfallDatabase | None) -> ScryfallDatabase:
    """Validate Scryfall database is available."""
    if db is None:
        raise DatabaseNotAvailableError("Scryfall")
    return db


async def get_card_image(
    db: ScryfallDatabase | None,
    name: str,
    set_code: str | None = None,
) -> CardImageResponse:
    """Get image URLs and pricing for a card."""
    scryfall = _require_scryfall(db)
    image = await scryfall.get_card_image(name, set_code)

    if not image:
        identifier = f"{name} in set {set_code}" if set_code else name
        raise CardNotFoundError(identifier)

    return CardImageResponse(
        card_name=image.name,
        set_code=image.set_code,
        images=image.to_image_urls(),
        prices=image.to_prices(),
        purchase_links=image.to_purchase_links(),
        related_links=image.to_related_links(),
        highres_image=image.highres_image,
        full_art=image.full_art,
    )


async def get_card_printings(
    scryfall_db: ScryfallDatabase | None,
    mtg_db: MTGDatabase | None,
    name: str,
    *,
    use_cache: bool = True,
) -> PrintingsResponse:
    """Get all printings of a card with images and prices.

    Args:
        scryfall_db: Scryfall database for images and prices
        mtg_db: MTGJson database for card metadata (artist, rarity, etc.)
        name: Card name to search for
        use_cache: Whether to use disk cache (default True)

    Returns:
        PrintingsResponse with all printings and their metadata
    """
    # Check cache first (include mtg_db availability in cache key since response differs)
    cache_key = f"{name}:mtgdb={'1' if mtg_db else '0'}"
    if use_cache:
        cached = get_cached(_PRINTINGS_CACHE_NS, cache_key, PrintingsResponse, _PRINTINGS_TTL_DAYS)
        if cached is not None:
            return cached

    scryfall = _require_scryfall(scryfall_db)
    printings = await scryfall.get_all_printings(name)

    if not printings:
        raise CardNotFoundError(name)

    # Build metadata lookup from MTGJson if available
    # Key by (set_code, collector_number) for exact match, with fallback to set_code only
    metadata_by_printing: dict[tuple[str, str], dict[str, str | None]] = {}
    metadata_by_set: dict[str, dict[str, str | None]] = {}
    # Card-level data (same for all printings)
    card_data: dict[str, str | None] = {}
    if mtg_db:
        try:
            cards = await mtg_db.get_all_printings(name)
            for card in cards:
                # Get card-level data from first card (same for all printings)
                if not card_data:
                    card_data = {
                        "mana_cost": card.mana_cost,
                        "type_line": card.type,
                        "oracle_text": card.text,
                        "power": card.power,
                        "toughness": card.toughness,
                        "loyalty": card.loyalty,
                    }
                if card.set_code:
                    metadata = {
                        "artist": card.artist,
                        "flavor_text": card.flavor,
                        "rarity": card.rarity,
                        "release_date": card.release_date,
                    }
                    # Store by (set_code, number) for exact match
                    if card.number:
                        metadata_by_printing[(card.set_code.upper(), card.number)] = metadata
                    # Also store by set_code as fallback
                    metadata_by_set[card.set_code.upper()] = metadata
        except Exception as e:
            # MTGJson metadata unavailable - continue without it
            # Scryfall data will still provide core printing info
            logger.debug("Failed to fetch MTGJson metadata for %s: %s", name, e)

    def get_metadata(set_code: str | None, collector_number: str | None) -> dict[str, str | None]:
        """Get metadata for a printing, trying exact match first."""
        if set_code and collector_number:
            exact = metadata_by_printing.get((set_code.upper(), collector_number))
            if exact:
                return exact
        if set_code:
            return metadata_by_set.get(set_code.upper(), {})
        return {}

    result = PrintingsResponse(
        card_name=name,
        printings=[
            PrintingInfo(
                uuid=p.scryfall_id,
                set_code=p.set_code,
                collector_number=p.collector_number,
                image=p.image_normal,
                art_crop=p.image_art_crop,
                price_usd=p.get_price_usd(),
                price_eur=p.get_price_eur(),
                artist=get_metadata(p.set_code, p.collector_number).get("artist"),
                flavor_text=get_metadata(p.set_code, p.collector_number).get("flavor_text"),
                rarity=get_metadata(p.set_code, p.collector_number).get("rarity"),
                release_date=get_metadata(p.set_code, p.collector_number).get("release_date"),
                illustration_id=p.illustration_id,
                mana_cost=card_data.get("mana_cost"),
                type_line=card_data.get("type_line"),
                oracle_text=card_data.get("oracle_text"),
                power=card_data.get("power"),
                toughness=card_data.get("toughness"),
                loyalty=card_data.get("loyalty"),
            )
            for p in printings
        ],
    )

    # Cache result for future use
    if use_cache:
        set_cached(_PRINTINGS_CACHE_NS, cache_key, result)

    return result


async def get_card_price(
    db: ScryfallDatabase | None,
    name: str,
    set_code: str | None = None,
) -> PriceResponse:
    """Get current price for a card."""
    scryfall = _require_scryfall(db)
    image = await scryfall.get_card_image(name, set_code)

    if not image:
        identifier = f"{name} in set {set_code}" if set_code else name
        raise CardNotFoundError(identifier)

    return PriceResponse(
        card_name=image.name,
        set_code=image.set_code,
        prices=image.to_prices(),
        purchase_links=image.to_purchase_links(),
    )


async def search_by_price(
    db: ScryfallDatabase | None,
    min_price: float | None = None,
    max_price: float | None = None,
    page: int = 1,
    page_size: int = 25,
) -> PriceSearchResponse:
    """Search for cards by price range."""
    scryfall = _require_scryfall(db)

    if min_price is None and max_price is None:
        raise ValidationError("Provide at least min_price or max_price")

    cards = await scryfall.search_by_price(
        min_price=min_price,
        max_price=max_price,
        page=page,
        page_size=min(page_size, 100),
    )

    return PriceSearchResponse(
        cards=[
            PriceSearchResult(
                name=c.name,
                set_code=c.set_code,
                price_usd=c.get_price_usd(),
                image=c.image_small,
            )
            for c in cards
        ],
        page=page,
        page_size=page_size,
    )
