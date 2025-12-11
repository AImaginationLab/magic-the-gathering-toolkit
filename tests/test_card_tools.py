"""Tests for card tools."""

from __future__ import annotations

import pytest

from mtg_mcp.data.database import MTGDatabase, ScryfallDatabase
from mtg_mcp.data.models.inputs import SearchCardsInput
from mtg_mcp.tools import cards


class TestSearchCards:
    """Tests for search_cards tool."""

    async def test_search_by_name(self, db: MTGDatabase, scryfall: ScryfallDatabase | None) -> None:
        """Test searching for cards by name."""
        filters = SearchCardsInput(name="Lightning Bolt")
        result = await cards.search_cards(db, scryfall, filters)

        assert result.count >= 1
        assert any("Lightning Bolt" in c.name for c in result.cards)

    async def test_search_by_colors(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test searching for cards by colors."""
        filters = SearchCardsInput(colors=["R"], type="Instant", page_size=10)
        result = await cards.search_cards(db, scryfall, filters)

        assert result.count > 0
        # All results should be red
        for card in result.cards:
            assert "R" in card.colors

    async def test_search_by_type(self, db: MTGDatabase, scryfall: ScryfallDatabase | None) -> None:
        """Test searching for cards by type."""
        filters = SearchCardsInput(type="Creature", subtype="Goblin", page_size=10)
        result = await cards.search_cards(db, scryfall, filters)

        assert result.count > 0
        for card in result.cards:
            assert "Creature" in (card.type or "")

    async def test_search_by_cmc(self, db: MTGDatabase, scryfall: ScryfallDatabase | None) -> None:
        """Test searching for cards by mana value."""
        filters = SearchCardsInput(cmc=1, type="Instant", colors=["R"], page_size=10)
        result = await cards.search_cards(db, scryfall, filters)

        assert result.count > 0
        for card in result.cards:
            assert card.cmc == 1

    async def test_search_by_format_legality(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test searching for cards legal in a format."""
        filters = SearchCardsInput(name="Lightning Bolt", format_legal="modern", page_size=5)
        result = await cards.search_cards(db, scryfall, filters)

        assert result.count >= 1

    async def test_search_pagination(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test search pagination."""
        filters1 = SearchCardsInput(type="Creature", page=1, page_size=5)
        filters2 = SearchCardsInput(type="Creature", page=2, page_size=5)

        result1 = await cards.search_cards(db, scryfall, filters1)
        result2 = await cards.search_cards(db, scryfall, filters2)

        assert result1.page == 1
        assert result2.page == 2
        assert len(result1.cards) == 5
        # Results should be different
        names1 = {c.name for c in result1.cards}
        names2 = {c.name for c in result2.cards}
        assert names1 != names2

    async def test_search_empty_results(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test search with no results."""
        filters = SearchCardsInput(name="xyznonexistentcardxyz")
        result = await cards.search_cards(db, scryfall, filters)

        assert result.count == 0
        assert len(result.cards) == 0


class TestGetCard:
    """Tests for get_card tool."""

    async def test_get_card_by_name(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test getting a card by name."""
        result = await cards.get_card(db, scryfall, name="Lightning Bolt")

        assert result.name == "Lightning Bolt"
        assert result.cmc == 1.0
        assert result.type is not None
        assert "Instant" in result.type

    async def test_get_card_with_legalities(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test that card details include legalities."""
        result = await cards.get_card(db, scryfall, name="Lightning Bolt")

        assert result.legalities is not None
        assert "modern" in result.legalities
        assert result.legalities["modern"] in ("Legal", "Banned", "Restricted")

    async def test_get_card_not_found(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test getting a nonexistent card raises error."""
        from mtg_mcp.exceptions import CardNotFoundError

        with pytest.raises(CardNotFoundError):
            await cards.get_card(db, scryfall, name="xyznonexistentcardxyz")

    async def test_get_card_no_params(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test that missing params raises validation error."""
        from mtg_mcp.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await cards.get_card(db, scryfall)


class TestGetCardRulings:
    """Tests for get_card_rulings tool."""

    async def test_get_rulings(self, db: MTGDatabase) -> None:
        """Test getting rulings for a card with rulings."""
        # Tarmogoyf has rulings
        result = await cards.get_card_rulings(db, "Tarmogoyf")

        assert result.card_name == "Tarmogoyf"
        assert result.count > 0
        assert len(result.rulings) > 0
        # Each ruling should have date and text
        for ruling in result.rulings:
            assert ruling.date
            assert ruling.text

    async def test_get_rulings_card_not_found(self, db: MTGDatabase) -> None:
        """Test getting rulings for nonexistent card."""
        from mtg_mcp.exceptions import CardNotFoundError

        with pytest.raises(CardNotFoundError):
            await cards.get_card_rulings(db, "xyznonexistentcardxyz")


class TestGetCardLegalities:
    """Tests for get_card_legalities tool."""

    async def test_get_legalities(self, db: MTGDatabase) -> None:
        """Test getting legalities for a card."""
        result = await cards.get_card_legalities(db, "Lightning Bolt")

        assert result.card_name == "Lightning Bolt"
        assert len(result.legalities) > 0
        # Should have common formats
        assert "modern" in result.legalities
        assert "legacy" in result.legalities
        assert "vintage" in result.legalities

    async def test_get_legalities_banned_card(self, db: MTGDatabase) -> None:
        """Test legalities for a banned card."""
        # Channel is banned in many formats
        result = await cards.get_card_legalities(db, "Channel")

        assert result.card_name == "Channel"
        # Should be banned/restricted in some formats
        legality_values = list(result.legalities.values())
        assert "Banned" in legality_values or "Restricted" in legality_values


class TestGetRandomCard:
    """Tests for get_random_card tool."""

    async def test_get_random_card(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test getting a random card."""
        result = await cards.get_random_card(db, scryfall)

        assert result.name
        assert result.type

    async def test_random_cards_are_different(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test that multiple random cards are likely different."""
        results = [await cards.get_random_card(db, scryfall) for _ in range(5)]
        names = [r.name for r in results]

        # With 30k+ cards, 5 random picks should have at least 2 different cards
        assert len(set(names)) >= 2
