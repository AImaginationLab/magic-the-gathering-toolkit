"""MCP tools for card images and pricing."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..data.models import (
    Card,
    CardImageResponse,
    ImageUrls,
    PriceResponse,
    Prices,
    PriceSearchResponse,
    PriceSearchResult,
    PrintingInfo,
    PrintingsResponse,
    PurchaseLinks,
    RelatedLinks,
)
from ..exceptions import CardNotFoundError, ValidationError

if TYPE_CHECKING:
    from ..data.database import UnifiedDatabase

logger = logging.getLogger(__name__)


async def get_card_image(
    db: UnifiedDatabase,
    name: str,
    set_code: str | None = None,
    collector_number: str | None = None,
) -> CardImageResponse:
    """Get image URLs and pricing for a card."""
    # If specific printing requested, use set/number lookup
    if set_code and collector_number:
        card = await db.get_card_by_set_and_number(set_code, collector_number)
        if not card:
            raise CardNotFoundError(f"{name} in set {set_code}")
    else:
        card = await db.get_card_by_name(name)

    return _card_to_image_response(card)


async def get_card_printings(
    db: UnifiedDatabase,
    name: str,
) -> PrintingsResponse:
    """Get all printings of a card with images and prices.

    Args:
        db: Unified MTG database
        name: Card name to search for

    Returns:
        PrintingsResponse with all printings and their metadata
    """
    printings = await db.get_all_printings(name)

    if not printings:
        raise CardNotFoundError(name)

    return PrintingsResponse(
        card_name=name,
        printings=[_card_to_printing_info(card) for card in printings],
    )


async def get_card_price(
    db: UnifiedDatabase,
    name: str,
    set_code: str | None = None,
    collector_number: str | None = None,
) -> PriceResponse:
    """Get current price for a card."""
    # If specific printing requested, use set/number lookup
    if set_code and collector_number:
        card = await db.get_card_by_set_and_number(set_code, collector_number)
        if not card:
            identifier = f"{name} in set {set_code}"
            raise CardNotFoundError(identifier)
    else:
        card = await db.get_card_by_name(name)

    return PriceResponse(
        card_name=card.name,
        set_code=card.set_code,
        prices=Prices(
            usd=card.get_price_usd(),
            usd_foil=card.get_price_usd_foil(),
            eur=card.get_price_eur(),
            eur_foil=card.get_price_eur_foil(),
        ),
        purchase_links=PurchaseLinks(
            tcgplayer=card.purchase_tcgplayer,
            cardmarket=card.purchase_cardmarket,
            cardhoarder=card.purchase_cardhoarder,
        ),
    )


async def search_by_price(
    db: UnifiedDatabase,
    min_price: float | None = None,
    max_price: float | None = None,
    page: int = 1,
    page_size: int = 25,
) -> PriceSearchResponse:
    """Search for cards by price range."""
    if min_price is None and max_price is None:
        raise ValidationError("Provide at least min_price or max_price")

    cards = await db.search_by_price(
        min_price=min_price,
        max_price=max_price,
        page=page,
        page_size=min(page_size, 100),
    )

    return PriceSearchResponse(
        cards=[
            PriceSearchResult(
                name=card.name,
                set_code=card.set_code,
                price_usd=card.get_price_usd(),
                image=card.image_small,
            )
            for card in cards
        ],
        page=page,
        page_size=page_size,
    )


def _card_to_image_response(card: Card) -> CardImageResponse:
    """Convert a Card to a CardImageResponse."""
    return CardImageResponse(
        card_name=card.name,
        set_code=card.set_code,
        images=ImageUrls(
            small=card.image_small,
            normal=card.image_normal,
            large=card.image_large,
            png=card.image_png,
            art_crop=card.image_art_crop,
        ),
        prices=Prices(
            usd=card.get_price_usd(),
            usd_foil=card.get_price_usd_foil(),
            eur=card.get_price_eur(),
            eur_foil=card.get_price_eur_foil(),
        ),
        purchase_links=PurchaseLinks(
            tcgplayer=card.purchase_tcgplayer,
            cardmarket=card.purchase_cardmarket,
            cardhoarder=card.purchase_cardhoarder,
        ),
        related_links=RelatedLinks(
            edhrec=card.link_edhrec,
            gatherer=card.link_gatherer,
        ),
        highres_image=card.highres_image,
        full_art=card.full_art,
    )


def _card_to_printing_info(card: Card) -> PrintingInfo:
    """Convert a Card to PrintingInfo."""
    return PrintingInfo(
        uuid=card.uuid,
        set_code=card.set_code,
        collector_number=card.number,
        image=card.image_normal,
        art_crop=card.image_art_crop,
        price_usd=card.get_price_usd(),
        price_usd_foil=card.get_price_usd_foil(),
        price_eur=card.get_price_eur(),
        artist=card.artist,
        flavor_text=card.flavor,
        rarity=card.rarity,
        release_date=card.release_date,
        illustration_id=card.illustration_id,
        mana_cost=card.mana_cost,
        type_line=card.type,
        oracle_text=card.text,
        power=card.power,
        toughness=card.toughness,
        loyalty=card.loyalty,
    )
