"""MCP tools for card operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mtg_core.data.models import (
    Card,
    CardDetail,
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
) -> SearchResult:
    """Search for Magic: The Gathering cards."""
    cards, total_count = await db.search_cards(filters)

    results = []
    for card in cards:
        summary = _card_to_summary(card)

        if scryfall:
            image = await scryfall.get_card_image(card.name, card.set_code)
            if image:
                summary.image = image.image_normal
                summary.image_small = image.image_small
                summary.price_usd = image.get_price_usd()
                summary.purchase_link = image.purchase_tcgplayer

        results.append(summary)

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
        image = await scryfall.get_card_image(card.name, card.set_code)
        if image:
            detail.images = image.to_image_urls()
            detail.prices = image.to_prices()
            detail.purchase_links = image.to_purchase_links()
            detail.related_links = image.to_related_links()

    return detail


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
        name=card.name,
        mana_cost=card.mana_cost,
        cmc=card.cmc,
        type=card.type,
        colors=card.colors or [],
        color_identity=card.color_identity or [],
        rarity=card.rarity,
        set_code=card.set_code,
        keywords=card.keywords or [],
        power=card.power,
        toughness=card.toughness,
    )


def _card_to_detail(card: Card) -> CardDetail:
    """Convert a Card to a detailed response."""
    return CardDetail(
        name=card.name,
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
