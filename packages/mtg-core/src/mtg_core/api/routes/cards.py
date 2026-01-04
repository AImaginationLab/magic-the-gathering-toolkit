"""Card API routes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request

from mtg_core.data.models import (
    CardDetail,
    PrintingsResponse,
    RulingsResponse,
    SearchCardsInput,
    SearchResult,
)
from mtg_core.exceptions import CardNotFoundError, ValidationError
from mtg_core.tools import cards as cards_tools
from mtg_core.tools import images as images_tools

from ..models.requests import (
    CardDetailsRequest,
    CardPrintingsRequest,
    CardRulingsRequest,
)

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_db(request: Request) -> UnifiedDatabase:
    """Get database from app state."""
    db: UnifiedDatabase = request.app.state.db_manager.db
    return db


@router.post("/search", response_model=SearchResult)
async def search_cards(
    request: Request,
    filters: SearchCardsInput,
) -> SearchResult:
    """Search for cards with various filters."""
    db = _get_db(request)

    # If in_collection filter is set, get collection card names
    collection_names: set[str] | None = None
    if filters.in_collection:
        user_db = request.app.state.db_manager.user
        if user_db is not None:
            collection_names = await user_db.get_collection_card_names()

    return await cards_tools.search_cards(db, filters, collection_names=collection_names)


@router.post("/details", response_model=CardDetail)
async def get_card_details(
    request: Request,
    body: CardDetailsRequest,
) -> CardDetail:
    """Get detailed information about a specific card."""
    db = _get_db(request)
    try:
        return await cards_tools.get_card(db, name=body.name)
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/rulings", response_model=RulingsResponse)
async def get_card_rulings(
    request: Request,
    body: CardRulingsRequest,
) -> RulingsResponse:
    """Get official rulings for a card."""
    db = _get_db(request)
    try:
        return await cards_tools.get_card_rulings(db, body.name)
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/printings", response_model=PrintingsResponse)
async def get_card_printings(
    request: Request,
    body: CardPrintingsRequest,
) -> PrintingsResponse:
    """Get all printings of a card across all sets."""
    db = _get_db(request)
    try:
        return await images_tools.get_card_printings(db, body.name)
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
