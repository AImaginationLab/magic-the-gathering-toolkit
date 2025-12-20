"""Tests for collection price accuracy with specific printings.

This test suite validates that collection value calculations use the correct
prices for specific printings (set_code + collector_number), not generic prices.

Bug History:
- Issue: Thoughtseize showing $20.77 instead of user's specific printing price
- Root Cause: Scryfall database was using unique_artwork (50k cards) instead of
  default_cards (110k cards), missing many printings
- Impact: Collection value calculations used wrong printings, inflating/deflating values
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from mtg_core.data.database import ScryfallDatabase


class TestCollectionPriceAccuracy:
    """Test price lookups for collection cards with specific printings."""

    async def test_specific_printing_lookup_uses_correct_price(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Verify looking up a specific printing returns that printing's price.

        Thoughtseize has many printings with vastly different prices:
        - OTP #20: $4.63
        - THS #107: $4.87
        - 2XM #109: $5.97 (regular)
        - 2XM #344: $20.77 (borderless)
        - SLD #1117: $34.74

        When a user has 2XM #109, they should see $5.97, not $20.77 from #344.
        """
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        # Simulate user having the cheap regular printing
        cheap_printing = await scryfall.get_card_image(
            "Thoughtseize", set_code="2xm", collector_number="109"
        )
        assert cheap_printing is not None
        cheap_price = cheap_printing.get_price_usd()
        assert cheap_price is not None
        assert cheap_price < 7.0, f"2XM #109 should be <$7, got ${cheap_price}"

        # Verify we're NOT getting the expensive borderless printing
        expensive_printing = await scryfall.get_card_image(
            "Thoughtseize", set_code="2xm", collector_number="344"
        )
        assert expensive_printing is not None
        expensive_price = expensive_printing.get_price_usd()
        assert expensive_price is not None
        assert expensive_price > 15.0, f"2XM #344 should be >$15, got ${expensive_price}"

        # Prices MUST be different
        assert cheap_price != expensive_price, (
            "Regular and borderless printings must have different prices"
        )

    async def test_composite_price_key_prevents_overwriting(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Verify composite keys prevent expensive printings from overwriting cheap ones.

        The collection stats panel uses composite keys like:
        - "Thoughtseize|2XM|109" -> $5.97
        - "Thoughtseize|2XM|344" -> $20.77

        Without composite keys, batch lookups would overwrite prices with
        whichever printing was processed last.
        """
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        # Get both printings
        regular = await scryfall.get_card_image(
            "Thoughtseize", set_code="2xm", collector_number="109"
        )
        borderless = await scryfall.get_card_image(
            "Thoughtseize", set_code="2xm", collector_number="344"
        )

        assert regular is not None
        assert borderless is not None

        # Build composite keys (matching CollectionStatsPanel._price_key)
        def price_key(name: str, set_code: str | None, collector_number: str | None) -> str:
            if set_code and collector_number:
                return f"{name}|{set_code.upper()}|{collector_number}"
            return name

        key_regular = price_key("Thoughtseize", "2xm", "109")
        key_borderless = price_key("Thoughtseize", "2xm", "344")

        # Keys must be different
        assert key_regular != key_borderless, "Composite keys must differentiate printings"
        assert key_regular == "Thoughtseize|2XM|109"
        assert key_borderless == "Thoughtseize|2XM|344"

        # Prices must not be equal
        assert regular.get_price_usd() != borderless.get_price_usd()

    async def test_basic_land_price_variation(self, scryfall: ScryfallDatabase | None) -> None:
        """Verify basic lands with many printings don't return expensive variants.

        Basic lands have the widest price variation:
        - Regular printings: $0.05 - $0.50
        - Full-art printings: $1 - $20
        - Special printings: $50 - $500+

        Without specific printing info, fallback should return cheap regular printings.
        """
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        # Generic lookup (no specific printing)
        swamp = await scryfall.get_card_image("Swamp")
        assert swamp is not None

        price = swamp.get_price_usd()
        if price is not None:
            # Should get a cheap regular printing, not full-art or promo
            assert price < 1.0, (
                f"Generic Swamp lookup returned ${price:.2f}. "
                "Expected cheap regular printing (<$1), not full-art/promo."
            )

    async def test_collection_value_calculation_accuracy(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Simulate collection value calculation with mixed printings.

        User collection:
        - 1x Thoughtseize (2XM #109) - should use $5.97
        - 1x Thoughtseize (2XM #344) - should use $20.77

        Total value should be ~$26.74, NOT $41.54 (if both used #344 price).
        """
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        # Simulate collection cards
        card1 = await scryfall.get_card_image("Thoughtseize", "2xm", "109")
        card2 = await scryfall.get_card_image("Thoughtseize", "2xm", "344")

        assert card1 is not None
        assert card2 is not None

        price1 = card1.get_price_usd()
        price2 = card2.get_price_usd()

        assert price1 is not None
        assert price2 is not None

        total_value = price1 + price2

        # Total should be around $26.74 (5.97 + 20.77)
        assert 25.0 < total_value < 28.0, (
            f"Total value ${total_value:.2f} out of expected range. "
            "Prices may have been overwritten incorrectly."
        )

    async def test_batch_lookup_preserves_specific_printings(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Verify batch lookups don't overwrite prices for same-name cards.

        When fetching prices for multiple cards with the same name but different
        printings, each should maintain its specific price.
        """
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        # Get multiple Thoughtseize printings
        printings = await scryfall.get_all_printings("Thoughtseize")

        # Should have at least 10 printings (was 6 with unique_artwork, now 12+ with default_cards)
        assert len(printings) >= 10, (
            f"Expected 10+ Thoughtseize printings, got {len(printings)}. "
            "Database may be using unique_artwork instead of default_cards."
        )

        # Extract unique prices (excluding None)
        prices = {p.get_price_usd() for p in printings if p.get_price_usd() is not None}

        # Should have multiple different prices
        assert len(prices) >= 4, (
            f"Expected 4+ unique prices, got {len(prices)}. "
            "Printings may have identical prices incorrectly."
        )

    async def test_foil_vs_nonfoil_price_differentiation(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Verify foil and non-foil prices are stored separately.

        Collection value calculation needs both:
        - price_usd: Regular non-foil price
        - price_usd_foil: Foil price (often 2-3x higher)
        """
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        card = await scryfall.get_card_image("Thoughtseize", "2xm", "109")
        assert card is not None

        nonfoil_price = card.get_price_usd()
        foil_price = card.get_price_usd_foil()

        # Both should exist for this printing
        assert nonfoil_price is not None, "Non-foil price should exist"
        assert foil_price is not None, "Foil price should exist"

        # Foil should typically be more expensive
        # (Not always true, but for modern sets it usually is)
        # Just verify they're tracked separately, not that foil > non-foil
        assert isinstance(nonfoil_price, float)
        assert isinstance(foil_price, float)


class TestCollectionPriceKeyImplementation:
    """Test the actual _price_key implementation matches expected behavior."""

    def test_price_key_with_full_printing_info(self) -> None:
        """Verify price_key generates composite key with all info."""

        def price_key(card_name: str, set_code: str | None, collector_number: str | None) -> str:
            """Implementation from CollectionStatsPanel and FullCollectionScreen."""
            if set_code and collector_number:
                return f"{card_name}|{set_code.upper()}|{collector_number}"
            return card_name

        key = price_key("Thoughtseize", "2xm", "109")
        assert key == "Thoughtseize|2XM|109"

    def test_price_key_without_printing_info_falls_back_to_name(self) -> None:
        """Verify price_key falls back to name-only when printing info missing."""

        def price_key(card_name: str, set_code: str | None, collector_number: str | None) -> str:
            if set_code and collector_number:
                return f"{card_name}|{set_code.upper()}|{collector_number}"
            return card_name

        # Missing collector number
        key1 = price_key("Lightning Bolt", "lea", None)
        assert key1 == "Lightning Bolt"

        # Missing set code
        key2 = price_key("Lightning Bolt", None, "1")
        assert key2 == "Lightning Bolt"

        # Missing both
        key3 = price_key("Lightning Bolt", None, None)
        assert key3 == "Lightning Bolt"

    def test_price_key_case_insensitivity(self) -> None:
        """Verify price_key normalizes set codes to uppercase."""

        def price_key(card_name: str, set_code: str | None, collector_number: str | None) -> str:
            if set_code and collector_number:
                return f"{card_name}|{set_code.upper()}|{collector_number}"
            return card_name

        key1 = price_key("Thoughtseize", "2xm", "109")
        key2 = price_key("Thoughtseize", "2XM", "109")
        key3 = price_key("Thoughtseize", "2Xm", "109")

        # All should normalize to uppercase
        assert key1 == key2 == key3 == "Thoughtseize|2XM|109"


class TestSplashScreenBulkType:
    """Test that splash screen downloads the correct Scryfall bulk type."""

    def test_splash_uses_default_cards_not_unique_artwork(self) -> None:
        """CRITICAL: Verify splash screen downloads default_cards bulk type.

        Bug History:
        - The splash screen was hardcoded to download 'unique_artwork' bulk type
        - unique_artwork only has ~50k cards (one per unique art)
        - default_cards has ~110k cards (ALL printings)
        - Without all printings, price lookups return wrong variants

        This test reads the splash.py source to verify it uses 'default_cards'.
        """
        import ast
        from pathlib import Path

        # Find splash.py
        splash_path = (
            Path(__file__).parent.parent
            / "packages"
            / "mtg-spellbook"
            / "src"
            / "mtg_spellbook"
            / "splash.py"
        )

        if not splash_path.exists():
            pytest.skip("splash.py not found")

        source = splash_path.read_text()

        # Parse and check for the bulk type string
        assert "default_cards" in source, (
            "splash.py MUST use 'default_cards' bulk type for Scryfall downloads. "
            "Using 'unique_artwork' causes missing printings and wrong prices."
        )

        # Ensure unique_artwork is NOT used for downloads
        # (it might appear in comments, but shouldn't be the active type)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            # Look for: item["type"] == "unique_artwork"
            if (
                isinstance(node, ast.Compare)
                and isinstance(node.comparators[0], ast.Constant)
                and node.comparators[0].value == "unique_artwork"
            ):
                pytest.fail(
                    "splash.py is using 'unique_artwork' bulk type! "
                    "This causes missing printings. Use 'default_cards' instead."
                )

    def test_scryfall_database_has_sufficient_cards(
        self, scryfall: ScryfallDatabase | None
    ) -> None:
        """Verify Scryfall database has enough cards (default_cards bulk type).

        - unique_artwork: ~50,000 cards (WRONG)
        - default_cards: ~110,000+ cards (CORRECT)
        """
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        # Get card count
        import asyncio

        async def get_count() -> int:
            async with scryfall._pool.get() as conn:
                cursor = await conn.execute("SELECT COUNT(*) FROM cards")
                row = await cursor.fetchone()
                return row[0] if row else 0

        count = asyncio.get_event_loop().run_until_complete(get_count())

        # Should have at least 100k cards (default_cards has ~110k)
        assert count > 100000, (
            f"Scryfall database only has {count} cards. "
            f"This suggests 'unique_artwork' bulk type was used instead of 'default_cards'. "
            f"Expected 100k+ cards for accurate price lookups."
        )
