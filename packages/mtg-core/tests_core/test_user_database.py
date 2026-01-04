"""Tests for UserDatabase class.

Comprehensive test suite covering:
- Deck CRUD operations
- Deck card management
- Collection management
- Deck tags
- Statistics queries
- Migration handling
- Concurrency limits
"""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

import pytest

from mtg_core.data.database.user import (
    UserDatabase,
)


@pytest.fixture
async def db() -> AsyncIterator[UserDatabase]:
    """Create a temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_user.db"
        user_db = UserDatabase(db_path, max_connections=5)
        await user_db.connect()
        yield user_db
        await user_db.close()


@pytest.fixture
async def db_with_deck(db: UserDatabase) -> AsyncIterator[tuple[UserDatabase, int]]:
    """Create a test database with a deck."""
    deck_id = await db.create_deck(
        name="Test Deck",
        format="standard",
        commander="Sol Ring",
        description="Test deck for testing",
    )
    yield db, deck_id


@pytest.fixture
async def db_with_collection(db: UserDatabase) -> AsyncIterator[UserDatabase]:
    """Create a test database with collection cards."""
    await db.add_to_collection("Lightning Bolt", quantity=4, foil_quantity=1)
    await db.add_to_collection("Counterspell", quantity=3)
    await db.add_to_collection("Sol Ring", quantity=2, foil_quantity=2)
    yield db


class TestDatabaseConnection:
    """Tests for database connection and initialization."""

    async def test_connect_creates_schema(self, db: UserDatabase) -> None:
        """Connecting should create all tables."""
        # Verify tables exist
        async with db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ) as cursor:
            tables = [row["name"] for row in await cursor.fetchall()]

        expected_tables = {
            "collection_cards",
            "collection_history",
            "deck_cards",
            "deck_tags",
            "decks",
            "schema_version",
        }
        assert expected_tables.issubset(set(tables)), (
            f"Missing tables: {expected_tables - set(tables)}"
        )

    async def test_schema_version_set(self, db: UserDatabase) -> None:
        """Schema version should be set correctly."""
        async with db.conn.execute("SELECT version FROM schema_version") as cursor:
            row = await cursor.fetchone()
            assert row is not None
            assert row["version"] == 6

    async def test_foreign_keys_enabled(self, db: UserDatabase) -> None:
        """Foreign keys should be enabled."""
        async with db.conn.execute("PRAGMA foreign_keys") as cursor:
            row = await cursor.fetchone()
            assert row[0] == 1

    async def test_close_connection(self, db: UserDatabase) -> None:
        """Closing should set connection to None."""
        await db.close()
        assert db._conn is None

    async def test_conn_property_raises_when_not_connected(self) -> None:
        """Accessing conn property when not connected should raise."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            user_db = UserDatabase(db_path)

            with pytest.raises(RuntimeError, match="not connected"):
                _ = user_db.conn


