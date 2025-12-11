"""Tests for deck analysis tools."""

from __future__ import annotations

import pytest

from mtg_mcp.data.database import MTGDatabase, ScryfallDatabase
from mtg_mcp.data.models.inputs import AnalyzeDeckInput, DeckCardInput, ValidateDeckInput
from mtg_mcp.tools import deck

# =============================================================================
# Test Data
# =============================================================================


def make_modern_burn_deck() -> list[DeckCardInput]:
    """Create a sample Modern burn deck for testing."""
    return [
        DeckCardInput(name="Lightning Bolt", quantity=4),
        DeckCardInput(name="Lava Spike", quantity=4),
        DeckCardInput(name="Rift Bolt", quantity=4),
        DeckCardInput(name="Skullcrack", quantity=4),
        DeckCardInput(name="Shard Volley", quantity=4),
        DeckCardInput(name="Monastery Swiftspear", quantity=4),
        DeckCardInput(name="Goblin Guide", quantity=4),
        DeckCardInput(name="Eidolon of the Great Revel", quantity=4),
        DeckCardInput(name="Light Up the Stage", quantity=4),
        DeckCardInput(name="Searing Blaze", quantity=4),
        DeckCardInput(name="Mountain", quantity=20),
        # Sideboard
        DeckCardInput(name="Smash to Smithereens", quantity=4, sideboard=True),
        DeckCardInput(name="Roiling Vortex", quantity=4, sideboard=True),
    ]


def make_commander_deck_with_issues() -> list[DeckCardInput]:
    """Create a Commander deck with validation issues for testing."""
    return [
        # Valid cards in WUBG identity
        DeckCardInput(name="Sol Ring", quantity=1),
        DeckCardInput(name="Arcane Signet", quantity=1),
        DeckCardInput(name="Command Tower", quantity=1),
        DeckCardInput(name="Swords to Plowshares", quantity=1),
        DeckCardInput(name="Counterspell", quantity=1),
        DeckCardInput(name="Eternal Witness", quantity=1),
        # Red card - outside color identity
        DeckCardInput(name="Lightning Bolt", quantity=1),
        # Duplicate - violates singleton
        DeckCardInput(name="Sol Ring", quantity=1),
        # Basic lands (exempt from singleton)
        DeckCardInput(name="Plains", quantity=10),
        DeckCardInput(name="Island", quantity=10),
        DeckCardInput(name="Swamp", quantity=10),
        DeckCardInput(name="Forest", quantity=10),
    ]


# =============================================================================
# validate_deck Tests
# =============================================================================


class TestValidateDeck:
    """Tests for validate_deck tool."""

    async def test_valid_modern_deck(self, db: MTGDatabase) -> None:
        """Test that a valid Modern deck passes validation."""
        deck_cards = make_modern_burn_deck()
        input_data = ValidateDeckInput(cards=deck_cards, format="modern")

        result = await deck.validate_deck(db, input_data)

        assert result.is_valid is True
        assert result.format == "modern"
        assert result.total_cards == 60
        assert result.sideboard_count == 8
        assert len(result.issues) == 0

    async def test_invalid_deck_size(self, db: MTGDatabase) -> None:
        """Test that a deck with too few cards gets a warning."""
        deck_cards = [
            DeckCardInput(name="Lightning Bolt", quantity=4),
            DeckCardInput(name="Mountain", quantity=10),
        ]
        input_data = ValidateDeckInput(cards=deck_cards, format="modern")

        result = await deck.validate_deck(db, input_data)

        # Deck size issues are warnings, not hard failures
        # (allows for partial deck analysis)
        assert any("60" in w for w in result.warnings)

    async def test_over_copy_limit(self, db: MTGDatabase) -> None:
        """Test that having more than 4 copies of a non-basic card fails."""
        deck_cards = [
            DeckCardInput(name="Lightning Bolt", quantity=5),  # Over limit
            DeckCardInput(name="Mountain", quantity=55),
        ]
        input_data = ValidateDeckInput(cards=deck_cards, format="modern")

        result = await deck.validate_deck(db, input_data)

        assert result.is_valid is False
        assert any(i.card_name == "Lightning Bolt" for i in result.issues)
        assert any(i.issue == "over_copy_limit" for i in result.issues)

    async def test_commander_singleton_violation(self, db: MTGDatabase) -> None:
        """Test that duplicate non-basic cards fail in Commander."""
        deck_cards = make_commander_deck_with_issues()
        input_data = ValidateDeckInput(
            cards=deck_cards,
            format="commander",
            commander="Atraxa, Praetors' Voice",
        )

        result = await deck.validate_deck(db, input_data)

        assert result.is_valid is False
        # Should catch Sol Ring duplicate
        sol_ring_issues = [i for i in result.issues if i.card_name == "Sol Ring"]
        assert len(sol_ring_issues) > 0
        assert any(i.issue == "over_singleton_limit" for i in sol_ring_issues)

    async def test_commander_color_identity_violation(self, db: MTGDatabase) -> None:
        """Test that cards outside commander's color identity fail."""
        deck_cards = make_commander_deck_with_issues()
        input_data = ValidateDeckInput(
            cards=deck_cards,
            format="commander",
            commander="Atraxa, Praetors' Voice",  # WUBG - no red
        )

        result = await deck.validate_deck(db, input_data)

        # Should catch Lightning Bolt (red) being outside color identity
        bolt_issues = [i for i in result.issues if i.card_name == "Lightning Bolt"]
        assert len(bolt_issues) > 0
        assert any(i.issue == "outside_color_identity" for i in bolt_issues)

    async def test_basic_lands_exempt_from_singleton(self, db: MTGDatabase) -> None:
        """Test that basic lands don't trigger singleton violations."""
        deck_cards = [
            DeckCardInput(name="Sol Ring", quantity=1),
            DeckCardInput(name="Plains", quantity=30),  # Many copies OK
            DeckCardInput(name="Island", quantity=30),
            DeckCardInput(name="Swamp", quantity=30),
            DeckCardInput(name="Forest", quantity=9),
        ]
        input_data = ValidateDeckInput(
            cards=deck_cards,
            format="commander",
            commander="Atraxa, Praetors' Voice",
        )

        result = await deck.validate_deck(db, input_data)

        # No issues for basic lands having multiple copies
        land_issues = [
            i for i in result.issues if i.card_name in ("Plains", "Island", "Swamp", "Forest")
        ]
        assert len(land_issues) == 0

    async def test_configurable_checks(self, db: MTGDatabase) -> None:
        """Test that validation checks can be disabled."""
        deck_cards = [
            DeckCardInput(name="Lightning Bolt", quantity=10),  # Way over limit
        ]
        input_data = ValidateDeckInput(
            cards=deck_cards,
            format="modern",
            check_copy_limit=False,  # Disable this check
            check_deck_size=False,  # Disable this check
        )

        result = await deck.validate_deck(db, input_data)

        # Should pass because we disabled the checks
        assert result.is_valid is True


