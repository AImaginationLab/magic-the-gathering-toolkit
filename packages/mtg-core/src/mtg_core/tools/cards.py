"""MCP tools for card operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mtg_core.data.models import (
    Card,
    CardDetail,
    CardSummary,
    ImageUrls,
    LegalitiesResponse,
    Prices,
    PurchaseLinks,
    RelatedLinks,
    RulingEntry,
    RulingsResponse,
    SearchCardsInput,
    SearchResult,
)
from mtg_core.exceptions import ValidationError

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase


async def search_cards(
    db: UnifiedDatabase,
    filters: SearchCardsInput,
    collection_names: set[str] | None = None,
    owned_cards: set[str] | None = None,
) -> SearchResult:
    """Search for Magic: The Gathering cards.

    Args:
        db: Unified MTG database connection
        filters: Search filters
        collection_names: If provided, only return cards with names in this set
        owned_cards: If provided, populate the `owned` field on results

    Returns:
        SearchResult with matching cards
    """
    cards, total_count = await db.search_cards(filters, collection_names=collection_names)
    results = [_card_to_summary(card) for card in cards]

    # Populate owned field if owned_cards set is provided
    if owned_cards is not None:
        for result in results:
            result.owned = result.name in owned_cards

    return SearchResult(
        cards=results,
        page=filters.page,
        page_size=filters.page_size,
        total_count=total_count,
    )


async def get_card(
    db: UnifiedDatabase,
    name: str | None = None,
    uuid: str | None = None,
) -> CardDetail:
    """Get detailed information about a specific card."""
    if not name and not uuid:
        raise ValidationError("Provide either 'name' or 'uuid'")

    # get_card_by_uuid and get_card_by_name raise CardNotFoundError if not found
    if uuid:
        card = await db.get_card_by_uuid(uuid)
    else:
        card = await db.get_card_by_name(name)  # type: ignore[arg-type]

    return _card_to_detail(card)


async def get_card_rulings(
    db: UnifiedDatabase,
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
    db: UnifiedDatabase,
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
        legalities=legalities,
    )


async def get_random_card(
    db: UnifiedDatabase,
) -> CardDetail:
    """Get a random Magic card."""
    card = await db.get_random_card()
    return _card_to_detail(card)


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
        # Images and prices from unified database
        image=card.image_normal,
        image_small=card.image_small,
        price_usd=card.get_price_usd(),
        purchase_link=card.purchase_tcgplayer,
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
        # Images and prices from unified database
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
    )
