"""MCP tools for card images and pricing."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    from ..data.database import ScryfallDatabase


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
    db: ScryfallDatabase | None,
    name: str,
) -> PrintingsResponse:
    """Get all printings of a card with images and prices."""
    scryfall = _require_scryfall(db)
    printings = await scryfall.get_all_printings(name)

    if not printings:
        raise CardNotFoundError(name)

    return PrintingsResponse(
        card_name=name,
        printings=[
            PrintingInfo(
                set_code=p.set_code,
                collector_number=p.collector_number,
                image=p.image_normal,
                price_usd=p.get_price_usd(),
            )
            for p in printings
        ],
    )


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