# =============================================================================
# analyze_mana_curve Tests
# =============================================================================


class TestAnalyzeManaCurve:
    """Tests for analyze_mana_curve tool."""

    async def test_burn_deck_curve(self, db: MTGDatabase) -> None:
        """Test mana curve analysis on a burn deck."""
        deck_cards = make_modern_burn_deck()
        input_data = AnalyzeDeckInput(cards=deck_cards)

        result = await deck.analyze_mana_curve(db, input_data)

        # Burn decks should have low average CMC
        assert result.average_cmc < 2.5
        assert result.land_count == 20
        assert result.nonland_count > 0
        # Most cards should be at 1-2 CMC
        assert result.curve.get(1, 0) + result.curve.get(2, 0) > 30

    async def test_empty_deck(self, db: MTGDatabase) -> None:
        """Test mana curve analysis with empty deck."""
        input_data = AnalyzeDeckInput(cards=[])

        result = await deck.analyze_mana_curve(db, input_data)

        assert result.average_cmc == 0.0
        assert result.land_count == 0
        assert result.nonland_count == 0


# =============================================================================
# analyze_colors Tests
# =============================================================================


class TestAnalyzeColors:
    """Tests for analyze_colors tool."""

    async def test_mono_red_deck(self, db: MTGDatabase) -> None:
        """Test color analysis on mono-red deck."""
        deck_cards = make_modern_burn_deck()
        input_data = AnalyzeDeckInput(cards=deck_cards)

        result = await deck.analyze_colors(db, input_data)

        assert result.colors == ["R"]
        assert result.color_identity == ["R"]
        assert "R" in result.mana_pip_totals
        assert result.mana_pip_totals["R"] > 0
        # Should recommend 100% red lands
        assert result.recommended_land_ratio.get("R", 0) == pytest.approx(1.0)

    async def test_colorless_count(self, db: MTGDatabase) -> None:
        """Test that lands are counted as colorless."""
        deck_cards = make_modern_burn_deck()
        input_data = AnalyzeDeckInput(cards=deck_cards)

        result = await deck.analyze_colors(db, input_data)

        # Mountains should be counted as colorless cards
        assert result.colorless_count >= 20


# =============================================================================
# analyze_deck_composition Tests
# =============================================================================


class TestAnalyzeDeckComposition:
    """Tests for analyze_deck_composition tool."""

    async def test_burn_composition(self, db: MTGDatabase) -> None:
        """Test composition analysis on burn deck."""
        deck_cards = make_modern_burn_deck()
        input_data = AnalyzeDeckInput(cards=deck_cards)

        result = await deck.analyze_deck_composition(db, input_data)

        assert result.total_cards > 0
        assert result.creatures > 0
        assert result.lands == 20
        assert result.spells > 0  # Instants + Sorceries
        assert result.interaction > 0  # Burn is interaction

    async def test_type_percentages(self, db: MTGDatabase) -> None:
        """Test that type percentages are reasonable."""
        deck_cards = make_modern_burn_deck()
        input_data = AnalyzeDeckInput(cards=deck_cards)

        result = await deck.analyze_deck_composition(db, input_data)

        # Each type should have a valid percentage
        for type_count in result.types:
            assert 0 <= type_count.percentage <= 100
            assert type_count.count > 0


# =============================================================================
# analyze_deck_price Tests
# =============================================================================


class TestAnalyzeDeckPrice:
    """Tests for analyze_deck_price tool."""

    async def test_price_calculation(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test price analysis returns valid data."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        deck_cards = make_modern_burn_deck()
        input_data = AnalyzeDeckInput(cards=deck_cards)

        result = await deck.analyze_deck_price(db, scryfall, input_data)

        # Should have some price data
        assert result.total_price is not None or len(result.missing_prices) > 0
        # Most expensive should be sorted descending
        if len(result.most_expensive) > 1:
            prices = [c.total_price for c in result.most_expensive if c.total_price]
            assert prices == sorted(prices, reverse=True)

    async def test_mainboard_sideboard_split(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test that mainboard and sideboard prices are calculated separately."""
        if scryfall is None:
            pytest.skip("Scryfall database not available")

        deck_cards = make_modern_burn_deck()
        input_data = AnalyzeDeckInput(cards=deck_cards)

        result = await deck.analyze_deck_price(db, scryfall, input_data)

        # If we have both prices, mainboard + sideboard should equal total
        if result.mainboard_price and result.sideboard_price and result.total_price:
            calculated = result.mainboard_price + result.sideboard_price
            assert abs(calculated - result.total_price) < 0.01
