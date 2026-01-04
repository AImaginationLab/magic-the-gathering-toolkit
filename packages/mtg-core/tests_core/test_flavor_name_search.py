"""Tests for flavor_name search functionality.

These tests verify that searching by flavor_name (alternate card names)
works correctly. For example, searching "SpongeBob" should find
"Jodah, the Unifier" which has flavor_name "SpongeBob SquarePants".
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from mtg_core.config import Settings
from mtg_core.data.database import UnifiedDatabase, create_database
from mtg_core.data.models import SearchCardsInput
from mtg_core.tools import cards

from .conftest import get_test_db_path

# Skip tests if no database available
DB_PATH = get_test_db_path()
pytestmark = pytest.mark.skipif(
    DB_PATH is None,
    reason="MTG database not found - run create-mtg-db first",
)


@pytest.fixture
async def db() -> AsyncIterator[UnifiedDatabase]:
    """Create database connection for tests."""
    assert DB_PATH is not None
    settings = Settings(mtg_db_path=DB_PATH)
    async with create_database(settings) as database:
        yield database


class TestFlavorNameSearch:
    """Tests for searching by flavor_name (alternate card names)."""

    async def test_search_spongebob_finds_jodah(self, db: UnifiedDatabase) -> None:
        """Searching 'spongebob' should find Jodah, the Unifier.

        The Secret Lair SpongeBob card has:
        - name: "Jodah, the Unifier"
        - flavor_name: "SpongeBob SquarePants"
        """
        filters = SearchCardsInput(name="spongebob", page_size=10)
        result = await cards.search_cards(db, filters)

        assert result.total_count >= 1, "Should find at least one card"

        # Check that one of the results is the SpongeBob/Jodah card
        card_names = [card.name for card in result.cards]
        flavor_names = [card.flavor_name for card in result.cards if card.flavor_name]

        assert "Jodah, the Unifier" in card_names, (
            f"Expected 'Jodah, the Unifier' in results, got: {card_names}"
        )
        assert "SpongeBob SquarePants" in flavor_names, (
            f"Expected 'SpongeBob SquarePants' flavor_name in results, got: {flavor_names}"
        )

    async def test_search_spongebob_case_insensitive(self, db: UnifiedDatabase) -> None:
        """Flavor name search should be case-insensitive."""
        for query in ["SpongeBob", "SPONGEBOB", "spongebob", "SpOnGeBOb"]:
            filters = SearchCardsInput(name=query, page_size=10)
            result = await cards.search_cards(db, filters)

            card_names = [card.name for card in result.cards]
            assert "Jodah, the Unifier" in card_names, (
                f"Case-insensitive search for '{query}' should find Jodah"
            )

    async def test_search_regular_name_still_works(self, db: UnifiedDatabase) -> None:
        """Searching by regular name should still work."""
        filters = SearchCardsInput(name="Jodah", page_size=10)
        result = await cards.search_cards(db, filters)

        assert result.total_count >= 1, "Should find Jodah cards"
        card_names = [card.name for card in result.cards]
        assert any("Jodah" in name for name in card_names), (
            f"Should find cards with 'Jodah' in name, got: {card_names}"
        )

    async def test_flavor_name_included_in_response(self, db: UnifiedDatabase) -> None:
        """Search results should include flavor_name in the response."""
        filters = SearchCardsInput(name="spongebob", page_size=10)
        result = await cards.search_cards(db, filters)

        # Find the Jodah card
        jodah = next(
            (card for card in result.cards if card.name == "Jodah, the Unifier"),
            None,
        )
        assert jodah is not None, "Should find Jodah, the Unifier"
        assert jodah.flavor_name == "SpongeBob SquarePants", (
            f"Jodah should have SpongeBob flavor_name, got: {jodah.flavor_name}"
        )


class TestFlavorNameFTS:
    """Tests for flavor_name in full-text search (FTS)."""

    async def test_fts_finds_spongebob(self, db: UnifiedDatabase) -> None:
        """FTS search should also find cards by flavor_name."""
        from mtg_core.data.database.fts import get_fts_columns, search_cards_fts

        # Skip if FTS table doesn't have flavor_name column
        available_cols = await get_fts_columns(db._db)
        if "flavor_name" not in available_cols:
            pytest.skip("FTS table missing flavor_name column - needs database rebuild")

        # Get raw database connection for FTS test
        uuids = await search_cards_fts(db._db, "spongebob", limit=10)

        assert len(uuids) >= 1, "FTS should find at least one card for 'spongebob'"

        # Verify the found card is the SpongeBob/Jodah card
        card = await db.get_card_by_uuid(uuids[0])
        assert card.name == "Jodah, the Unifier", (
            f"FTS should find Jodah, the Unifier, got: {card.name}"
        )
        assert card.flavor_name == "SpongeBob SquarePants"
