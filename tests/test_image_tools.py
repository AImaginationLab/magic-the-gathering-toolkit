"""Tests for image and price tools."""

from __future__ import annotations

import pytest

from mtg_core.data.database import ScryfallDatabase
from mtg_core.tools import images


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
        assert any(
            [
                result.images.small,
                result.images.normal,
                result.images.large,
            ]
        )

    async def test_get_card_image_with_set(self, scryfall: ScryfallDatabase | None) -> None:
        """Test getting card image from a specific set."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.get_card_image(scryfall, "Lightning Bolt", set_code="A25")

        assert result.card_name == "Lightning Bolt"
        assert result.set_code is not None

    async def test_get_card_image_not_found(self, scryfall: ScryfallDatabase | None) -> None:
        """Test getting image for nonexistent card."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        from mtg_core.exceptions import CardNotFoundError

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

    async def test_printings_have_set_codes(self, scryfall: ScryfallDatabase | None) -> None:
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

    async def test_search_by_min_price(self, scryfall: ScryfallDatabase | None) -> None:
        """Test searching for cards above a minimum price."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.search_by_price(scryfall, min_price=50.0, page_size=10)

        assert result.count > 0
        for card in result.cards:
            if card.price_usd is not None:
                assert card.price_usd >= 50.0

    async def test_search_by_max_price(self, scryfall: ScryfallDatabase | None) -> None:
        """Test searching for cards below a maximum price."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.search_by_price(scryfall, max_price=1.0, page_size=10)

        assert result.count > 0
        for card in result.cards:
            if card.price_usd is not None:
                assert card.price_usd <= 1.0

    async def test_search_by_price_range(self, scryfall: ScryfallDatabase | None) -> None:
        """Test searching for cards in a price range."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        result = await images.search_by_price(scryfall, min_price=5.0, max_price=10.0, page_size=10)

        assert result.count > 0
        for card in result.cards:
            if card.price_usd is not None:
                assert 5.0 <= card.price_usd <= 10.0

    async def test_search_by_price_pagination(self, scryfall: ScryfallDatabase | None) -> None:
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


class TestScryfallDatabaseIntegrity:
    """Tests to ensure Scryfall database has all printings (not just unique_artwork)."""

    async def test_database_has_all_printings(self, scryfall: ScryfallDatabase | None) -> None:
        """Ensure database uses default_cards (~110k) not unique_artwork (~50k).

        This is critical for accurate price lookups. The unique_artwork bulk type
        only has one printing per unique art, missing many printings users may own.
        """
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        stats = await scryfall.get_database_stats()
        # default_cards has ~110k+ cards, unique_artwork has ~50k
        assert stats["total_cards"] > 100000, (
            f"Scryfall database only has {stats['total_cards']} cards. "
            "Expected 100k+ (default_cards). Got unique_artwork (~50k) instead? "
            "Run: uv run create-datasources --skip-mtgjson --skip-combos"
        )

    async def test_multiple_printings_exist_for_reprinted_card(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Ensure cards with multiple printings have all of them available.

        Thoughtseize in 2XM has both regular (#109) and borderless (#344) printings.
        If only one exists, the database is using unique_artwork bulk type.
        """
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        printings = await scryfall.get_all_printings("Thoughtseize")
        set_2xm_printings = [p for p in printings if p.set_code and p.set_code.lower() == "2xm"]

        assert len(set_2xm_printings) >= 2, (
            f"Expected 2+ Thoughtseize printings in 2XM, got {len(set_2xm_printings)}. "
            "Database may be using unique_artwork instead of default_cards."
        )


class TestSpecificPrintingPriceLookup:
    """Tests for looking up prices by specific printing (set_code + collector_number)."""

    async def test_lookup_specific_printing_by_collector_number(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test that we can look up a specific printing by collector number."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        # Look up regular Thoughtseize (cheaper)
        regular = await scryfall.get_card_image("Thoughtseize", set_code="2xm", collector_number="109")
        assert regular is not None, "Failed to find Thoughtseize 2xm #109"
        assert regular.collector_number == "109"

        # Look up borderless Thoughtseize (more expensive)
        borderless = await scryfall.get_card_image("Thoughtseize", set_code="2xm", collector_number="344")
        assert borderless is not None, "Failed to find Thoughtseize 2xm #344"
        assert borderless.collector_number == "344"

        # Prices should be different
        regular_price = regular.get_price_usd()
        borderless_price = borderless.get_price_usd()

        if regular_price and borderless_price:
            assert regular_price != borderless_price, (
                "Regular and borderless printings should have different prices"
            )

    async def test_fallback_prefers_cheapest_regular_printing(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """When no specific printing is requested, prefer cheapest regular printing.

        This prevents expensive special printings (borderless, full-art) from being
        returned when looking up common cards like basic lands.
        """
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        # Basic lands have HUGE price variation ($0.05 to $500+)
        # The fallback should return a cheap regular printing, not an expensive one
        swamp = await scryfall.get_card_image("Swamp")
        assert swamp is not None

        price = swamp.get_price_usd()
        if price is not None:
            # A regular Swamp should cost under $1, not $19+ for full-art or $500+ for promo
            assert price < 1.0, (
                f"Swamp fallback returned ${price:.2f}, expected under $1. "
                "Fallback should prefer cheapest regular printing."
            )
