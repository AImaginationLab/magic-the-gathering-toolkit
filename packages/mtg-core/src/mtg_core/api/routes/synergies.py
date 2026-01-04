"""Synergy API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request

from mtg_core.data.database import UserDatabase
from mtg_core.data.models import FindSynergiesResult
from mtg_core.exceptions import CardNotFoundError
from mtg_core.tools.synergy import find_synergies

from ..models.requests import FindSynergiesRequest

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase

router = APIRouter()


def _get_db(request: Request) -> UnifiedDatabase:
    """Get database from app state."""
    db: UnifiedDatabase = request.app.state.db_manager.db
    return db


def _get_user_db(request: Request) -> UserDatabase | None:
    """Get user database from app state (may be None)."""
    user_db: UserDatabase | None = request.app.state.db_manager.user
    return user_db


@router.post("/find", response_model=FindSynergiesResult)
async def find_card_synergies(
    request: Request,
    body: FindSynergiesRequest,
) -> FindSynergiesResult:
    """Find cards that synergize with a given card."""
    db = _get_db(request)
    user_db = _get_user_db(request)

    try:
        result = await find_synergies(
            db,
            card_name=body.card_name,
            max_results=body.limit,
            format_legal=body.format_legal,
        )
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Populate owned field if user database is available
    if user_db is not None:
        owned_cards = await user_db.get_collection_card_names()
        for synergy in result.synergies:
            synergy.owned = synergy.name in owned_cards

    return result