class TestDeckCRUD:
    """Tests for deck creation, retrieval, update, and deletion."""

    async def test_create_deck_minimal(self, db: UserDatabase) -> None:
        """Create a deck with minimal information."""
        deck_id = await db.create_deck(name="Minimal Deck")
        assert deck_id > 0

        deck = await db.get_deck(deck_id)
        assert deck is not None
        assert deck.name == "Minimal Deck"
        assert deck.format is None
        assert deck.commander is None
        assert deck.description is None

    async def test_create_deck_full(self, db: UserDatabase) -> None:
        """Create a deck with all metadata."""
        deck_id = await db.create_deck(
            name="Full Deck",
            format="commander",
            commander="Atraxa, Praetors' Voice",
            description="Four-color goodstuff",
        )

        deck = await db.get_deck(deck_id)
        assert deck is not None
        assert deck.name == "Full Deck"
        assert deck.format == "commander"
        assert deck.commander == "Atraxa, Praetors' Voice"
        assert deck.description == "Four-color goodstuff"
        assert isinstance(deck.created_at, datetime)
        assert isinstance(deck.updated_at, datetime)

    async def test_get_deck_nonexistent(self, db: UserDatabase) -> None:
        """Getting a nonexistent deck should return None."""
        deck = await db.get_deck(99999)
        assert deck is None

    async def test_update_deck_partial(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Update only some deck fields."""
        db, deck_id = db_with_deck

        await db.update_deck(deck_id, name="Updated Name")

        deck = await db.get_deck(deck_id)
        assert deck is not None
        assert deck.name == "Updated Name"
        assert deck.format == "standard"
        assert deck.commander == "Sol Ring"

    async def test_update_deck_all_fields(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Update all deck fields."""
        db, deck_id = db_with_deck

        await db.update_deck(
            deck_id,
            name="New Name",
            format="modern",
            commander="Urza, Lord High Artificer",
            description="New description",
        )

        deck = await db.get_deck(deck_id)
        assert deck is not None
        assert deck.name == "New Name"
        assert deck.format == "modern"
        assert deck.commander == "Urza, Lord High Artificer"
        assert deck.description == "New description"

    async def test_update_deck_no_fields(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Updating with no fields should do nothing."""
        db, deck_id = db_with_deck

        original = await db.get_deck(deck_id)
        await db.update_deck(deck_id)
        updated = await db.get_deck(deck_id)

        assert original is not None
        assert updated is not None
        assert original.name == updated.name

    async def test_delete_deck_existing(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Deleting an existing deck should return True."""
        db, deck_id = db_with_deck

        deleted = await db.delete_deck(deck_id)
        assert deleted is True

        deck = await db.get_deck(deck_id)
        assert deck is None

    async def test_delete_deck_nonexistent(self, db: UserDatabase) -> None:
        """Deleting a nonexistent deck should return False."""
        deleted = await db.delete_deck(99999)
        assert deleted is False

    async def test_delete_deck_cascades_cards(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Deleting a deck should cascade delete cards."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4)
        await db.add_card(deck_id, "Counterspell", quantity=2)

        await db.delete_deck(deck_id)

        # Verify cards are deleted
        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 0

    async def test_list_decks_empty(self, db: UserDatabase) -> None:
        """Listing decks when none exist should return empty list."""
        decks = await db.list_decks()
        assert decks == []

    async def test_list_decks_with_cards(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """List decks should include card counts."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4)
        await db.add_card(deck_id, "Counterspell", quantity=2)
        await db.add_card(deck_id, "Force of Will", quantity=1, sideboard=True)

        decks = await db.list_decks()
        assert len(decks) == 1

        deck = decks[0]
        assert deck.id == deck_id
        assert deck.name == "Test Deck"
        assert deck.card_count == 6
        assert deck.sideboard_count == 1
        assert deck.format == "standard"
        assert deck.commander == "Sol Ring"

    async def test_list_decks_ordered_by_updated_at(self, db: UserDatabase) -> None:
        """List decks should be ordered by updated_at DESC."""
        deck1_id = await db.create_deck(name="Deck 1")
        await asyncio.sleep(0.01)
        await db.create_deck(name="Deck 2")
        await asyncio.sleep(0.01)
        await db.update_deck(deck1_id, description="Updated")

        decks = await db.list_decks()
        assert len(decks) == 2
        assert decks[0].name == "Deck 1"
        assert decks[1].name == "Deck 2"


class TestDeckCards:
    """Tests for deck card operations."""

    async def test_add_card_new(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Add a new card to a deck."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4)

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].card_name == "Lightning Bolt"
        assert cards[0].quantity == 4
        assert cards[0].is_sideboard is False

    async def test_add_card_with_printing(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Add a card with set and collector number."""
        db, deck_id = db_with_deck

        await db.add_card(
            deck_id,
            "Lightning Bolt",
            quantity=2,
            set_code="LEA",
            collector_number="161",
        )

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].set_code == "LEA"
        assert cards[0].collector_number == "161"

    async def test_add_card_to_sideboard(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Add a card to sideboard."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Force of Will", quantity=3, sideboard=True)

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].is_sideboard is True

    async def test_add_card_as_commander(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Add a card as commander."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Atraxa, Praetors' Voice", quantity=1, is_commander=True)

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].is_commander is True

    async def test_add_card_existing_increases_quantity(
        self, db_with_deck: tuple[UserDatabase, int]
    ) -> None:
        """Adding same card should increase quantity."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=2)
        await db.add_card(deck_id, "Lightning Bolt", quantity=2)

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].quantity == 4

    async def test_add_card_existing_updates_printing(
        self, db_with_deck: tuple[UserDatabase, int]
    ) -> None:
        """Adding same card with new printing should update printing."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=2, set_code="LEA")
        await db.add_card(
            deck_id, "Lightning Bolt", quantity=2, set_code="M11", collector_number="146"
        )

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].set_code == "M11"
        assert cards[0].collector_number == "146"

    async def test_add_card_mainboard_and_sideboard_separate(
        self, db_with_deck: tuple[UserDatabase, int]
    ) -> None:
        """Same card in mainboard and sideboard are separate entries."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4, sideboard=False)
        await db.add_card(deck_id, "Lightning Bolt", quantity=2, sideboard=True)

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 2

    async def test_remove_card_existing(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Remove an existing card."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4)
        removed = await db.remove_card(deck_id, "Lightning Bolt")

        assert removed is True
        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 0

    async def test_remove_card_nonexistent(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Removing nonexistent card should return False."""
        db, deck_id = db_with_deck

        removed = await db.remove_card(deck_id, "Nonexistent Card")
        assert removed is False

    async def test_remove_card_from_sideboard(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Remove a card from sideboard only."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4, sideboard=False)
        await db.add_card(deck_id, "Lightning Bolt", quantity=2, sideboard=True)

        removed = await db.remove_card(deck_id, "Lightning Bolt", sideboard=True)

        assert removed is True
        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].is_sideboard is False

    async def test_set_quantity(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Set quantity of a card."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=2)
        await db.set_quantity(deck_id, "Lightning Bolt", quantity=4)

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].quantity == 4

    async def test_set_quantity_zero_removes_card(
        self, db_with_deck: tuple[UserDatabase, int]
    ) -> None:
        """Setting quantity to 0 should remove card."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4)
        await db.set_quantity(deck_id, "Lightning Bolt", quantity=0)

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 0

    async def test_set_quantity_negative_removes_card(
        self, db_with_deck: tuple[UserDatabase, int]
    ) -> None:
        """Setting quantity to negative should remove card."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4)
        await db.set_quantity(deck_id, "Lightning Bolt", quantity=-1)

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 0

    async def test_move_to_sideboard_new(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Move a card to sideboard when not already there."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4, sideboard=False)
        await db.move_to_sideboard(deck_id, "Lightning Bolt")

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].is_sideboard is True
        assert cards[0].quantity == 4

    async def test_move_to_sideboard_existing(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Move to sideboard when card already in sideboard should merge."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4, sideboard=False)
        await db.add_card(deck_id, "Lightning Bolt", quantity=2, sideboard=True)
        await db.move_to_sideboard(deck_id, "Lightning Bolt")

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].is_sideboard is True
        assert cards[0].quantity == 6

    async def test_move_to_mainboard_new(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Move a card to mainboard when not already there."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=3, sideboard=True)
        await db.move_to_mainboard(deck_id, "Lightning Bolt")

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].is_sideboard is False
        assert cards[0].quantity == 3

    async def test_move_to_mainboard_existing(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Move to mainboard when card already in mainboard should merge."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=2, sideboard=False)
        await db.add_card(deck_id, "Lightning Bolt", quantity=3, sideboard=True)
        await db.move_to_mainboard(deck_id, "Lightning Bolt")

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].is_sideboard is False
        assert cards[0].quantity == 5

    async def test_get_deck_cards_ordered(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Get deck cards should be ordered by sideboard then name."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Counterspell", quantity=2, sideboard=False)
        await db.add_card(deck_id, "Lightning Bolt", quantity=4, sideboard=False)
        await db.add_card(deck_id, "Force of Will", quantity=1, sideboard=True)

        cards = await db.get_deck_cards(deck_id)
        assert len(cards) == 3
        assert cards[0].card_name == "Counterspell"
        assert cards[1].card_name == "Lightning Bolt"
        assert cards[2].card_name == "Force of Will"


