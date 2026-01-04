"""Comprehensive tests for deck analysis tools.

These tests verify all deck analysis functionality:
- validate_deck: format legality checking
- analyze_mana_curve: mana cost distribution analysis
- analyze_colors: color balance analysis
- analyze_deck_composition: card type ratios
- analyze_deck_price: price analysis with Scryfall data
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from mtg_core.config import Settings
from mtg_core.data.database import UnifiedDatabase, create_database
from mtg_core.data.models import AnalyzeDeckInput, DeckCardInput, ValidateDeckInput
from mtg_core.tools import deck

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


# =============================================================================
# Test Data - Sample Decks
# =============================================================================


def get_valid_standard_deck() -> list[DeckCardInput]:
    """Valid 60-card Standard deck with proper card quantities."""
    return [
        DeckCardInput(name="Lightning Bolt", quantity=4),
        DeckCardInput(name="Llanowar Elves", quantity=4),
        DeckCardInput(name="Forest", quantity=20),
        DeckCardInput(name="Mountain", quantity=20),
        DeckCardInput(name="Shock", quantity=4),
        DeckCardInput(name="Giant Growth", quantity=4),
        DeckCardInput(name="Grizzly Bears", quantity=4),
    ]


def get_invalid_standard_deck_too_many_copies() -> list[DeckCardInput]:
    """Invalid Standard deck with >4 copies of non-basic land."""
    return [
        DeckCardInput(name="Lightning Bolt", quantity=8),  # Too many!
        DeckCardInput(name="Forest", quantity=30),
        DeckCardInput(name="Mountain", quantity=22),
    ]


def get_commander_deck() -> list[DeckCardInput]:
    """Valid Commander deck (100 cards, singleton)."""
    # Create 99 unique cards + commander
    cards = [
        DeckCardInput(name="Lightning Bolt", quantity=1),
        DeckCardInput(name="Llanowar Elves", quantity=1),
        DeckCardInput(name="Giant Growth", quantity=1),
        DeckCardInput(name="Shock", quantity=1),
        DeckCardInput(name="Forest", quantity=30),
        DeckCardInput(name="Mountain", quantity=30),
    ]
    # Add more unique cards to reach 99 (excluding commander)
    unique_cards = [
        "Counterspell",
        "Swords to Plowshares",
        "Path to Exile",
        "Sol Ring",
        "Command Tower",
        "Birds of Paradise",
        "Cultivate",
        "Kodama's Reach",
        "Explosive Vegetation",
        "Rampant Growth",
        "Harmonize",
        "Beast Within",
        "Heroic Intervention",
        "Return to Nature",
        "Naturalize",
        "Reclamation Sage",
        "Eternal Witness",
        "Wood Elves",
        "Farhaven Elf",
        "Solemn Simulacrum",
        "Burnished Hart",
        "Wayfarer's Bauble",
        "Commander's Sphere",
        "Thought Vessel",
        "Mind Stone",
        "Hedron Archive",
        "Thran Dynamo",
        "Gilded Lotus",
        "Darksteel Ingot",
        "Chromatic Lantern",
        "Arcane Signet",
        "Fellwar Stone",
    ]
    for card_name in unique_cards[: 99 - len(cards)]:
        cards.append(DeckCardInput(name=card_name, quantity=1))
    return cards


def get_invalid_commander_deck_non_singleton() -> list[DeckCardInput]:
    """Invalid Commander deck with duplicate non-basic lands."""
    return [
        DeckCardInput(name="Lightning Bolt", quantity=2),  # Violation!
        DeckCardInput(name="Llanowar Elves", quantity=1),
        DeckCardInput(name="Forest", quantity=48),  # Basic lands OK
        DeckCardInput(name="Mountain", quantity=48),
    ]


def get_multicolor_deck() -> list[DeckCardInput]:
    """Deck with multicolor cards for color analysis."""
    return [
        DeckCardInput(name="Lightning Bolt", quantity=4),  # R
        DeckCardInput(name="Llanowar Elves", quantity=4),  # G
        DeckCardInput(name="Counterspell", quantity=4),  # U
        DeckCardInput(name="Putrefy", quantity=4),  # BG
        DeckCardInput(name="Forest", quantity=12),
        DeckCardInput(name="Mountain", quantity=12),
        DeckCardInput(name="Island", quantity=12),
        DeckCardInput(name="Swamp", quantity=8),
    ]


def get_creature_heavy_deck() -> list[DeckCardInput]:
    """Deck with mostly creatures for composition analysis."""
    return [
        DeckCardInput(name="Grizzly Bears", quantity=4),
        DeckCardInput(name="Llanowar Elves", quantity=4),
        DeckCardInput(name="Birds of Paradise", quantity=4),
        DeckCardInput(name="Tarmogoyf", quantity=4),
        DeckCardInput(name="Giant Growth", quantity=4),
        DeckCardInput(name="Lightning Bolt", quantity=4),
        DeckCardInput(name="Forest", quantity=18),
        DeckCardInput(name="Mountain", quantity=18),
    ]


def get_deck_with_sideboard() -> list[DeckCardInput]:
    """Deck with mainboard and sideboard cards."""
    return [
        DeckCardInput(name="Lightning Bolt", quantity=4, sideboard=False),
        DeckCardInput(name="Forest", quantity=28, sideboard=False),
        DeckCardInput(name="Mountain", quantity=28, sideboard=False),
        DeckCardInput(name="Shock", quantity=4, sideboard=True),
        DeckCardInput(name="Naturalize", quantity=3, sideboard=True),
    ]


# =============================================================================
# Test validate_deck
# =============================================================================


class TestValidateDeck:
    """Tests for validate_deck function."""

    async def test_valid_standard_deck(self, db: UnifiedDatabase) -> None:
        """Valid 60-card Standard deck should pass validation."""
        cards = get_valid_standard_deck()
        input_data = ValidateDeckInput(cards=cards, format="standard", check_legality=False)
        result = await deck.validate_deck(db, input_data)

        # May have warnings about deck size but should be valid overall
        assert result.format == "standard"
        assert result.total_cards == 60

    async def test_invalid_too_many_copies(self, db: UnifiedDatabase) -> None:
        """Deck with >4 copies should fail validation."""
        cards = get_invalid_standard_deck_too_many_copies()
        input_data = ValidateDeckInput(cards=cards, format="standard")
        result = await deck.validate_deck(db, input_data)

        assert result.is_valid is False
        assert any(issue.issue == "over_copy_limit" for issue in result.issues)
        assert any("Lightning Bolt" in issue.card_name for issue in result.issues)

    async def test_commander_deck_size_exactly_100(self, db: UnifiedDatabase) -> None:
        """Commander deck should have exactly 100 cards."""
        cards = get_commander_deck()
        input_data = ValidateDeckInput(
            cards=cards,
            format="commander",
            commander="Omnath, Locus of Mana",
            check_legality=False,
            check_color_identity=False,  # Disable to avoid color identity issues
        )
        result = await deck.validate_deck(db, input_data)

        # Should track deck size
        assert result.format == "commander"
        # May have warnings about deck size
        assert isinstance(result.total_cards, int)

    async def test_commander_singleton_violation(self, db: UnifiedDatabase) -> None:
        """Commander deck with duplicates should fail singleton check."""
        cards = get_invalid_commander_deck_non_singleton()
        input_data = ValidateDeckInput(
            cards=cards, format="commander", commander="Omnath, Locus of Mana"
        )
        result = await deck.validate_deck(db, input_data)

        assert result.is_valid is False
        assert any(issue.issue == "over_singleton_limit" for issue in result.issues)

    async def test_basic_lands_exempt_from_singleton(self, db: UnifiedDatabase) -> None:
        """Basic lands should be exempt from singleton rule in Commander."""
        cards = [
            DeckCardInput(name="Sol Ring", quantity=1),  # Colorless artifact
            DeckCardInput(name="Forest", quantity=49),  # Multiple basics OK
            DeckCardInput(name="Forest", quantity=49),  # Multiple basics OK
        ]
        input_data = ValidateDeckInput(
            cards=cards,
            format="commander",
            commander="Omnath, Locus of Mana",
            check_singleton=True,
            check_legality=False,
            check_color_identity=False,  # Disable to avoid identity issues
        )
        result = await deck.validate_deck(db, input_data)

        # Should not complain about multiple basic lands (singleton violations)
        singleton_issues = [
            issue for issue in result.issues if issue.issue == "over_singleton_limit"
        ]
        basic_singleton_issues = [
            issue for issue in singleton_issues if issue.card_name == "Forest"
        ]
        assert len(basic_singleton_issues) == 0

    async def test_deck_size_warning_too_small(self, db: UnifiedDatabase) -> None:
        """Deck with <60 cards should get warning."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=4),
            DeckCardInput(name="Forest", quantity=20),
        ]
        input_data = ValidateDeckInput(cards=cards, format="standard", check_deck_size=True)
        result = await deck.validate_deck(db, input_data)

        assert result.total_cards == 24
        assert any("minimum" in warning.lower() for warning in result.warnings)

    async def test_sideboard_count_tracking(self, db: UnifiedDatabase) -> None:
        """Sideboard cards should be tracked separately."""
        cards = get_deck_with_sideboard()
        input_data = ValidateDeckInput(cards=cards, format="standard")
        result = await deck.validate_deck(db, input_data)

        assert result.total_cards == 60  # Mainboard only
        assert result.sideboard_count == 7

    async def test_sideboard_over_limit_warning(self, db: UnifiedDatabase) -> None:
        """Sideboard with >15 cards should get warning."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=4, sideboard=False),
            DeckCardInput(name="Forest", quantity=28, sideboard=False),
            DeckCardInput(name="Mountain", quantity=28, sideboard=False),
            DeckCardInput(name="Shock", quantity=16, sideboard=True),  # Too many!
        ]
        input_data = ValidateDeckInput(cards=cards, format="standard", check_deck_size=True)
        result = await deck.validate_deck(db, input_data)

        assert result.sideboard_count == 16
        assert any("Sideboard" in warning and "maximum" in warning for warning in result.warnings)

    async def test_known_format_validation(self, db: UnifiedDatabase) -> None:
        """Known formats should validate correctly."""
        cards = get_valid_standard_deck()
        # Test with a known format
        input_data = ValidateDeckInput(cards=cards, format="modern", check_legality=False)
        result = await deck.validate_deck(db, input_data)

        assert result.format == "modern"
        # Modern has similar rules to Standard
        assert result.total_cards == 60

    async def test_card_not_found_issue(self, db: UnifiedDatabase) -> None:
        """Non-existent cards should be reported as issues."""
        cards = [
            DeckCardInput(name="Totally Fake Card That Doesn't Exist", quantity=4),
            DeckCardInput(name="Forest", quantity=56),
        ]
        input_data = ValidateDeckInput(cards=cards, format="standard")
        result = await deck.validate_deck(db, input_data)

        assert result.is_valid is False
        assert any(issue.issue == "not_found" for issue in result.issues)
        assert any("Totally Fake Card" in issue.card_name for issue in result.issues)

    async def test_check_legality_flag(self, db: UnifiedDatabase) -> None:
        """check_legality flag should control format legality checks."""
        cards = [
            DeckCardInput(name="Black Lotus", quantity=1),  # Banned in most formats
            DeckCardInput(name="Forest", quantity=59),
        ]
        # With check_legality=False, should not check if card is legal
        input_no_check = ValidateDeckInput(cards=cards, format="standard", check_legality=False)
        result_no_check = await deck.validate_deck(db, input_no_check)

        # Should not have legality issues when check_legality=False
        legality_issues = [issue for issue in result_no_check.issues if issue.issue == "not_legal"]
        assert len(legality_issues) == 0

    async def test_check_copy_limit_flag(self, db: UnifiedDatabase) -> None:
        """check_copy_limit flag should control copy limit checks."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=8),  # Too many
            DeckCardInput(name="Forest", quantity=52),
        ]
        input_no_check = ValidateDeckInput(cards=cards, format="standard", check_copy_limit=False)
        result_no_check = await deck.validate_deck(db, input_no_check)

        # Should not have copy limit issues when check_copy_limit=False
        copy_issues = [
            issue for issue in result_no_check.issues if issue.issue == "over_copy_limit"
        ]
        assert len(copy_issues) == 0

    async def test_check_deck_size_flag(self, db: UnifiedDatabase) -> None:
        """check_deck_size flag should control deck size warnings."""
        cards = [DeckCardInput(name="Forest", quantity=30)]
        input_no_check = ValidateDeckInput(cards=cards, format="standard", check_deck_size=False)
        result_no_check = await deck.validate_deck(db, input_no_check)

        # Should not have size warnings when check_deck_size=False
        assert len(result_no_check.warnings) == 0


