"""Artist API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from mtg_core.data.models.responses import ArtistCardsResult, ArtistSummary
from mtg_core.tools import artists as artists_tools

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase

router = APIRouter()


def _get_db(request: Request) -> UnifiedDatabase:
    """Get database from app state."""
    db: UnifiedDatabase = request.app.state.db_manager.db
    return db


class ArtistsListResponse(BaseModel):
    """Response for listing artists."""

    artists: list[ArtistSummary]
    total_count: int
    limit: int
    offset: int = Field(default=0, description="Offset for pagination")


@router.get("", response_model=ArtistsListResponse)
async def list_artists(
    request: Request,
    query: str | None = Query(default=None, description="Search artists by name"),
    min_cards: int = Query(default=1, ge=1, description="Minimum number of cards"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
) -> ArtistsListResponse:
    """List all artists with optional filtering and pagination.

    Returns artists sorted by card count (descending).
    """
    db = _get_db(request)

    if query:
        all_artists = await db.search_artists(query, min_cards=min_cards)
    else:
        all_artists = await db.get_all_artists(min_cards=min_cards)

    total_count = len(all_artists)
    paginated = all_artists[offset : offset + limit]

    return ArtistsListResponse(
        artists=paginated,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


@router.get("/{name}/cards", response_model=ArtistCardsResult)
async def get_artist_cards(
    request: Request,
    name: str,
) -> ArtistCardsResult:
    """Get all cards by a specific artist.

    Returns unique cards (one per card name) sorted by release date.
    """
    db = _get_db(request)
    return await artists_tools.get_artist_cards(db, name)
