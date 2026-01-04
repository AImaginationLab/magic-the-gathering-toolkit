"""Recommendation API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from mtg_core.data.models import Card, SuggestCardsResult
from mtg_core.tools.recommendations import (
    CardData,
    DeckFilters,
    DeckSuggestion,
    get_deck_finder,
)
from mtg_core.tools.recommendations.constants import THEME_KEYWORDS, TRIBAL_TYPES
from mtg_core.tools.synergy import suggest_cards

from ..models.requests import (
    FindCommandersRequest,
    FindDecksRequest,
    SuggestCardsRequest,
)

logger = logging.getLogger(__name__)


def _card_to_card_data(card: Card) -> CardData:
    """Convert a Card database model to CardData for recommendations."""
    return CardData(
        name=card.name,
        type_line=card.type,
        colors=card.colors,
        mana_cost=card.mana_cost,
        text=card.text,
        color_identity=card.color_identity,
        keywords=card.keywords,
        subtypes=card.subtypes,
        power=card.power,
        toughness=card.toughness,
        edhrec_rank=card.edhrec_rank,
        set_code=card.set_code,
    )


router = APIRouter()


class FilterOptionsResponse(BaseModel):
    """Available filter options for deck suggestions."""

    themes: list[str]
    tribals: list[str]


@router.get("/filter-options", response_model=FilterOptionsResponse)
async def get_filter_options() -> FilterOptionsResponse:
    """Get available filter options for deck suggestions (themes, tribals)."""
    return FilterOptionsResponse(
        themes=sorted(THEME_KEYWORDS.keys()),
        tribals=sorted(TRIBAL_TYPES),
    )


@router.post("/cards", response_model=SuggestCardsResult)
async def suggest_cards_for_deck(
    request: Request,
    body: SuggestCardsRequest,
) -> SuggestCardsResult:
    """Suggest cards to add to a deck based on themes and synergies."""
    db = request.app.state.db_manager.db
    user_db = request.app.state.db_manager.user

    result = await suggest_cards(
        db,
        deck_cards=body.deck_cards,
        format_legal=body.format_legal,
        budget_max=body.budget_max,
        max_results=body.max_results,
    )

    # Populate owned field if user database is available
    if user_db is not None:
        owned_cards = await user_db.get_collection_card_names()
        for suggestion in result.suggestions:
            suggestion.owned = suggestion.name in owned_cards

    return result


@router.post("/commanders", response_model=list[dict[str, Any]])
async def find_commanders(
    request: Request,
    body: FindCommandersRequest,
) -> list[dict[str, Any]]:
    """Find commanders that work well with a collection."""
    db = request.app.state.db_manager.db
    user_db = request.app.state.db_manager.user
    deck_finder = get_deck_finder()
    if not deck_finder._initialized:
        await deck_finder.initialize(db)

    # Get collection cards - either from request or from user database
    if body.use_collection:
        if user_db is None:
            return []  # User database not available
        collection_card_names = await user_db.get_collection_card_names()
    elif body.collection_cards:
        collection_card_names = set(body.collection_cards)
    else:
        return []  # No cards provided

    # Batch fetch all cards (fixes N+1 query)
    cards_by_name = await db.get_cards_by_names(list(collection_card_names))
    card_data_list = [_card_to_card_data(card) for card in cards_by_name.values()]

    if len(cards_by_name) < len(collection_card_names):
        missing = {n.lower() for n in collection_card_names} - set(cards_by_name.keys())
        logger.debug("Cards not found in database: %s", missing)

    filters = DeckFilters(
        colors=body.colors,
        creature_type=body.creature_type,
        creature_types=body.creature_types,
        theme=body.theme,
        themes=body.themes,
        format=body.format,
        set_codes=body.set_codes,
    )

    suggestions = await deck_finder.find_commander_decks(
        _collection_cards=collection_card_names,
        card_data=card_data_list,
        limit=body.limit,
        filters=filters,
    )

    # Extract commander information
    result: list[dict[str, Any]] = []
    for sug in suggestions:
        if sug.commander:
            result.append(
                {
                    "name": sug.commander,
                    "colors": sug.colors,
                    "archetype": sug.archetype,
                    "completion_pct": sug.completion_pct,
                    "reasons": sug.reasons,
                }
            )
    return result


@router.post("/decks", response_model=list[DeckSuggestion])
async def find_buildable_decks(
    request: Request,
    body: FindDecksRequest,
) -> list[DeckSuggestion]:
    """Find decks that can be built from a collection."""
    db = request.app.state.db_manager.db
    user_db = request.app.state.db_manager.user
    deck_finder = get_deck_finder()
    if not deck_finder._initialized:
        await deck_finder.initialize(db)

    # Get collection cards - either from request or from user database
    if body.use_collection:
        if user_db is None:
            return []  # User database not available
        collection_card_names = await user_db.get_collection_card_names()
    elif body.collection_cards:
        collection_card_names = set(body.collection_cards)
    else:
        return []  # No cards provided

    # Batch fetch all cards (fixes N+1 query)
    cards_by_name = await db.get_cards_by_names(list(collection_card_names))
    card_data_list = [_card_to_card_data(card) for card in cards_by_name.values()]

    if len(cards_by_name) < len(collection_card_names):
        missing = {n.lower() for n in collection_card_names} - set(cards_by_name.keys())
        logger.debug("Cards not found in database: %s", missing)

    filters = DeckFilters(
        colors=body.colors,
        creature_type=body.creature_type,
        creature_types=body.creature_types,
        theme=body.theme,
        themes=body.themes,
        set_codes=body.set_codes,
    )

    # Use find_buildable_decks which dispatches to the correct format handler
    return await deck_finder.find_buildable_decks(
        collection_cards=collection_card_names,
        format=body.format or "commander",
        card_data=card_data_list,
        min_completion=body.min_completion,
        limit=body.limit,
        filters=filters,
    )
