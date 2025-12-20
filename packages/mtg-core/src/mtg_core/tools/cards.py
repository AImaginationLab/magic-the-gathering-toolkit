"""MCP tools for card operations."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from mtg_core.data.models import (
    Card,
    CardDetail,
    CardImage,
    CardSummary,
    LegalitiesResponse,
    RulingEntry,
    RulingsResponse,
    SearchCardsInput,
    SearchResult,
)
from mtg_core.exceptions import ValidationError

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase, ScryfallDatabase


async def search_cards(
    db: MTGDatabase,
    scryfall: ScryfallDatabase | None,
    filters: SearchCardsInput,
    use_fts: bool = True,
) -> SearchResult:
    """Search for Magic: The Gathering cards.

    Args:
        db: MTG database connection
        scryfall: Optional Scryfall database for images/prices
        filters: Search filters
        use_fts: If True, use FTS5 for text searches when available

    Returns:
        SearchResult with matching cards
    """
    # Use FTS-enhanced search when text filter is provided
    if use_fts and filters.text:
        cards, total_count = await db.search_cards_with_fts(filters, use_fts=True)
    else:
        cards, total_count = await db.search_cards(filters)

    results = [_card_to_summary(card) for card in cards]

    if scryfall:

        async def _enrich_with_scryfall(summary: CardSummary, card: Card) -> None:
            image = await scryfall.get_card_image(card.name, card.set_code, card.number)
            if image:
                summary.image = image.image_normal
                summary.image_small = image.image_small
                summary.price_usd = image.get_price_usd()
                summary.purchase_link = image.purchase_tcgplayer

        await asyncio.gather(
            *[
                _enrich_with_scryfall(summary, card)
                for summary, card in zip(results, cards, strict=True)
            ],
            return_exceptions=True,
        )

    return SearchResult(
        cards=results,
        page=filters.page,
        page_size=filters.page_size,
        total_count=total_count,
    )


async def get_card(
    db: MTGDatabase,
    scryfall: ScryfallDatabase | None,
    name: str | None = None,
    uuid: str | None = None,
) -> CardDetail:
    """Get detailed information about a specific card."""
    if not name and not uuid:
        raise ValidationError("Provide either 'name' or 'uuid'")

    # get_card_by_uuid and get_card_by_name raise CardNotFoundError if not found
    card = await db.get_card_by_uuid(uuid) if uuid else await db.get_card_by_name(name)  # type: ignore[arg-type]

    detail = _card_to_detail(card)

    if scryfall:
        # Try exact printing match first (name + set + number)
        image = await scryfall.get_card_image(card.name, card.set_code, card.number)

        # Check if we got the right printing (same set) or if Scryfall fell back
        if image and image.set_code and image.set_code.upper() != (card.set_code or "").upper():
            # Scryfall didn't have our exact set - find another printing by same artist
            image = await _find_image_by_artist(db, scryfall, card)

        if image:
            detail.images = image.to_image_urls()
            detail.prices = image.to_prices()
            detail.purchase_links = image.to_purchase_links()
            detail.related_links = image.to_related_links()

    return detail


async def _find_image_by_artist(
    db: MTGDatabase,
    scryfall: ScryfallDatabase,
    card: Card,
) -> CardImage | None:
    """Find a Scryfall image matching the card's artist.

    When Scryfall doesn't have the exact printing, find another printing
    by the same artist that Scryfall does have.
    """
    if not card.artist:
        return None

    # Get all printings from MTGJson
    printings = await db.get_all_printings(card.name)

    # Find printings by the same artist
    same_artist_printings = [p for p in printings if p.artist == card.artist]

    # Try each printing until we find one Scryfall has
    for printing in same_artist_printings:
        if printing.set_code == card.set_code:
            continue  # Skip the one we already tried

        image = await scryfall.get_card_image(printing.name, printing.set_code, printing.number)
        if image and image.set_code and image.set_code.upper() == (printing.set_code or "").upper():
            return image

    return None


async def get_card_rulings(
    db: MTGDatabase,
    name: str,
) -> RulingsResponse:
    """Get official rulings for a card."""
    rulings = await db.get_card_rulings(name)

    if not rulings:
        # Verify card exists - raises CardNotFoundError if not
        await db.get_card_by_name(name, include_extras=False)
        return RulingsResponse(
            card_name=name,
            rulings=[],
            note="No rulings found for this card",
        )

    return RulingsResponse(
        card_name=name,
        rulings=[RulingEntry(date=r.date, text=r.text) for r in rulings],
    )


async def get_card_legalities(
    db: MTGDatabase,
    name: str,
) -> LegalitiesResponse:
    """Get format legalities for a card."""
    legalities = await db.get_card_legalities(name)

    if not legalities:
        # Verify card exists - raises CardNotFoundError if not
        await db.get_card_by_name(name, include_extras=False)
        return LegalitiesResponse(
            card_name=name,
            legalities={},
            note="No legality data found for this card",
        )

    return LegalitiesResponse(
        card_name=name,
        legalities={leg.format: leg.legality for leg in legalities},
    )


async def get_random_card(
    db: MTGDatabase,
    scryfall: ScryfallDatabase | None,
) -> CardDetail:
    """Get a random Magic card."""
    card = await db.get_random_card()

    detail = _card_to_detail(card)

    if scryfall:
        image = await scryfall.get_card_image(card.name)
        if image:
            detail.images = image.to_image_urls()
            detail.prices = image.to_prices()

    return detail


def _card_to_summary(card: Card) -> CardSummary:
    """Convert a Card to a summary response."""
    return CardSummary(
        uuid=card.uuid,
        name=card.name,
        flavor_name=card.flavor_name,
        mana_cost=card.mana_cost,
        cmc=card.cmc,
        type=card.type,
        colors=card.colors or [],
        color_identity=card.color_identity or [],
        rarity=card.rarity,
        set_code=card.set_code,
        collector_number=card.number,
        keywords=card.keywords or [],
        power=card.power,
        toughness=card.toughness,
    )


def _card_to_detail(card: Card) -> CardDetail:
    """Convert a Card to a detailed response."""
    return CardDetail(
        name=card.name,
        flavor_name=card.flavor_name,
        uuid=card.uuid,
        mana_cost=card.mana_cost,
        cmc=card.cmc,
        colors=card.colors or [],
        color_identity=card.color_identity or [],
        type=card.type,
        supertypes=card.supertypes or [],
        types=card.types or [],
        subtypes=card.subtypes or [],
        text=card.text,
        flavor=card.flavor,
        rarity=card.rarity,
        set_code=card.set_code,
        number=card.number,
        artist=card.artist,
        layout=card.layout,
        keywords=card.keywords or [],
        power=card.power,
        toughness=card.toughness,
        loyalty=card.loyalty,
        defense=card.defense,
        edhrec_rank=card.edhrec_rank,
        legalities={leg.format: leg.legality for leg in card.legalities}
        if card.legalities
        else None,
        rulings_count=len(card.rulings) if card.rulings else None,
    )