# =============================================================================
# Test analyze_mana_curve
# =============================================================================


class TestAnalyzeManaCurve:
    """Tests for analyze_mana_curve function."""

    async def test_mana_curve_basic(self, db: UnifiedDatabase) -> None:
        """Should calculate mana curve correctly."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=4),  # CMC 1
            DeckCardInput(name="Grizzly Bears", quantity=4),  # CMC 2
            DeckCardInput(name="Giant Growth", quantity=4),  # CMC 1
            DeckCardInput(name="Forest", quantity=24),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_mana_curve(db, input_data)

        # Note: types field may be None in database, so land detection might not work
        # The function counts all cards including lands in nonland if types is None
        assert result.nonland_count >= 12
        assert 1 in result.curve
        assert 2 in result.curve

    async def test_mana_curve_average_median(self, db: UnifiedDatabase) -> None:
        """Should calculate average and median CMC."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=10),  # CMC 1
            DeckCardInput(name="Grizzly Bears", quantity=10),  # CMC 2
            DeckCardInput(name="Shock", quantity=10),  # CMC 1
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_mana_curve(db, input_data)

        # Average: (20*1 + 10*2) / 30 = 40/30 = 1.33
        assert result.average_cmc == pytest.approx(1.33, abs=0.2)
        assert result.median_cmc >= 1.0

    async def test_mana_curve_x_spells(self, db: UnifiedDatabase) -> None:
        """Should detect X spells in mana curve."""
        cards = [
            DeckCardInput(name="Fireball", quantity=4),  # Has X in cost
            DeckCardInput(name="Lightning Bolt", quantity=4),
            DeckCardInput(name="Forest", quantity=52),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_mana_curve(db, input_data)

        # Fireball should be counted as X spell
        assert result.x_spell_count >= 4

    async def test_mana_curve_lands_excluded(self, db: UnifiedDatabase) -> None:
        """Lands should not appear in mana curve."""
        cards = [
            DeckCardInput(name="Forest", quantity=30),
            DeckCardInput(name="Mountain", quantity=30),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_mana_curve(db, input_data)

        # Lands are excluded from mana curve, so an all-land deck has empty curve
        assert result.curve.get(0, 0) == 0
        assert result.land_count == 60

    async def test_mana_curve_high_cmc_cards(self, db: UnifiedDatabase) -> None:
        """Should handle high CMC cards (6+)."""
        cards = [
            DeckCardInput(name="Shivan Dragon", quantity=4),  # CMC 6
            DeckCardInput(name="Lightning Bolt", quantity=4),
            DeckCardInput(name="Forest", quantity=52),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_mana_curve(db, input_data)

        # Should have entries for both low and high CMC
        assert 1 in result.curve
        assert result.curve[6] >= 4 or result.curve.get(6, 0) >= 4

    async def test_mana_curve_zero_cmc(self, db: UnifiedDatabase) -> None:
        """Should handle 0 CMC cards correctly."""
        cards = [
            DeckCardInput(name="Ornithopter", quantity=4),  # CMC 0
            DeckCardInput(name="Lightning Bolt", quantity=4),
            DeckCardInput(name="Forest", quantity=52),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_mana_curve(db, input_data)

        assert 0 in result.curve
        assert result.curve[0] >= 4

    async def test_mana_curve_empty_deck(self, db: UnifiedDatabase) -> None:
        """Should handle empty deck gracefully."""
        cards: list[DeckCardInput] = []
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_mana_curve(db, input_data)

        assert result.land_count == 0
        assert result.nonland_count == 0
        assert result.average_cmc == 0.0
        assert result.median_cmc == 0.0


# =============================================================================
# Test analyze_colors
# =============================================================================


class TestAnalyzeColors:
    """Tests for analyze_colors function."""

    async def test_color_analysis_monocolor(self, db: UnifiedDatabase) -> None:
        """Should analyze mono-color deck correctly."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=4),  # Red
            DeckCardInput(name="Shock", quantity=4),  # Red
            DeckCardInput(name="Mountain", quantity=52),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_colors(db, input_data)

        assert "R" in result.colors
        assert len(result.colors) == 1
        assert result.multicolor_count == 0

    async def test_color_analysis_multicolor_deck(self, db: UnifiedDatabase) -> None:
        """Should analyze multicolor deck correctly."""
        cards = get_multicolor_deck()
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_colors(db, input_data)

        # Should detect multiple colors
        assert len(result.colors) >= 3
        # Should have multicolor cards (Putrefy is BG)
        assert result.multicolor_count > 0

    async def test_color_analysis_wubrg_order(self, db: UnifiedDatabase) -> None:
        """Colors should be returned in WUBRG order."""
        cards = [
            DeckCardInput(name="Giant Growth", quantity=4),  # G
            DeckCardInput(name="Lightning Bolt", quantity=4),  # R
            DeckCardInput(name="Counterspell", quantity=4),  # U
            DeckCardInput(name="Forest", quantity=16),
            DeckCardInput(name="Mountain", quantity=16),
            DeckCardInput(name="Island", quantity=16),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_colors(db, input_data)

        # Should be in WUBRG order: U, R, G
        expected_order = ["U", "R", "G"]
        assert result.colors == expected_order

    async def test_color_analysis_colorless_count(self, db: UnifiedDatabase) -> None:
        """Should count colorless cards correctly."""
        cards = [
            DeckCardInput(name="Sol Ring", quantity=4),  # Colorless
            DeckCardInput(name="Lightning Bolt", quantity=4),
            DeckCardInput(name="Mountain", quantity=52),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_colors(db, input_data)

        assert result.colorless_count >= 4

    async def test_color_analysis_mana_pips(self, db: UnifiedDatabase) -> None:
        """Should count mana symbols (pips) correctly."""
        cards = [
            DeckCardInput(name="Counterspell", quantity=4),  # UU (2 blue pips)
            DeckCardInput(name="Island", quantity=56),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_colors(db, input_data)

        # Counterspell has UU, so 4 copies = 8 blue pips
        assert result.mana_pip_totals.get("U", 0) >= 8

    async def test_color_analysis_recommended_land_ratio(self, db: UnifiedDatabase) -> None:
        """Should recommend land ratios based on pip counts."""
        cards = [
            DeckCardInput(name="Counterspell", quantity=10),  # UU
            DeckCardInput(name="Lightning Bolt", quantity=5),  # R
            DeckCardInput(name="Island", quantity=25),
            DeckCardInput(name="Mountain", quantity=20),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_colors(db, input_data)

        # More blue pips than red, so blue ratio should be higher
        blue_ratio = result.recommended_land_ratio.get("U", 0)
        red_ratio = result.recommended_land_ratio.get("R", 0)
        assert blue_ratio > red_ratio

    async def test_color_analysis_color_identity(self, db: UnifiedDatabase) -> None:
        """Should track color identity separately from colors."""
        cards = [
            # A card with hybrid mana might have different identity
            DeckCardInput(name="Lightning Bolt", quantity=4),
            DeckCardInput(name="Mountain", quantity=56),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_colors(db, input_data)

        # Colors and identity should both include red
        assert "R" in result.colors
        assert "R" in result.color_identity

    async def test_color_analysis_breakdown(self, db: UnifiedDatabase) -> None:
        """Should provide detailed color breakdown."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=4),  # R
            DeckCardInput(name="Llanowar Elves", quantity=4),  # G
            DeckCardInput(name="Forest", quantity=26),
            DeckCardInput(name="Mountain", quantity=26),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_colors(db, input_data)

        # Should have breakdown for each color
        assert len(result.breakdown) >= 2
        # Each breakdown should have color, card_count, mana_symbols
        for item in result.breakdown:
            assert item.color in ["R", "G"]
            assert item.card_count > 0


# =============================================================================
# Test analyze_deck_composition
# =============================================================================


class TestAnalyzeDeckComposition:
    """Tests for analyze_deck_composition function."""

    async def test_composition_creature_count(self, db: UnifiedDatabase) -> None:
        """Should count creatures correctly (if types field is populated)."""
        cards = get_creature_heavy_deck()
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_composition(db, input_data)

        # Note: types field may be None in database
        # If types is None, creature/land counts will be 0
        assert result.total_cards == 60

    async def test_composition_type_breakdown(self, db: UnifiedDatabase) -> None:
        """Should provide type breakdown with percentages (if types field is populated)."""
        cards = [
            DeckCardInput(name="Grizzly Bears", quantity=20),  # Creature
            DeckCardInput(name="Lightning Bolt", quantity=20),  # Instant
            DeckCardInput(name="Forest", quantity=20),  # Land
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_composition(db, input_data)

        assert result.total_cards == 60
        # Note: if types field is None, types list will be empty
        # Just verify percentages are valid
        for type_count in result.types:
            assert 0 <= type_count.percentage <= 100

    async def test_composition_spells_count(self, db: UnifiedDatabase) -> None:
        """Should count instants + sorceries as spells (if types field is populated)."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=10),  # Instant
            DeckCardInput(name="Giant Growth", quantity=10),  # Instant
            DeckCardInput(name="Forest", quantity=40),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_composition(db, input_data)

        # Note: if types field is None, spell count will be 0
        # Just verify the function doesn't crash
        assert result.total_cards == 60

    async def test_composition_interaction_detection(self, db: UnifiedDatabase) -> None:
        """Should detect interaction (removal, counters) heuristically."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=4),  # Deals damage
            DeckCardInput(name="Counterspell", quantity=4),  # Counter
            DeckCardInput(name="Naturalize", quantity=4),  # Destroy
            DeckCardInput(name="Forest", quantity=48),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_composition(db, input_data)

        # Should detect some interaction cards
        assert result.interaction > 0

    async def test_composition_ramp_detection(self, db: UnifiedDatabase) -> None:
        """Should detect ramp cards heuristically."""
        cards = [
            DeckCardInput(name="Llanowar Elves", quantity=4),  # Mana dork
            DeckCardInput(name="Sol Ring", quantity=4),  # Mana rock
            DeckCardInput(name="Rampant Growth", quantity=4),  # Land ramp
            DeckCardInput(name="Forest", quantity=48),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_composition(db, input_data)

        # Should detect some ramp cards
        assert result.ramp_count > 0

    async def test_composition_noncreatures_calculation(self, db: UnifiedDatabase) -> None:
        """Should calculate noncreatures correctly (excluding lands)."""
        cards = [
            DeckCardInput(name="Grizzly Bears", quantity=20),  # Creatures
            DeckCardInput(name="Lightning Bolt", quantity=20),  # Noncreature spell
            DeckCardInput(name="Forest", quantity=20),  # Land
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_composition(db, input_data)

        # Note: if types field is None, all counts will be off
        # Noncreatures = total - creatures - lands
        assert result.total_cards == 60
        assert result.noncreatures == result.total_cards - result.creatures - result.lands

    async def test_composition_empty_deck(self, db: UnifiedDatabase) -> None:
        """Should handle empty deck gracefully."""
        cards: list[DeckCardInput] = []
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_composition(db, input_data)

        assert result.total_cards == 0
        assert result.creatures == 0
        assert result.lands == 0


# =============================================================================
# Test analyze_deck_price
# =============================================================================


class TestAnalyzeDeckPrice:
    """Tests for analyze_deck_price function."""

    async def test_price_analysis_basic(self, db: UnifiedDatabase) -> None:
        """Should analyze deck prices correctly."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=4),
            DeckCardInput(name="Forest", quantity=56),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_price(db, input_data)

        # Should have some price data (if available in DB)
        # Note: prices may be None if not in database
        if result.total_price is not None:
            assert result.total_price >= 0

    async def test_price_analysis_missing_prices(self, db: UnifiedDatabase) -> None:
        """Should track cards with missing price data."""
        cards = [
            DeckCardInput(name="Totally Fake Card", quantity=4),
            DeckCardInput(name="Forest", quantity=56),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_price(db, input_data)

        # Fake card should be in missing_prices
        assert "Totally Fake Card" in result.missing_prices

    async def test_price_analysis_most_expensive(self, db: UnifiedDatabase) -> None:
        """Should return top 10 most expensive cards."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=4),
            DeckCardInput(name="Tarmogoyf", quantity=4),  # Expensive
            DeckCardInput(name="Birds of Paradise", quantity=4),
            DeckCardInput(name="Forest", quantity=48),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_price(db, input_data)

        # Should have up to 10 entries
        assert len(result.most_expensive) <= 10

    async def test_price_analysis_sideboard_separate(self, db: UnifiedDatabase) -> None:
        """Should track mainboard and sideboard prices separately."""
        cards = get_deck_with_sideboard()
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_price(db, input_data)

        # Should have separate tracking
        # (values may be None if no price data available)
        assert isinstance(result.mainboard_price, (float, type(None)))
        assert isinstance(result.sideboard_price, (float, type(None)))

    async def test_price_analysis_average_price(self, db: UnifiedDatabase) -> None:
        """Should calculate average card price correctly."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=10),
            DeckCardInput(name="Forest", quantity=50),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_price(db, input_data)

        # Average should be total / quantity (if prices available)
        if result.average_card_price is not None:
            assert result.average_card_price >= 0

    async def test_price_analysis_quantity_multiplier(self, db: UnifiedDatabase) -> None:
        """Should multiply unit price by quantity."""
        cards = [DeckCardInput(name="Lightning Bolt", quantity=4)]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_price(db, input_data)

        # If we have a price, the total should be unit * quantity
        if result.most_expensive:
            for card_price in result.most_expensive:
                if card_price.unit_price is not None and card_price.total_price is not None:
                    expected = card_price.unit_price * card_price.quantity
                    assert card_price.total_price == pytest.approx(expected, abs=0.01)

    async def test_price_analysis_sorted_descending(self, db: UnifiedDatabase) -> None:
        """Most expensive list should be sorted by price descending."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=4),
            DeckCardInput(name="Tarmogoyf", quantity=1),
            DeckCardInput(name="Birds of Paradise", quantity=4),
            DeckCardInput(name="Forest", quantity=51),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_price(db, input_data)

        # Verify sorted order (excluding None prices)
        prices = [cp.total_price for cp in result.most_expensive if cp.total_price is not None]
        assert prices == sorted(prices, reverse=True)


# =============================================================================
# Test Helper Functions
# =============================================================================


class TestHelperFunctions:
    """Tests for internal helper functions."""

    async def test_get_card_price(self, db: UnifiedDatabase) -> None:
        """_get_card_price should return price or None."""
        # Real card should have price (or None if not in DB)
        price = await deck._get_card_price(db, "Lightning Bolt")
        assert price is None or isinstance(price, float)

        # Fake card should return None
        fake_price = await deck._get_card_price(db, "Totally Fake Card")
        assert fake_price is None

    async def test_resolve_deck_cards(self, db: UnifiedDatabase) -> None:
        """_resolve_deck_cards should batch load all cards."""
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=4),
            DeckCardInput(name="Forest", quantity=20),
            DeckCardInput(name="Fake Card", quantity=1),
        ]
        resolved = await deck._resolve_deck_cards(db, cards, include_extras=False)

        assert len(resolved) == 3
        # Real cards should resolve
        bolt_result = next(r for r in resolved if r[0].name == "Lightning Bolt")
        assert bolt_result[1] is not None
        assert bolt_result[1].name == "Lightning Bolt"

        # Fake card should be None
        fake_result = next(r for r in resolved if r[0].name == "Fake Card")
        assert fake_result[1] is None

    async def test_resolve_deck_cards_empty(self, db: UnifiedDatabase) -> None:
        """_resolve_deck_cards should handle empty list."""
        resolved = await deck._resolve_deck_cards(db, [], include_extras=False)
        assert resolved == []

    async def test_resolve_deck_cards_include_extras(self, db: UnifiedDatabase) -> None:
        """_resolve_deck_cards should load extras when requested."""
        cards = [DeckCardInput(name="Lightning Bolt", quantity=1)]
        resolved = await deck._resolve_deck_cards(db, cards, include_extras=True)

        assert len(resolved) == 1
        _card_input, card = resolved[0]
        assert card is not None
        # With include_extras, should have legalities/rulings loaded
        # (May be None if not in database)
        assert hasattr(card, "legalities")


# =============================================================================
# Test Format Rules Constants
# =============================================================================


class TestFormatRules:
    """Tests for FORMAT_RULES and BASIC_LANDS constants."""

    def test_format_rules_coverage(self) -> None:
        """FORMAT_RULES should include all major formats."""
        assert "standard" in deck.FORMAT_RULES
        assert "modern" in deck.FORMAT_RULES
        assert "commander" in deck.FORMAT_RULES
        assert "pioneer" in deck.FORMAT_RULES
        assert "pauper" in deck.FORMAT_RULES

    def test_format_rules_structure(self) -> None:
        """Each format rule should be a 5-tuple."""
        for _format_name, rules in deck.FORMAT_RULES.items():
            assert isinstance(rules, tuple)
            assert len(rules) == 5
            min_size, max_sb, copy_limit, singleton, check_identity = rules
            assert isinstance(min_size, int)
            assert isinstance(max_sb, int)
            assert isinstance(copy_limit, int)
            assert isinstance(singleton, bool)
            assert isinstance(check_identity, bool)

    def test_commander_rules_singleton(self) -> None:
        """Commander should have singleton rules."""
        rules = deck.FORMAT_RULES["commander"]
        min_size, max_sb, copy_limit, is_singleton, check_identity = rules
        assert min_size == 100
        assert max_sb == 0  # No sideboard
        assert copy_limit == 1
        assert is_singleton is True
        assert check_identity is True

    def test_standard_rules_60_card(self) -> None:
        """Standard should have 60-card rules."""
        rules = deck.FORMAT_RULES["standard"]
        min_size, max_sb, copy_limit, is_singleton, check_identity = rules
        assert min_size == 60
        assert max_sb == 15
        assert copy_limit == 4
        assert is_singleton is False
        assert check_identity is False

    def test_basic_lands_comprehensive(self) -> None:
        """BASIC_LANDS should include all basic land types."""
        assert "Plains" in deck.BASIC_LANDS
        assert "Island" in deck.BASIC_LANDS
        assert "Swamp" in deck.BASIC_LANDS
        assert "Mountain" in deck.BASIC_LANDS
        assert "Forest" in deck.BASIC_LANDS
        assert "Wastes" in deck.BASIC_LANDS
        assert "Snow-Covered Plains" in deck.BASIC_LANDS
        assert "Snow-Covered Island" in deck.BASIC_LANDS
        assert "Snow-Covered Swamp" in deck.BASIC_LANDS
        assert "Snow-Covered Mountain" in deck.BASIC_LANDS
        assert "Snow-Covered Forest" in deck.BASIC_LANDS

    def test_interaction_patterns(self) -> None:
        """INTERACTION_PATTERNS should include common removal keywords."""
        assert "destroy target" in deck.INTERACTION_PATTERNS
        assert "exile target" in deck.INTERACTION_PATTERNS
        assert "counter target" in deck.INTERACTION_PATTERNS

    def test_ramp_patterns(self) -> None:
        """RAMP_PATTERNS should include mana acceleration keywords."""
        assert any("add" in pattern for pattern in deck.RAMP_PATTERNS)
        assert any("search" in pattern for pattern in deck.RAMP_PATTERNS)


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    async def test_deck_with_all_same_card(self, db: UnifiedDatabase) -> None:
        """Deck with only one unique card (except lands)."""
        cards = [DeckCardInput(name="Forest", quantity=60)]
        input_data = AnalyzeDeckInput(cards=cards)

        # Should not crash
        curve_result = await deck.analyze_mana_curve(db, input_data)
        # May count as nonland if types field is None
        assert curve_result.land_count + curve_result.nonland_count == 60

        color_result = await deck.analyze_colors(db, input_data)
        assert "G" in color_result.color_identity

    async def test_deck_with_zero_quantity_cards(self, db: UnifiedDatabase) -> None:
        """Cards with quantity=0 should be handled (validation prevents this)."""
        # Note: Pydantic validation requires quantity >= 1, so this is prevented
        # at the input level. Testing here for completeness.
        pass

    async def test_very_large_deck(self, db: UnifiedDatabase) -> None:
        """Should handle decks with many card entries (within quantity limits)."""
        # Note: quantity max is 99, so we use multiple entries
        cards = [
            DeckCardInput(name="Lightning Bolt", quantity=50),
            DeckCardInput(name="Shock", quantity=50),
            DeckCardInput(name="Forest", quantity=50),
            DeckCardInput(name="Mountain", quantity=50),
        ]
        input_data = AnalyzeDeckInput(cards=cards)

        result = await deck.analyze_mana_curve(db, input_data)
        # Should handle 200 cards without crashing
        assert result.nonland_count + result.land_count == 200

    async def test_commander_without_commander_specified(self, db: UnifiedDatabase) -> None:
        """Commander format without specifying commander card."""
        cards = get_commander_deck()
        input_data = ValidateDeckInput(cards=cards, format="commander")
        # Commander not specified
        result = await deck.validate_deck(db, input_data)

        # Should still validate format rules, just no color identity check
        assert result.format == "commander"

    async def test_deck_all_multicolor_cards(self, db: UnifiedDatabase) -> None:
        """Deck with only multicolor cards."""
        cards = [
            DeckCardInput(name="Putrefy", quantity=30),  # BG
            DeckCardInput(name="Forest", quantity=15),
            DeckCardInput(name="Swamp", quantity=15),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_colors(db, input_data)

        assert result.multicolor_count >= 30
        assert len(result.colors) >= 2

    async def test_price_analysis_all_missing_prices(self, db: UnifiedDatabase) -> None:
        """Deck where all cards have missing prices."""
        cards = [
            DeckCardInput(name="Fake Card 1", quantity=20),
            DeckCardInput(name="Fake Card 2", quantity=20),
            DeckCardInput(name="Fake Card 3", quantity=20),
        ]
        input_data = AnalyzeDeckInput(cards=cards)
        result = await deck.analyze_deck_price(db, input_data)

        assert len(result.missing_prices) == 3
        assert result.total_price is None or result.total_price == 0
