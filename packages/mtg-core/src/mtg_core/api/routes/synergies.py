"""Synergy API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request

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


@router.post("/find", response_model=FindSynergiesResult)
async def find_card_synergies(
    request: Request,
    body: FindSynergiesRequest,
) -> FindSynergiesResult:
    """Find cards that synergize with a given card."""
    db = _get_db(request)
    try:
        return await find_synergies(
            db,
            card_name=body.card_name,
            max_results=body.limit,
            format_legal=body.format_legal,
        )
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