class TestDeckQueries:
    """Tests for deck query operations."""

    async def test_find_decks_with_card_single_deck(
        self, db_with_deck: tuple[UserDatabase, int]
    ) -> None:
        """Find decks containing a specific card."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4)

        decks = await db.find_decks_with_card("Lightning Bolt")
        assert len(decks) == 1
        assert decks[0].id == deck_id

    async def test_find_decks_with_card_multiple_decks(self, db: UserDatabase) -> None:
        """Find card in multiple decks."""
        deck1_id = await db.create_deck(name="Deck 1")
        deck2_id = await db.create_deck(name="Deck 2")

        await db.add_card(deck1_id, "Lightning Bolt", quantity=4)
        await db.add_card(deck2_id, "Lightning Bolt", quantity=2)

        decks = await db.find_decks_with_card("Lightning Bolt")
        assert len(decks) == 2

    async def test_find_decks_with_card_not_found(self, db: UserDatabase) -> None:
        """Find card that isn't in any deck."""
        decks = await db.find_decks_with_card("Nonexistent Card")
        assert len(decks) == 0

    async def test_get_deck_card_count_single(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Get card count for a card in one location."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4)

        count = await db.get_deck_card_count(deck_id, "Lightning Bolt")
        assert count == 4

    async def test_get_deck_card_count_mainboard_and_sideboard(
        self, db_with_deck: tuple[UserDatabase, int]
    ) -> None:
        """Get card count should sum mainboard and sideboard."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4, sideboard=False)
        await db.add_card(deck_id, "Lightning Bolt", quantity=2, sideboard=True)

        count = await db.get_deck_card_count(deck_id, "Lightning Bolt")
        assert count == 6

    async def test_get_deck_card_count_not_found(
        self, db_with_deck: tuple[UserDatabase, int]
    ) -> None:
        """Get card count for card not in deck should return 0."""
        db, deck_id = db_with_deck

        count = await db.get_deck_card_count(deck_id, "Nonexistent Card")
        assert count == 0


class TestDeckTags:
    """Tests for deck tag operations."""

    async def test_add_tag(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Add a tag to a deck."""
        db, deck_id = db_with_deck

        await db.add_tag(deck_id, "competitive")

        tags = await db.get_deck_tags(deck_id)
        assert tags == ["competitive"]

    async def test_add_multiple_tags(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Add multiple tags to a deck."""
        db, deck_id = db_with_deck

        await db.add_tag(deck_id, "competitive")
        await db.add_tag(deck_id, "aggro")
        await db.add_tag(deck_id, "budget")

        tags = await db.get_deck_tags(deck_id)
        assert tags == ["aggro", "budget", "competitive"]

    async def test_add_duplicate_tag(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Adding duplicate tag should be idempotent."""
        db, deck_id = db_with_deck

        await db.add_tag(deck_id, "competitive")
        await db.add_tag(deck_id, "competitive")

        tags = await db.get_deck_tags(deck_id)
        assert tags == ["competitive"]

    async def test_remove_tag(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Remove a tag from a deck."""
        db, deck_id = db_with_deck

        await db.add_tag(deck_id, "competitive")
        await db.add_tag(deck_id, "aggro")
        await db.remove_tag(deck_id, "competitive")

        tags = await db.get_deck_tags(deck_id)
        assert tags == ["aggro"]

    async def test_get_deck_tags_empty(self, db_with_deck: tuple[UserDatabase, int]) -> None:
        """Get tags for deck with no tags."""
        db, deck_id = db_with_deck

        tags = await db.get_deck_tags(deck_id)
        assert tags == []

    async def test_find_decks_by_tag(self, db: UserDatabase) -> None:
        """Find decks with a specific tag."""
        deck1_id = await db.create_deck(name="Deck 1")
        deck2_id = await db.create_deck(name="Deck 2")
        deck3_id = await db.create_deck(name="Deck 3")

        await db.add_tag(deck1_id, "competitive")
        await db.add_tag(deck2_id, "competitive")
        await db.add_tag(deck3_id, "casual")

        decks = await db.find_decks_by_tag("competitive")
        assert len(decks) == 2

        names = {deck.name for deck in decks}
        assert names == {"Deck 1", "Deck 2"}

    async def test_find_decks_by_tag_not_found(self, db: UserDatabase) -> None:
        """Find decks by tag that doesn't exist."""
        decks = await db.find_decks_by_tag("nonexistent")
        assert len(decks) == 0


class TestCollectionOperations:
    """Tests for collection card operations."""

    async def test_add_to_collection_new(self, db: UserDatabase) -> None:
        """Add a new card to collection."""
        await db.add_to_collection("Lightning Bolt", quantity=4)

        card = await db.get_collection_card("Lightning Bolt")
        assert card is not None
        assert card.card_name == "Lightning Bolt"
        assert card.quantity == 4
        assert card.foil_quantity == 0

    async def test_add_to_collection_with_foils(self, db: UserDatabase) -> None:
        """Add a card with foils."""
        await db.add_to_collection("Lightning Bolt", quantity=4, foil_quantity=2)

        card = await db.get_collection_card("Lightning Bolt")
        assert card is not None
        assert card.quantity == 4
        assert card.foil_quantity == 2

    async def test_add_to_collection_with_printing(self, db: UserDatabase) -> None:
        """Add a card with set and collector number."""
        await db.add_to_collection(
            "Lightning Bolt", quantity=4, set_code="LEA", collector_number="161"
        )

        card = await db.get_collection_card("Lightning Bolt")
        assert card is not None
        assert card.set_code == "LEA"
        assert card.collector_number == "161"

    async def test_add_to_collection_existing_increases_quantity(self, db: UserDatabase) -> None:
        """Adding same card with same printing should increase quantity."""
        # Must specify set_code and collector_number for conflict detection
        # (NULL values don't conflict in SQLite unique constraints)
        await db.add_to_collection(
            "Lightning Bolt", quantity=2, set_code="LEA", collector_number="161"
        )
        await db.add_to_collection(
            "Lightning Bolt", quantity=2, foil_quantity=1, set_code="LEA", collector_number="161"
        )

        card = await db.get_collection_card(
            "Lightning Bolt", set_code="LEA", collector_number="161"
        )
        assert card is not None
        assert card.quantity == 4
        assert card.foil_quantity == 1

    async def test_add_to_collection_logs_history(self, db: UserDatabase) -> None:
        """Adding to collection should log history."""
        await db.add_to_collection("Lightning Bolt", quantity=4, foil_quantity=1)

        history = await db.get_collection_history(limit=10)
        assert len(history) == 1
        assert history[0].card_name == "Lightning Bolt"
        assert history[0].action == "add"
        assert history[0].quantity_change == 4
        assert history[0].foil_quantity_change == 1

    async def test_remove_from_collection_existing(self, db_with_collection: UserDatabase) -> None:
        """Remove an existing card from collection."""
        removed = await db_with_collection.remove_from_collection("Lightning Bolt")
        assert removed is True

        card = await db_with_collection.get_collection_card("Lightning Bolt")
        assert card is None

    async def test_remove_from_collection_nonexistent(self, db: UserDatabase) -> None:
        """Removing nonexistent card should return False."""
        removed = await db.remove_from_collection("Nonexistent Card")
        assert removed is False

    async def test_remove_from_collection_logs_history(
        self, db_with_collection: UserDatabase
    ) -> None:
        """Removing from collection should log history."""
        await db_with_collection.remove_from_collection("Lightning Bolt")

        history = await db_with_collection.get_collection_history(limit=10, action="remove")
        assert len(history) == 1
        assert history[0].card_name == "Lightning Bolt"
        assert history[0].action == "remove"
        assert history[0].quantity_change == -4
        assert history[0].foil_quantity_change == -1

    async def test_set_collection_quantity(self, db_with_collection: UserDatabase) -> None:
        """Set quantity of a collection card."""
        await db_with_collection.set_collection_quantity(
            "Lightning Bolt", quantity=10, foil_quantity=5
        )

        card = await db_with_collection.get_collection_card("Lightning Bolt")
        assert card is not None
        assert card.quantity == 10
        assert card.foil_quantity == 5

    async def test_set_collection_quantity_zero_removes(
        self, db_with_collection: UserDatabase
    ) -> None:
        """Setting quantity to 0 should remove card."""
        await db_with_collection.set_collection_quantity(
            "Lightning Bolt", quantity=0, foil_quantity=0
        )

        card = await db_with_collection.get_collection_card("Lightning Bolt")
        assert card is None

    async def test_set_collection_quantity_logs_history(
        self, db_with_collection: UserDatabase
    ) -> None:
        """Setting quantity should log history."""
        await db_with_collection.set_collection_quantity(
            "Lightning Bolt", quantity=10, foil_quantity=2
        )

        history = await db_with_collection.get_collection_history(limit=10, action="update")
        assert len(history) == 1
        assert history[0].card_name == "Lightning Bolt"
        assert history[0].action == "update"
        assert history[0].quantity_change == 6  # 10 - 4 original
        assert history[0].foil_quantity_change == 1  # 2 - 1 original

    async def test_update_collection_printing(self, db_with_collection: UserDatabase) -> None:
        """Update printing info for collection card."""
        updated = await db_with_collection.update_collection_printing(
            "Lightning Bolt", set_code="M11", collector_number="146"
        )

        assert updated is True

        card = await db_with_collection.get_collection_card("Lightning Bolt")
        assert card is not None
        assert card.set_code == "M11"
        assert card.collector_number == "146"

    async def test_update_collection_printing_not_found(self, db: UserDatabase) -> None:
        """Update printing for nonexistent card should return False."""
        updated = await db.update_collection_printing(
            "Nonexistent", set_code="M11", collector_number="146"
        )
        assert updated is False

    async def test_get_collection_card_not_found(self, db: UserDatabase) -> None:
        """Get nonexistent card should return None."""
        card = await db.get_collection_card("Nonexistent Card")
        assert card is None

    async def test_get_collection_cards_pagination(self, db_with_collection: UserDatabase) -> None:
        """Get collection cards with pagination."""
        # Add more cards
        for i in range(5):
            await db_with_collection.add_to_collection(f"Card {i}", quantity=1)

        # Get first page
        page1 = await db_with_collection.get_collection_cards(limit=3, offset=0)
        assert len(page1) == 3

        # Get second page
        page2 = await db_with_collection.get_collection_cards(limit=3, offset=3)
        assert len(page2) == 3

        # Get third page
        page3 = await db_with_collection.get_collection_cards(limit=3, offset=6)
        assert len(page3) == 2

    async def test_get_collection_count(self, db_with_collection: UserDatabase) -> None:
        """Get total number of unique cards."""
        count = await db_with_collection.get_collection_count()
        assert count == 3

    async def test_get_collection_card_names(self, db_with_collection: UserDatabase) -> None:
        """Get all card names in collection."""
        names = await db_with_collection.get_collection_card_names()
        assert names == {"Lightning Bolt", "Counterspell", "Sol Ring"}

    async def test_get_collection_total_cards(self, db_with_collection: UserDatabase) -> None:
        """Get total number of cards including quantities."""
        # Lightning Bolt: 4 + 1 foil = 5
        # Counterspell: 3
        # Sol Ring: 2 + 2 foil = 4
        # Total: 12
        total = await db_with_collection.get_collection_total_cards()
        assert total == 12

    async def test_get_collection_foil_total(self, db_with_collection: UserDatabase) -> None:
        """Get total number of foil cards."""
        # Lightning Bolt: 1 foil
        # Sol Ring: 2 foil
        # Total: 3
        foil_total = await db_with_collection.get_collection_foil_total()
        assert foil_total == 3


class TestCollectionDeckUsage:
    """Tests for collection and deck usage queries."""

    async def test_get_card_deck_usage_single_deck(self, db: UserDatabase) -> None:
        """Get deck usage for a card in one deck."""
        deck_id = await db.create_deck(name="Test Deck")
        await db.add_card(deck_id, "Lightning Bolt", quantity=4)

        usage = await db.get_card_deck_usage("Lightning Bolt")
        assert usage == [("Test Deck", 4)]

    async def test_get_card_deck_usage_multiple_decks(self, db: UserDatabase) -> None:
        """Get deck usage across multiple decks."""
        deck1_id = await db.create_deck(name="Deck 1")
        deck2_id = await db.create_deck(name="Deck 2")

        await db.add_card(deck1_id, "Lightning Bolt", quantity=4)
        await db.add_card(deck2_id, "Lightning Bolt", quantity=2)

        usage = await db.get_card_deck_usage("Lightning Bolt")
        assert len(usage) == 2
        assert ("Deck 1", 4) in usage
        assert ("Deck 2", 2) in usage

    async def test_get_card_deck_usage_mainboard_and_sideboard(self, db: UserDatabase) -> None:
        """Get deck usage should sum mainboard and sideboard."""
        deck_id = await db.create_deck(name="Test Deck")
        await db.add_card(deck_id, "Lightning Bolt", quantity=4, sideboard=False)
        await db.add_card(deck_id, "Lightning Bolt", quantity=2, sideboard=True)

        usage = await db.get_card_deck_usage("Lightning Bolt")
        assert usage == [("Test Deck", 6)]

    async def test_get_card_deck_usage_not_found(self, db: UserDatabase) -> None:
        """Get deck usage for card not in any deck."""
        usage = await db.get_card_deck_usage("Nonexistent Card")
        assert usage == []

    async def test_get_card_total_deck_usage(self, db: UserDatabase) -> None:
        """Get total copies across all decks."""
        deck1_id = await db.create_deck(name="Deck 1")
        deck2_id = await db.create_deck(name="Deck 2")

        await db.add_card(deck1_id, "Lightning Bolt", quantity=4)
        await db.add_card(deck2_id, "Lightning Bolt", quantity=2)

        total = await db.get_card_total_deck_usage("Lightning Bolt")
        assert total == 6

    async def test_get_card_total_deck_usage_not_found(self, db: UserDatabase) -> None:
        """Get total usage for card not in any deck."""
        total = await db.get_card_total_deck_usage("Nonexistent Card")
        assert total == 0

    async def test_get_cards_deck_usage_batch(self, db: UserDatabase) -> None:
        """Get deck usage for multiple cards in one query."""
        deck_id = await db.create_deck(name="Test Deck")
        await db.add_card(deck_id, "Lightning Bolt", quantity=4)
        await db.add_card(deck_id, "Counterspell", quantity=3)
        await db.add_card(deck_id, "Sol Ring", quantity=1)

        usage = await db.get_cards_deck_usage_batch(
            ["Lightning Bolt", "Counterspell", "Force of Will"]
        )

        assert usage["Lightning Bolt"] == [("Test Deck", 4)]
        assert usage["Counterspell"] == [("Test Deck", 3)]
        assert usage["Force of Will"] == []

    async def test_get_cards_deck_usage_batch_empty(self, db: UserDatabase) -> None:
        """Get batch usage with empty list."""
        usage = await db.get_cards_deck_usage_batch([])
        assert usage == {}


class TestCollectionHistory:
    """Tests for collection history."""

    async def test_get_collection_history_all(self, db: UserDatabase) -> None:
        """Get all collection history."""
        await db.add_to_collection("Lightning Bolt", quantity=4)
        await db.add_to_collection("Counterspell", quantity=3)
        await db.remove_from_collection("Lightning Bolt")

        history = await db.get_collection_history(limit=10)
        assert len(history) == 3

    async def test_get_collection_history_pagination(self, db: UserDatabase) -> None:
        """Get collection history with pagination."""
        for i in range(5):
            await db.add_to_collection(f"Card {i}", quantity=1)

        page1 = await db.get_collection_history(limit=2, offset=0)
        assert len(page1) == 2

        page2 = await db.get_collection_history(limit=2, offset=2)
        assert len(page2) == 2

    async def test_get_collection_history_filter_by_action(self, db: UserDatabase) -> None:
        """Get collection history filtered by action."""
        await db.add_to_collection("Lightning Bolt", quantity=4)
        await db.add_to_collection("Counterspell", quantity=3)
        await db.set_collection_quantity("Lightning Bolt", quantity=10)
        await db.remove_from_collection("Counterspell")

        adds = await db.get_collection_history(limit=10, action="add")
        assert len(adds) == 2
        assert all(h.action == "add" for h in adds)

        updates = await db.get_collection_history(limit=10, action="update")
        assert len(updates) == 1
        assert updates[0].action == "update"

        removes = await db.get_collection_history(limit=10, action="remove")
        assert len(removes) == 1
        assert removes[0].action == "remove"

    async def test_get_collection_history_ordered_by_date(self, db: UserDatabase) -> None:
        """History should be ordered by created_at DESC."""
        await db.add_to_collection("Card 1", quantity=1)
        await asyncio.sleep(1.1)  # SQLite CURRENT_TIMESTAMP has second precision
        await db.add_to_collection("Card 2", quantity=1)
        await asyncio.sleep(1.1)
        await db.add_to_collection("Card 3", quantity=1)

        history = await db.get_collection_history(limit=10)
        assert len(history) == 3
        assert history[0].card_name == "Card 3"
        assert history[1].card_name == "Card 2"
        assert history[2].card_name == "Card 1"

    async def test_get_recent_removals(self, db: UserDatabase) -> None:
        """Get recently removed cards."""
        await db.add_to_collection("Lightning Bolt", quantity=4)
        await db.add_to_collection("Counterspell", quantity=3)
        await db.remove_from_collection("Lightning Bolt")
        await db.remove_from_collection("Counterspell")

        removals = await db.get_recent_removals(limit=10)
        assert len(removals) == 2
        assert all(r.action == "remove" for r in removals)


class TestMigrations:
    """Tests for database migrations."""

    async def test_migration_from_version_0(self) -> None:
        """Test migration from version 0 (no schema)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create database without schema
            db = UserDatabase(db_path)
            await db.connect()

            # Verify schema version is current
            async with db.conn.execute("SELECT version FROM schema_version") as cursor:
                row = await cursor.fetchone()
                assert row["version"] == 6

            await db.close()

    async def test_column_exists_check(self, db: UserDatabase) -> None:
        """Test column existence check."""
        exists = await db._column_exists("decks", "name")
        assert exists is True

        exists = await db._column_exists("decks", "nonexistent_column")
        assert exists is False

    async def test_add_column_if_missing_new_column(self) -> None:
        """Test adding a new column."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = UserDatabase(db_path)
            await db.connect()

            # Add a test column
            await db._add_column_if_missing("decks", "test_column", "TEXT")

            # Verify column exists
            exists = await db._column_exists("decks", "test_column")
            assert exists is True

            await db.close()

    async def test_add_column_if_missing_existing_column(self, db: UserDatabase) -> None:
        """Test adding an existing column (should be idempotent)."""
        # Should not raise
        await db._add_column_if_missing("decks", "name", "TEXT")

        # Column should still exist
        exists = await db._column_exists("decks", "name")
        assert exists is True

    async def test_migration_from_older_version(self) -> None:
        """Test migration from an older schema version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = UserDatabase(db_path)
            await db.connect()

            # Manually set schema version to 1
            await db.conn.execute("UPDATE schema_version SET version = 1")
            await db.conn.commit()
            await db.close()

            # Reconnect - should trigger migration
            db = UserDatabase(db_path)
            await db.connect()

            # Verify schema version is current
            async with db.conn.execute("SELECT version FROM schema_version") as cursor:
                row = await cursor.fetchone()
                assert row["version"] == 6

            # Verify migration added columns
            exists = await db._column_exists("deck_cards", "set_code")
            assert exists is True

            await db.close()


class TestConcurrency:
    """Tests for concurrency and connection pooling."""

    async def test_concurrent_queries(self, db: UserDatabase) -> None:
        """Multiple concurrent queries should work."""
        # Create test data
        deck_id = await db.create_deck(name="Test Deck")
        await db.add_card(deck_id, "Lightning Bolt", quantity=4)

        # Run multiple queries concurrently
        tasks = [
            db.get_deck(deck_id),
            db.list_decks(),
            db.get_deck_cards(deck_id),
            db.get_collection_count(),
        ]

        results = await asyncio.gather(*tasks)
        assert results[0] is not None
        assert len(results[1]) == 1
        assert len(results[2]) == 1
        assert results[3] == 0

    async def test_semaphore_limits_connections(self, db: UserDatabase) -> None:
        """Semaphore should limit concurrent database connections."""

        # Create a slow query
        async def slow_query() -> None:
            async with db._execute("SELECT 1"):
                await asyncio.sleep(0.1)

        # Try to run more queries than max_connections
        start_time = asyncio.get_event_loop().time()
        await asyncio.gather(*[slow_query() for _ in range(10)])
        elapsed = asyncio.get_event_loop().time() - start_time

        # With max_connections=5, 10 queries should take at least 0.2 seconds
        # (2 batches of 5 concurrent queries, each taking 0.1 seconds)
        assert elapsed >= 0.15


class TestTriggers:
    """Tests for database triggers."""

    async def test_deck_updated_at_trigger_on_update(
        self, db_with_deck: tuple[UserDatabase, int]
    ) -> None:
        """Updating deck should update updated_at timestamp."""
        db, deck_id = db_with_deck

        original = await db.get_deck(deck_id)
        await asyncio.sleep(1.1)  # SQLite CURRENT_TIMESTAMP has second precision
        await db.update_deck(deck_id, description="Updated")
        updated = await db.get_deck(deck_id)

        assert original is not None
        assert updated is not None
        assert updated.updated_at > original.updated_at

    async def test_deck_updated_at_trigger_on_card_insert(
        self, db_with_deck: tuple[UserDatabase, int]
    ) -> None:
        """Adding card should update deck's updated_at."""
        db, deck_id = db_with_deck

        original = await db.get_deck(deck_id)
        await asyncio.sleep(1.1)  # SQLite CURRENT_TIMESTAMP has second precision
        await db.add_card(deck_id, "Lightning Bolt", quantity=4)
        updated = await db.get_deck(deck_id)

        assert original is not None
        assert updated is not None
        assert updated.updated_at > original.updated_at

    async def test_deck_updated_at_trigger_on_card_update(
        self, db_with_deck: tuple[UserDatabase, int]
    ) -> None:
        """Updating card quantity should update deck's updated_at."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4)
        original = await db.get_deck(deck_id)
        await asyncio.sleep(1.1)  # SQLite CURRENT_TIMESTAMP has second precision
        await db.set_quantity(deck_id, "Lightning Bolt", quantity=2)
        updated = await db.get_deck(deck_id)

        assert original is not None
        assert updated is not None
        assert updated.updated_at > original.updated_at

    async def test_deck_updated_at_trigger_on_card_delete(
        self, db_with_deck: tuple[UserDatabase, int]
    ) -> None:
        """Removing card should update deck's updated_at."""
        db, deck_id = db_with_deck

        await db.add_card(deck_id, "Lightning Bolt", quantity=4)
        original = await db.get_deck(deck_id)
        await asyncio.sleep(1.1)  # SQLite CURRENT_TIMESTAMP has second precision
        await db.remove_card(deck_id, "Lightning Bolt")
        updated = await db.get_deck(deck_id)

        assert original is not None
        assert updated is not None
        assert updated.updated_at > original.updated_at

    async def test_collection_updated_at_trigger(self, db: UserDatabase) -> None:
        """Updating collection card should update updated_at."""
        await db.add_to_collection("Lightning Bolt", quantity=4)
        original = await db.get_collection_card("Lightning Bolt")

        await asyncio.sleep(1.1)  # SQLite CURRENT_TIMESTAMP has second precision
        await db.set_collection_quantity("Lightning Bolt", quantity=10)
        updated = await db.get_collection_card("Lightning Bolt")

        assert original is not None
        assert updated is not None
        assert updated.updated_at > original.updated_at
