"""MCP tools for artist discovery with caching."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..cache import get_cached, set_cached
from ..data.models.responses import ArtistCardsResult, CardSummary

if TYPE_CHECKING:
    from ..data.database import MTGDatabase

# Cache namespace and TTL for artist cards
_ARTIST_CACHE_NS = "artist_cards"
_ARTIST_TTL_DAYS = 30  # Artist portfolios rarely change


async def get_artist_cards(
    db: MTGDatabase,
    artist_name: str,
    *,
    use_cache: bool = True,
) -> ArtistCardsResult:
    """Get all cards by an artist with caching.

    Args:
        db: MTG database connection
        artist_name: Name of the artist
        use_cache: Whether to use disk cache (default True)

    Returns:
        ArtistCardsResult with all cards by this artist
    """
    cache_key = artist_name.lower()

    # Check cache first
    if use_cache:
        cached = get_cached(_ARTIST_CACHE_NS, cache_key, ArtistCardsResult, _ARTIST_TTL_DAYS)
        if cached is not None:
            return cached

    # Fetch from database
    cards = await db.get_cards_by_artist(artist_name)

    # Convert to CardSummary for caching (smaller than full Card objects)
    summaries = [
        CardSummary(
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
        for card in cards
    ]

    result = ArtistCardsResult(
        artist_name=artist_name,
        cards=summaries,
    )

    # Cache result for future use
    if use_cache:
        set_cached(_ARTIST_CACHE_NS, cache_key, result)

    return result
