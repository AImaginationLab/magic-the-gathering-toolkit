"""Tests for UserDatabase (deck management)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mtg_core.data.database import UserDatabase


@pytest.fixture
async def user_db():
    """Create a temporary user database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_user.sqlite"
        db = UserDatabase(db_path)
        await db.connect()
        yield db
        await db.close()


class TestDeckCRUD:
    """Test deck create, read, update, delete operations."""

    async def test_create_deck(self, user_db: UserDatabase):
        """Test creating a new deck."""
        deck_id = await user_db.create_deck("Test Deck", "standard", None, "A test deck")
        assert deck_id == 1

        deck = await user_db.get_deck(deck_id)
        assert deck is not None
        assert deck.name == "Test Deck"
        assert deck.format == "standard"
        assert deck.description == "A test deck"

    async def test_list_decks_empty(self, user_db: UserDatabase):
        """Test listing decks when none exist."""
        decks = await user_db.list_decks()
        assert decks == []

    async def test_list_decks(self, user_db: UserDatabase):
        """Test listing multiple decks."""
        await user_db.create_deck("Deck 1", "standard")
        await user_db.create_deck("Deck 2", "modern")
        await user_db.create_deck("Deck 3", "commander", commander="Atraxa, Praetors' Voice")

        decks = await user_db.list_decks()
        assert len(decks) == 3

        # Find the commander deck by name
        deck_names = {d.name: d for d in decks}
        assert "Deck 1" in deck_names
        assert "Deck 2" in deck_names
        assert "Deck 3" in deck_names
        assert deck_names["Deck 3"].commander == "Atraxa, Praetors' Voice"
        assert deck_names["Deck 1"].format == "standard"
        assert deck_names["Deck 2"].format == "modern"

    async def test_update_deck(self, user_db: UserDatabase):
        """Test updating deck metadata."""
        deck_id = await user_db.create_deck("Old Name", "standard")

        await user_db.update_deck(deck_id, name="New Name", format="modern")

        deck = await user_db.get_deck(deck_id)
        assert deck is not None
        assert deck.name == "New Name"
        assert deck.format == "modern"

    async def test_delete_deck(self, user_db: UserDatabase):
        """Test deleting a deck."""
        deck_id = await user_db.create_deck("To Delete")

        deleted = await user_db.delete_deck(deck_id)
        assert deleted is True

        deck = await user_db.get_deck(deck_id)
        assert deck is None

    async def test_delete_nonexistent_deck(self, user_db: UserDatabase):
        """Test deleting a deck that doesn't exist."""
        deleted = await user_db.delete_deck(999)
        assert deleted is False

    async def test_get_nonexistent_deck(self, user_db: UserDatabase):
        """Test getting a deck that doesn't exist."""
        deck = await user_db.get_deck(999)
        assert deck is None


class TestCardOperations:
    """Test card add, remove, quantity operations."""

    async def test_add_card(self, user_db: UserDatabase):
        """Test adding a card to a deck."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 4)

        cards = await user_db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].card_name == "Lightning Bolt"
        assert cards[0].quantity == 4
        assert cards[0].is_sideboard is False

    async def test_add_card_to_sideboard(self, user_db: UserDatabase):
        """Test adding a card to sideboard."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 4)
        await user_db.add_card(deck_id, "Pyroblast", 2, sideboard=True)

        cards = await user_db.get_deck_cards(deck_id)
        assert len(cards) == 2

        mainboard = [c for c in cards if not c.is_sideboard]
        sideboard = [c for c in cards if c.is_sideboard]

        assert len(mainboard) == 1
        assert len(sideboard) == 1
        assert sideboard[0].card_name == "Pyroblast"

    async def test_add_card_increments_quantity(self, user_db: UserDatabase):
        """Test that adding the same card increases quantity."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 2)
        await user_db.add_card(deck_id, "Lightning Bolt", 2)

        cards = await user_db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].quantity == 4

    async def test_remove_card(self, user_db: UserDatabase):
        """Test removing a card from a deck."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 4)

        removed = await user_db.remove_card(deck_id, "Lightning Bolt")
        assert removed is True

        cards = await user_db.get_deck_cards(deck_id)
        assert len(cards) == 0

    async def test_remove_nonexistent_card(self, user_db: UserDatabase):
        """Test removing a card that doesn't exist."""
        deck_id = await user_db.create_deck("Test Deck")

        removed = await user_db.remove_card(deck_id, "Lightning Bolt")
        assert removed is False

    async def test_set_quantity(self, user_db: UserDatabase):
        """Test setting card quantity."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 4)

        await user_db.set_quantity(deck_id, "Lightning Bolt", 2)

        cards = await user_db.get_deck_cards(deck_id)
        assert cards[0].quantity == 2

    async def test_set_quantity_zero_removes(self, user_db: UserDatabase):
        """Test that setting quantity to 0 removes the card."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 4)

        await user_db.set_quantity(deck_id, "Lightning Bolt", 0)

        cards = await user_db.get_deck_cards(deck_id)
        assert len(cards) == 0

    async def test_move_to_sideboard(self, user_db: UserDatabase):
        """Test moving a card to sideboard."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 4)

        await user_db.move_to_sideboard(deck_id, "Lightning Bolt")

        cards = await user_db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].is_sideboard is True

    async def test_move_to_mainboard(self, user_db: UserDatabase):
        """Test moving a card to mainboard."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 4, sideboard=True)

        await user_db.move_to_mainboard(deck_id, "Lightning Bolt")

        cards = await user_db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].is_sideboard is False

    async def test_move_to_sideboard_merges(self, user_db: UserDatabase):
        """Test that moving to sideboard merges with existing sideboard cards."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 2)
        await user_db.add_card(deck_id, "Lightning Bolt", 2, sideboard=True)

        await user_db.move_to_sideboard(deck_id, "Lightning Bolt")

        cards = await user_db.get_deck_cards(deck_id)
        assert len(cards) == 1
        assert cards[0].is_sideboard is True
        assert cards[0].quantity == 4


class TestQueries:
    """Test query operations."""

    async def test_get_deck_cards(self, user_db: UserDatabase):
        """Test getting all cards in a deck."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 4)
        await user_db.add_card(deck_id, "Mountain", 20)
        await user_db.add_card(deck_id, "Pyroblast", 2, sideboard=True)

        cards = await user_db.get_deck_cards(deck_id)
        assert len(cards) == 3

    async def test_find_decks_with_card(self, user_db: UserDatabase):
        """Test finding decks containing a specific card."""
        deck1_id = await user_db.create_deck("Deck 1")
        deck2_id = await user_db.create_deck("Deck 2")
        await user_db.create_deck("Deck 3")  # No Lightning Bolt

        await user_db.add_card(deck1_id, "Lightning Bolt", 4)
        await user_db.add_card(deck2_id, "Lightning Bolt", 4)

        decks = await user_db.find_decks_with_card("Lightning Bolt")
        assert len(decks) == 2
        deck_names = {d.name for d in decks}
        assert "Deck 1" in deck_names
        assert "Deck 2" in deck_names

    async def test_get_deck_card_count(self, user_db: UserDatabase):
        """Test getting total quantity of a card across mainboard and sideboard."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 4)
        await user_db.add_card(deck_id, "Lightning Bolt", 2, sideboard=True)

        count = await user_db.get_deck_card_count(deck_id, "Lightning Bolt")
        assert count == 6

    async def test_deck_list_includes_card_counts(self, user_db: UserDatabase):
        """Test that deck list includes accurate card counts."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 4)
        await user_db.add_card(deck_id, "Mountain", 20)
        await user_db.add_card(deck_id, "Pyroblast", 2, sideboard=True)

        decks = await user_db.list_decks()
        assert len(decks) == 1
        assert decks[0].card_count == 24  # Mainboard
        assert decks[0].sideboard_count == 2


