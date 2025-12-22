"""MCP tools for set operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..data.models import Set, SetDetail, SetsResponse, SetSummary

if TYPE_CHECKING:
    from ..data.database import UnifiedDatabase


async def get_sets(
    db: UnifiedDatabase,
    name: str | None = None,
    set_type: str | None = None,
    include_online_only: bool = True,
) -> SetsResponse:
    """Get Magic: The Gathering sets."""
    if name:
        sets = await db.search_sets(name)
    else:
        sets = await db.get_all_sets(
            set_type=set_type,
            include_online_only=include_online_only,
        )

    # Apply filters if searching by name
    if name and set_type:
        type_lower = set_type.lower()
        sets = [s for s in sets if s.type and type_lower in s.type.lower()]

    if name and not include_online_only:
        sets = [s for s in sets if not s.is_online_only]

    return SetsResponse(sets=[_set_to_summary(s) for s in sets])


async def get_set(
    db: UnifiedDatabase,
    code: str,
) -> SetDetail:
    """Get detailed information about a specific set."""
    # db.get_set raises SetNotFoundError if not found
    mtg_set = await db.get_set(code)
    return _set_to_detail(mtg_set)


def _set_to_summary(mtg_set: Set) -> SetSummary:
    """Convert a Set to a summary response."""
    return SetSummary(
        code=mtg_set.code,
        name=mtg_set.name,
        type=mtg_set.type,
        release_date=mtg_set.release_date,
    )


def _set_to_detail(mtg_set: Set) -> SetDetail:
    """Convert a Set to a detailed response."""
    return SetDetail(
        code=mtg_set.code,
        name=mtg_set.name,
        type=mtg_set.type,
        release_date=mtg_set.release_date,
        block=mtg_set.block,
        base_set_size=mtg_set.base_set_size,
        total_set_size=mtg_set.total_set_size,
        is_online_only=mtg_set.is_online_only,
        is_foil_only=mtg_set.is_foil_only,
        keyrune_code=mtg_set.keyrune_code,
    )
