"""Tests for image and price tools."""

from __future__ import annotations

import pytest

from mtg_mcp.data.database import ScryfallDatabase
from mtg_mcp.tools import images


class TestGetCardImage:
    """Tests for get_card_image tool."""

    async def test_get_card_image(self, scryfall: ScryfallDatabase | None) -> None:
        """Test getting card image URLs."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.get_card_image(scryfall, "Lightning Bolt")

        assert result.card_name == "Lightning Bolt"
        assert result.images is not None
        # Should have at least one image URL
        assert any([
            result.images.small,
            result.images.normal,
            result.images.large,
        ])

    async def test_get_card_image_with_set(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test getting card image from a specific set."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.get_card_image(scryfall, "Lightning Bolt", set_code="A25")

        assert result.card_name == "Lightning Bolt"
        assert result.set_code is not None

    async def test_get_card_image_not_found(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test getting image for nonexistent card."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        from mtg_mcp.exceptions import CardNotFoundError

        with pytest.raises(CardNotFoundError):
            await images.get_card_image(scryfall, "xyznonexistentcardxyz")


class TestGetCardPrintings:
    """Tests for get_card_printings tool."""

    async def test_get_printings(self, scryfall: ScryfallDatabase | None) -> None:
        """Test getting all printings of a card."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.get_card_printings(scryfall, "Lightning Bolt")

        assert result.card_name == "Lightning Bolt"
        assert result.count > 1  # Lightning Bolt has many printings
        assert len(result.printings) > 1

    async def test_printings_have_set_codes(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test that printings include set codes."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.get_card_printings(scryfall, "Lightning Bolt")

        for printing in result.printings:
            assert printing.set_code is not None


class TestGetCardPrice:
    """Tests for get_card_price tool."""

    async def test_get_card_price(self, scryfall: ScryfallDatabase | None) -> None:
        """Test getting card price."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.get_card_price(scryfall, "Lightning Bolt")

        assert result.card_name == "Lightning Bolt"
        assert result.prices is not None
        # Should have at least USD price
        # (price might be None if no market data, but prices object should exist)

    async def test_get_price_with_set(self, scryfall: ScryfallDatabase | None) -> None:
        """Test getting price for specific printing."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.get_card_price(scryfall, "Lightning Bolt", set_code="A25")

        assert result.card_name == "Lightning Bolt"
        assert result.set_code is not None


class TestSearchByPrice:
    """Tests for search_by_price tool."""

    async def test_search_by_min_price(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test searching for cards above a minimum price."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.search_by_price(scryfall, min_price=50.0, page_size=10)

        assert result.count > 0
        for card in result.cards:
            if card.price_usd is not None:
                assert card.price_usd >= 50.0

    async def test_search_by_max_price(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test searching for cards below a maximum price."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.search_by_price(scryfall, max_price=1.0, page_size=10)

        assert result.count > 0
        for card in result.cards:
            if card.price_usd is not None:
                assert card.price_usd <= 1.0

    async def test_search_by_price_range(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test searching for cards in a price range."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.search_by_price(
            scryfall, min_price=5.0, max_price=10.0, page_size=10
        )

        assert result.count > 0
        for card in result.cards:
            if card.price_usd is not None:
                assert 5.0 <= card.price_usd <= 10.0

    async def test_search_by_price_pagination(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test price search pagination."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result1 = await images.search_by_price(scryfall, max_price=5.0, page=1, page_size=5)
        result2 = await images.search_by_price(scryfall, max_price=5.0, page=2, page_size=5)

        assert result1.page == 1
        assert result2.page == 2
        # Results should be different
        names1 = {c.name for c in result1.cards}
        names2 = {c.name for c in result2.cards}
        assert names1 != names2