class TestTags:
    """Test tag operations."""

    async def test_add_tag(self, user_db: UserDatabase):
        """Test adding a tag to a deck."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_tag(deck_id, "aggro")

        tags = await user_db.get_deck_tags(deck_id)
        assert tags == ["aggro"]

    async def test_add_multiple_tags(self, user_db: UserDatabase):
        """Test adding multiple tags to a deck."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_tag(deck_id, "aggro")
        await user_db.add_tag(deck_id, "budget")
        await user_db.add_tag(deck_id, "competitive")

        tags = await user_db.get_deck_tags(deck_id)
        assert sorted(tags) == ["aggro", "budget", "competitive"]

    async def test_add_duplicate_tag(self, user_db: UserDatabase):
        """Test that adding duplicate tag is idempotent."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_tag(deck_id, "aggro")
        await user_db.add_tag(deck_id, "aggro")

        tags = await user_db.get_deck_tags(deck_id)
        assert tags == ["aggro"]

    async def test_remove_tag(self, user_db: UserDatabase):
        """Test removing a tag from a deck."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_tag(deck_id, "aggro")
        await user_db.add_tag(deck_id, "budget")

        await user_db.remove_tag(deck_id, "aggro")

        tags = await user_db.get_deck_tags(deck_id)
        assert tags == ["budget"]

    async def test_find_decks_by_tag(self, user_db: UserDatabase):
        """Test finding decks by tag."""
        deck1_id = await user_db.create_deck("Aggro Deck 1")
        deck2_id = await user_db.create_deck("Aggro Deck 2")
        deck3_id = await user_db.create_deck("Control Deck")

        await user_db.add_tag(deck1_id, "aggro")
        await user_db.add_tag(deck2_id, "aggro")
        await user_db.add_tag(deck3_id, "control")

        aggro_decks = await user_db.find_decks_by_tag("aggro")
        assert len(aggro_decks) == 2

        deck_names = {d.name for d in aggro_decks}
        assert "Aggro Deck 1" in deck_names
        assert "Aggro Deck 2" in deck_names


class TestCascadeDelete:
    """Test that deleting a deck cleans up related data."""

    async def test_delete_deck_removes_cards(self, user_db: UserDatabase):
        """Test that deleting a deck removes its cards."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_card(deck_id, "Lightning Bolt", 4)
        await user_db.add_card(deck_id, "Mountain", 20)

        await user_db.delete_deck(deck_id)

        # Cards should be gone (cascade delete)
        cards = await user_db.get_deck_cards(deck_id)
        assert len(cards) == 0

    async def test_delete_deck_removes_tags(self, user_db: UserDatabase):
        """Test that deleting a deck removes its tags."""
        deck_id = await user_db.create_deck("Test Deck")
        await user_db.add_tag(deck_id, "aggro")
        await user_db.add_tag(deck_id, "budget")

        await user_db.delete_deck(deck_id)

        # Tags should be gone (cascade delete)
        tags = await user_db.get_deck_tags(deck_id)
        assert len(tags) == 0
