"""Shared fixtures and helpers for screenshot tests.

This module provides shared constants, fixtures, and helper functions
used across all screenshot test modules.

Database methods are mocked to return deterministic data for consistent snapshots.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

    from textual.pilot import Pilot


# Menu item indices (0-indexed from the first item)
# Menu order: Search, Artists, Sets, Decks, Collection
MENU_SEARCH = 0
MENU_ARTISTS = 1
MENU_SETS = 2
MENU_DECKS = 3
MENU_COLLECTION = 4

# Fixed delay for menu to open (consistent timing for animations)
MENU_OPEN_DELAY = 0.3


async def navigate_via_menu(pilot: Pilot[None], menu_index: int, delay: float = 0.3) -> None:
    """Navigate to a menu item using F10 and arrow keys.

    Args:
        pilot: The Textual pilot instance.
        menu_index: Index of the menu item (0=Artists, 1=Sets, 2=Decks, 3=Collection).
        delay: Pause delay after navigation completes.
    """
    # Open menu
    await pilot.press("f10")
    await pilot.pause(delay=MENU_OPEN_DELAY)
    # Navigate down to the desired item
    for _ in range(menu_index):
        await pilot.press("down")
    # Select item
    await pilot.press("enter")
    # Wait for screen/widget to load
    await pilot.pause(delay=delay)


# Fixed mock data for deterministic snapshots
MOCK_ARTIST = {
    "name": "Rebecca Guay",
    "card_count": 150,
    "sets_count": 45,
    "first_card_year": 1997,
    "most_recent_year": 2023,
}

MOCK_CARD = {
    "uuid": "mock-uuid-001",
    "name": "Lightning Bolt",
    "mana_cost": "{R}",
    "cmc": 1.0,
    "type_line": "Instant",
    "oracle_text": "Lightning Bolt deals 3 damage to any target.",
    "colors": ["R"],
    "color_identity": ["R"],
    "rarity": "common",
    "set_code": "LEB",
    "set_name": "Limited Edition Beta",
    "collector_number": "161",
    "power": None,
    "toughness": None,
    "loyalty": None,
    "keywords": [],
    "legalities": [
        {"format": "vintage", "legality": "Legal"},
        {"format": "legacy", "legality": "Legal"},
        {"format": "modern", "legality": "Legal"},
    ],
    "edhrec_rank": 1,
}

MOCK_SEARCH_RESULTS = [
    {**MOCK_CARD, "uuid": f"mock-uuid-{i:03d}", "collector_number": str(160 + i)} for i in range(10)
]

MOCK_ARTISTS = [
    {
        "name": "Rebecca Guay",
        "card_count": 150,
        "sets_count": 45,
        "first_card_year": 1997,
        "most_recent_year": 2023,
    },
    {
        "name": "Terese Nielsen",
        "card_count": 200,
        "sets_count": 50,
        "first_card_year": 1996,
        "most_recent_year": 2020,
    },
    {
        "name": "John Avon",
        "card_count": 180,
        "sets_count": 55,
        "first_card_year": 1996,
        "most_recent_year": 2023,
    },
]

MOCK_SETS = [
    {
        "code": "LEB",
        "name": "Limited Edition Beta",
        "release_date": "1993-10-01",
        "set_type": "core",
        "card_count": 302,
    },
    {
        "code": "ARN",
        "name": "Arabian Nights",
        "release_date": "1993-12-01",
        "set_type": "expansion",
        "card_count": 92,
    },
    {
        "code": "ATQ",
        "name": "Antiquities",
        "release_date": "1994-03-01",
        "set_type": "expansion",
        "card_count": 100,
    },
]


def _create_mock_artist_summary():
    """Create a mock ArtistSummary."""
    from mtg_core.data.models.responses import ArtistSummary

    return ArtistSummary(**MOCK_ARTIST)


def _create_mock_card():
    """Create a mock Card."""
    from mtg_core.data.models.card import Card

    return Card(**MOCK_CARD)


def _create_mock_search_results():
    """Create mock search results."""
    from mtg_core.data.models.card import Card

    return [Card(**data) for data in MOCK_SEARCH_RESULTS]


def _create_mock_artists():
    """Create mock artist list."""
    from mtg_core.data.models.responses import ArtistSummary

    return [ArtistSummary(**data) for data in MOCK_ARTISTS]


@pytest.fixture
def mock_database_for_snapshots() -> Iterator[None]:
    """Mock database methods to return deterministic data for snapshots.

    This fixture automatically patches database methods that return
    non-deterministic data (random artists, search results, etc.)
    to ensure snapshot tests produce consistent output across platforms.
    """
    mock_artist = _create_mock_artist_summary()
    mock_card = _create_mock_card()
    mock_results = _create_mock_search_results()
    mock_artists = _create_mock_artists()

    with (
        patch(
            "mtg_core.data.database.UnifiedDatabase.get_random_artist_for_spotlight",
            new_callable=AsyncMock,
            return_value=mock_artist,
        ),
        patch(
            "mtg_core.data.database.UnifiedDatabase.search_cards",
            new_callable=AsyncMock,
            return_value=(mock_results, len(mock_results)),
        ),
        patch(
            "mtg_core.data.database.UnifiedDatabase.get_card_by_name",
            new_callable=AsyncMock,
            return_value=mock_card,
        ),
        patch(
            "mtg_core.data.database.UnifiedDatabase.get_all_artists",
            new_callable=AsyncMock,
            return_value=mock_artists,
        ),
        patch(
            "mtg_core.data.database.UnifiedDatabase.search_artists",
            new_callable=AsyncMock,
            return_value=mock_artists,
        ),
    ):
        yield
