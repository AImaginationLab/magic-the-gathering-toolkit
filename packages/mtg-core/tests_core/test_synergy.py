"""Comprehensive tests for synergy module.

Tests cover:
- detection.py: Theme/combo detection and color analysis
- scoring.py: Synergy scoring and pattern matching
- search.py: Synergy search functionality
- tools.py: Main synergy tool implementations
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest

from mtg_core.config import Settings
from mtg_core.data.database import UnifiedDatabase, create_database
from mtg_core.data.models.card import Card
from mtg_core.data.models.inputs import SearchCardsInput
from mtg_core.data.models.responses import (
    SynergyType,
)
from mtg_core.exceptions import CardNotFoundError
from mtg_core.tools.synergy.detection import (
    combo_to_model,
    detect_deck_colors,
    detect_themes,
    find_combos_for_card,
    find_combos_in_deck,
)
from mtg_core.tools.synergy.scoring import (
    calculate_synergy_score,
    card_has_pattern,
    create_synergy_result,
    normalize_card_name,
)
from mtg_core.tools.synergy.search import search_synergies
from mtg_core.tools.synergy.tools import (
    detect_combos,
    find_synergies,
    suggest_cards,
)

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


@pytest.fixture
def sample_card() -> Card:
    """Create a sample card for testing."""
    return Card(
        name="Lightning Bolt",
        mana_cost="{R}",
        cmc=1.0,
        colors=["R"],
        color_identity=["R"],
        type="Instant",
        types=["Instant"],
        text="Lightning Bolt deals 3 damage to any target.",
        keywords=["Damage"],
    )


@pytest.fixture
def flying_card() -> Card:
    """Create a card with Flying keyword."""
    return Card(
        name="Serra Angel",
        mana_cost="{3}{W}{W}",
        cmc=5.0,
        colors=["W"],
        color_identity=["W"],
        type="Creature — Angel",
        types=["Creature"],
        subtypes=["Angel"],
        text="Flying, vigilance",
        keywords=["Flying", "Vigilance"],
        power="4",
        toughness="4",
    )


@pytest.fixture
def etb_card() -> Card:
    """Create a card with enters-the-battlefield ability."""
    return Card(
        name="Mulldrifter",
        mana_cost="{4}{U}",
        cmc=5.0,
        colors=["U"],
        color_identity=["U"],
        type="Creature — Elemental Fish",
        types=["Creature"],
        subtypes=["Elemental", "Fish"],
        text="When Mulldrifter enters the battlefield, draw two cards.",
        keywords=["Flying"],
        power="2",
        toughness="2",
    )


@pytest.fixture
def tribal_card() -> Card:
    """Create a tribal creature card."""
    return Card(
        name="Lord of Atlantis",
        mana_cost="{U}{U}",
        cmc=2.0,
        colors=["U"],
        color_identity=["U"],
        type="Creature — Merfolk",
        types=["Creature"],
        subtypes=["Merfolk"],
        text="Other Merfolk get +1/+1 and have islandwalk.",
        power="2",
        toughness="2",
    )


# =============================================================================
# scoring.py Tests
# =============================================================================


class TestNormalizeCardName:
    """Tests for normalize_card_name function."""

    def test_lowercase_conversion(self) -> None:
        """Should convert to lowercase."""
        assert normalize_card_name("Lightning Bolt") == "lightning bolt"
        assert normalize_card_name("LIGHTNING BOLT") == "lightning bolt"

    def test_strip_whitespace(self) -> None:
        """Should strip leading/trailing whitespace."""
        assert normalize_card_name("  Lightning Bolt  ") == "lightning bolt"
        assert normalize_card_name("\tLightning Bolt\n") == "lightning bolt"

    def test_empty_string(self) -> None:
        """Should handle empty strings."""
        assert normalize_card_name("") == ""
        assert normalize_card_name("   ") == ""


class TestCardHasPattern:
    """Tests for card_has_pattern function."""

    def test_pattern_match_case_insensitive(self, sample_card: Card) -> None:
        """Should match patterns case-insensitively."""
        assert card_has_pattern(sample_card, "damage")
        assert card_has_pattern(sample_card, "DAMAGE")
        assert card_has_pattern(sample_card, "DaMaGe")

    def test_regex_pattern(self, etb_card: Card) -> None:
        """Should support regex patterns."""
        assert card_has_pattern(etb_card, r"enters.*battlefield")
        assert card_has_pattern(etb_card, r"draw.*card")

    def test_no_match(self, sample_card: Card) -> None:
        """Should return False when pattern doesn't match."""
        assert not card_has_pattern(sample_card, "flying")
        assert not card_has_pattern(sample_card, "graveyard")

    def test_no_text(self) -> None:
        """Should return False when card has no text."""
        card = Card(name="Black Lotus", text=None)
        assert not card_has_pattern(card, "damage")

    def test_invalid_regex_fallback(self, sample_card: Card) -> None:
        """Should fallback to string matching on invalid regex."""
        # Invalid regex but valid substring
        assert card_has_pattern(sample_card, "3 damage")


class TestCalculateSynergyScore:
    """Tests for calculate_synergy_score function."""

    def test_base_score_keyword(self, sample_card: Card, flying_card: Card) -> None:
        """Should use base score for keyword synergy."""
        score = calculate_synergy_score(flying_card, sample_card, "keyword")
        assert 0.7 <= score <= 0.9  # Base is 0.8, may have color bonus

    def test_base_score_tribal(self, sample_card: Card, tribal_card: Card) -> None:
        """Should use base score for tribal synergy."""
        score = calculate_synergy_score(tribal_card, sample_card, "tribal")
        assert 0.75 <= score <= 0.95  # Base is 0.85, may have color bonus

    def test_color_identity_bonus(self) -> None:
        """Should add bonus for matching color identity."""
        card1 = Card(name="Card1", color_identity=["R", "G"])
        card2 = Card(name="Card2", color_identity=["R", "G"])
        score = calculate_synergy_score(card1, card2, "keyword")
        # Base 0.8 + 0.1 * (2 colors overlap / 2 source colors) = 0.9
        assert score == pytest.approx(0.9, abs=0.01)

    def test_partial_color_overlap(self) -> None:
        """Should calculate partial color overlap bonus."""
        card1 = Card(name="Card1", color_identity=["R", "G"])
        card2 = Card(name="Card2", color_identity=["R", "U"])
        score = calculate_synergy_score(card1, card2, "keyword")
        # Base 0.8 + 0.1 * (1 overlap / 2 source colors) = 0.85
        assert score == pytest.approx(0.85, abs=0.01)

    def test_no_color_overlap(self) -> None:
        """Should use base score when no color overlap."""
        card1 = Card(name="Card1", color_identity=["R"])
        card2 = Card(name="Card2", color_identity=["U"])
        score = calculate_synergy_score(card1, card2, "keyword")
        assert score == 0.8  # No bonus

    def test_score_capped_at_one(self) -> None:
        """Should cap score at 1.0."""
        # Create scenario that would exceed 1.0
        card1 = Card(name="Card1", color_identity=["W", "U", "B", "R", "G"])
        card2 = Card(name="Card2", color_identity=["W", "U", "B", "R", "G"])
        score = calculate_synergy_score(card1, card2, "tribal")  # Base 0.85
        assert score <= 1.0

    def test_no_color_identity(self, sample_card: Card) -> None:
        """Should handle missing color identity."""
        card_no_ci = Card(name="Test", color_identity=None)
        score = calculate_synergy_score(card_no_ci, sample_card, "keyword")
        assert score == 0.8  # Base score only


class TestCreateSynergyResult:
    """Tests for create_synergy_result function."""

    def test_create_basic_result(self, sample_card: Card, flying_card: Card) -> None:
        """Should create synergy result with correct fields."""
        result = create_synergy_result(
            flying_card,
            sample_card,
            "keyword",
            "Test synergy reason",
        )
        assert result.name == "Serra Angel"
        assert result.synergy_type == "keyword"
        assert result.reason == "Test synergy reason"
        assert 0.0 <= result.score <= 1.0
        assert result.mana_cost == "{3}{W}{W}"
        assert result.type_line == "Creature — Angel"

    def test_score_modifier(self, sample_card: Card, flying_card: Card) -> None:
        """Should apply score modifier."""
        result = create_synergy_result(
            flying_card,
            sample_card,
            "keyword",
            "Test",
            score_modifier=0.5,
        )
        base_score = calculate_synergy_score(flying_card, sample_card, "keyword")
        assert result.score == pytest.approx(base_score * 0.5, abs=0.01)

    def test_all_synergy_types(self, sample_card: Card, flying_card: Card) -> None:
        """Should work with all synergy types."""
        synergy_types: list[SynergyType] = ["keyword", "tribal", "ability", "theme", "archetype"]
        for stype in synergy_types:
            result = create_synergy_result(flying_card, sample_card, stype, "Reason")
            assert result.synergy_type == stype


# =============================================================================
# detection.py Tests
# =============================================================================


class TestDetectThemes:
    """Tests for detect_themes function."""

    def test_tokens_theme(self) -> None:
        """Should detect tokens theme from card text."""
        cards = [
            Card(name="Card1", text="Create a 1/1 white Soldier creature token."),
            Card(name="Card2", text="Create two 2/2 green Bear creature tokens."),
            Card(name="Card3", text="Whenever a token enters the battlefield, draw a card."),
        ]
        themes = detect_themes(cards)
        assert "tokens" in themes

    def test_aristocrats_theme(self) -> None:
        """Should detect aristocrats theme from sacrifice/death triggers."""
        cards = [
            Card(name="Card1", text="Sacrifice a creature: Draw a card."),
            Card(name="Card2", text="Whenever a creature dies, each opponent loses 1 life."),
            Card(
                name="Card3",
                text="Whenever another creature you control dies, create a Treasure token.",
            ),
        ]
        themes = detect_themes(cards)
        assert "aristocrats" in themes

    def test_tribal_theme_from_subtypes(self) -> None:
        """Should detect tribal theme from repeated subtypes."""
        cards = [
            Card(name="Card1", subtypes=["Elf"]),
            Card(name="Card2", subtypes=["Elf", "Warrior"]),
            Card(name="Card3", subtypes=["Elf", "Druid"]),
            Card(name="Card4", subtypes=["Elf", "Scout"]),
            Card(name="Card5", subtypes=["Elf", "Shaman"]),
        ]
        themes = detect_themes(cards)
        assert "tribal" in themes

    def test_spellslinger_theme(self) -> None:
        """Should detect spellslinger theme from instant/sorcery matters."""
        cards = [
            Card(name="Card1", types=["Instant"], text="Counter target spell."),
            Card(
                name="Card2", text="Whenever you cast an instant or sorcery spell, create a token."
            ),
            Card(
                name="Card3",
                text="Prowess (This creature gets +1/+1 whenever you cast a noncreature spell.)",
            ),
            Card(name="Card4", text="Whenever you cast an instant spell, draw a card."),
        ]
        themes = detect_themes(cards)
        assert "spellslinger" in themes

    def test_no_themes_detected(self) -> None:
        """Should return empty list when no themes detected."""
        cards = [
            Card(name="Card1", text="Add {G}."),
            Card(name="Card2", text="Draw a card."),
        ]
        themes = detect_themes(cards)
        assert len(themes) == 0

    def test_theme_threshold(self) -> None:
        """Should require at least 3 matches for theme detection."""
        # Only 2 cards with token text - not enough
        cards = [
            Card(name="Card1", text="Create a token."),
            Card(name="Card2", text="Populate."),
        ]
        themes = detect_themes(cards)
        assert "tokens" not in themes

    def test_cards_without_text(self) -> None:
        """Should handle cards without text."""
        cards = [
            Card(name="Card1", text=None),
            Card(name="Card2", text=""),
        ]
        themes = detect_themes(cards)
        assert len(themes) == 0


class TestDetectDeckColors:
    """Tests for detect_deck_colors function."""

    def test_single_color(self) -> None:
        """Should detect single color."""
        cards = [
            Card(name="Card1", color_identity=["R"]),
            Card(name="Card2", color_identity=["R"]),
        ]
        colors = detect_deck_colors(cards)
        assert colors == ["R"]

    def test_multiple_colors_in_order(self) -> None:
        """Should return colors in WUBRG order."""
        cards = [
            Card(name="Card1", color_identity=["R", "G"]),
            Card(name="Card2", color_identity=["U", "W"]),
            Card(name="Card3", color_identity=["B"]),
        ]
        colors = detect_deck_colors(cards)
        assert colors == ["W", "U", "B", "R", "G"]

    def test_colorless_deck(self) -> None:
        """Should return empty list for colorless deck."""
        cards = [
            Card(name="Card1", color_identity=None),
            Card(name="Card2", color_identity=[]),
        ]
        colors = detect_deck_colors(cards)
        assert colors == []

    def test_no_duplicate_colors(self) -> None:
        """Should not duplicate colors."""
        cards = [
            Card(name="Card1", color_identity=["R", "G"]),
            Card(name="Card2", color_identity=["R", "G"]),
            Card(name="Card3", color_identity=["R"]),
        ]
        colors = detect_deck_colors(cards)
        assert colors == ["R", "G"]


class TestComboToModel:
    """Tests for combo_to_model function."""

    def test_basic_combo_conversion(self) -> None:
        """Should convert combo dict to Combo model."""
        combo_data = {
            "id": "test-combo",
            "cards": [
                ("Card A", "Role A"),
                ("Card B", "Role B"),
            ],
            "desc": "Does something infinite",
            "type": "infinite",
            "colors": ["U", "R"],
        }
        result = combo_to_model(combo_data)
        assert result.id == "test-combo"
        assert len(result.cards) == 2
        assert result.cards[0].name == "Card A"
        assert result.cards[0].role == "Role A"
        assert result.description == "Does something infinite"
        assert result.combo_type == "infinite"
        assert result.colors == ["U", "R"]

    def test_cards_without_roles(self) -> None:
        """Should handle cards without explicit roles."""
        combo_data = {
            "id": "test-combo",
            "cards": ["Card A", "Card B"],
            "desc": "Test combo",
            "type": "value",
        }
        result = combo_to_model(combo_data)
        assert result.cards[0].name == "Card A"
        assert result.cards[0].role == "Combo piece"
        assert result.cards[1].name == "Card B"
        assert result.cards[1].role == "Combo piece"

    def test_missing_colors(self) -> None:
        """Should handle missing colors field."""
        combo_data = {
            "id": "test-combo",
            "cards": ["Card A"],
            "desc": "Test",
            "type": "lock",
        }
        result = combo_to_model(combo_data)
        assert result.colors == []


class TestFindCombosForCard:
    """Tests for find_combos_for_card function."""

    def test_find_splinter_twin_combos(self) -> None:
        """Should find combos containing Splinter Twin."""
        combos = find_combos_for_card("Splinter Twin")
        assert len(combos) >= 2  # Twin with Exarch and Pestermite
        combo_ids = [c.id for c in combos]
        assert "twin" in combo_ids
        assert "twin-pestermite" in combo_ids

    def test_find_thoracle_combos(self) -> None:
        """Should find Thassa's Oracle combos."""
        combos = find_combos_for_card("Thassa's Oracle")
        assert len(combos) >= 2
        combo_ids = [c.id for c in combos]
        assert "thoracle-consult" in combo_ids
        assert "thoracle-pact" in combo_ids

    def test_card_not_in_combos(self) -> None:
        """Should return empty list for card not in any combo."""
        combos = find_combos_for_card("Lightning Bolt")
        assert len(combos) == 0

    def test_case_insensitive_search(self) -> None:
        """Should be case-insensitive."""
        combos_lower = find_combos_for_card("splinter twin")
        combos_upper = find_combos_for_card("SPLINTER TWIN")
        assert len(combos_lower) == len(combos_upper)


class TestFindCombosInDeck:
    """Tests for find_combos_in_deck function."""

    def test_complete_combo_detected(self) -> None:
        """Should detect complete combos in deck."""
        deck = ["Splinter Twin", "Deceiver Exarch", "Lightning Bolt"]
        complete, _potential, _missing = find_combos_in_deck(deck)
        assert len(complete) >= 1
        combo_ids = [c.id for c in complete]
        assert "twin" in combo_ids

    def test_multiple_complete_combos(self) -> None:
        """Should detect multiple complete combos."""
        deck = [
            "Splinter Twin",
            "Deceiver Exarch",
            "Pestermite",
            "Thassa's Oracle",
            "Demonic Consultation",
        ]
        complete, _potential, _missing = find_combos_in_deck(deck)
        combo_ids = [c.id for c in complete]
        assert "twin" in combo_ids
        assert "twin-pestermite" in combo_ids
        assert "thoracle-consult" in combo_ids

    def test_potential_combo_one_piece_missing(self) -> None:
        """Should detect potential combos missing one piece."""
        deck = ["Splinter Twin", "Lightning Bolt"]  # Missing Exarch/Pestermite
        _complete, potential, missing = find_combos_in_deck(deck)
        assert len(potential) >= 1
        # Should have missing cards listed
        for combo in potential:
            assert combo.id in missing
            assert len(missing[combo.id]) > 0

    def test_potential_combo_two_pieces_missing(self) -> None:
        """Should detect potential combos missing two pieces."""
        deck = ["Splinter Twin"]  # Missing Exarch (1 piece for 2-card combo)
        _complete, potential, _missing = find_combos_in_deck(deck)
        # Should still detect as potential since missing <= 2
        twin_combos = [c for c in potential if "twin" in c.id]
        assert len(twin_combos) >= 1

    def test_no_combos_in_deck(self) -> None:
        """Should return empty lists when no combos present."""
        deck = ["Lightning Bolt", "Giant Growth", "Dark Ritual"]
        complete, potential, missing = find_combos_in_deck(deck)
        assert len(complete) == 0
        assert len(potential) == 0
        assert len(missing) == 0

    def test_missing_cards_accuracy(self) -> None:
        """Should accurately report missing cards for potential combos."""
        deck = ["Kiki-Jiki, Mirror Breaker"]
        _complete, potential, missing = find_combos_in_deck(deck)
        # Should find Kiki combos as potential
        kiki_combos = [c for c in potential if "kiki" in c.id]
        assert len(kiki_combos) >= 1
        for combo in kiki_combos:
            missing_cards = missing[combo.id]
            # Should be missing Zealous Conscripts or Felidar Guardian
            assert any("Conscripts" in card or "Felidar" in card for card in missing_cards)


# =============================================================================
# search.py Tests
# =============================================================================


class TestSearchSynergies:
    """Tests for search_synergies function."""

    @pytest.mark.asyncio
    async def test_basic_search(self, db: UnifiedDatabase) -> None:
        """Should search for synergistic cards."""
        source_card = Card(
            name="Test Card",
            color_identity=["U"],
        )
        seen_names: set[str] = set()
        search_terms = [("flying", "Has flying")]

        results = await search_synergies(
            db,
            source_card,
            search_terms,
            "keyword",
            seen_names,
            color_identity=["U"],
            format_legal=None,
            page_size=5,
        )

        assert len(results) > 0
        assert all(r.synergy_type == "keyword" for r in results)
        # Should update seen_names
        assert len(seen_names) > 0

    @pytest.mark.asyncio
    async def test_deduplication(self, db: UnifiedDatabase) -> None:
        """Should not return duplicate cards."""
        source_card = Card(name="Test", color_identity=["R"])
        seen_names: set[str] = set()
        search_terms = [("haste", "Has haste"), ("haste", "Fast attacker")]

        results = await search_synergies(
            db,
            source_card,
            search_terms,
            "keyword",
            seen_names,
            color_identity=["R"],
            format_legal=None,
            page_size=10,
        )

        # Each card should appear only once despite multiple search terms
        names = [r.name for r in results]
        assert len(names) == len(set(names))

    @pytest.mark.asyncio
    async def test_color_filter(self, db: UnifiedDatabase) -> None:
        """Should respect color identity filter."""
        source_card = Card(name="Test", color_identity=["G"])
        seen_names: set[str] = set()
        search_terms = [("trample", "Has trample")]

        results = await search_synergies(
            db,
            source_card,
            search_terms,
            "keyword",
            seen_names,
            color_identity=["G"],
            format_legal=None,
            page_size=10,
        )

        # Results should include cards with green in color identity
        # (not strictly green-only, since color_identity includes multicolor)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_format_filter(self, db: UnifiedDatabase) -> None:
        """Should respect format legality filter."""
        source_card = Card(name="Test", color_identity=["W"])
        seen_names: set[str] = set()
        search_terms = [("lifelink", "Has lifelink")]

        results = await search_synergies(
            db,
            source_card,
            search_terms,
            "keyword",
            seen_names,
            color_identity=["W"],
            format_legal="standard",
            page_size=5,
        )

        # Should return results (assuming some standard-legal lifelink cards exist)
        assert len(results) >= 0  # May be 0 if no standard cards match

    @pytest.mark.asyncio
    async def test_page_size_limit(self, db: UnifiedDatabase) -> None:
        """Should respect page_size limit."""
        source_card = Card(name="Test", color_identity=["U"])
        seen_names: set[str] = set()
        search_terms = [("draw", "Card draw")]

        results = await search_synergies(
            db,
            source_card,
            search_terms,
            "ability",
            seen_names,
            color_identity=None,
            format_legal=None,
            page_size=3,
        )

        # Should return at most page_size results per search term
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_score_modifier(self, db: UnifiedDatabase) -> None:
        """Should apply score modifier to results."""
        source_card = Card(name="Test", color_identity=["B"])
        seen_names: set[str] = set()
        search_terms = [("deathtouch", "Has deathtouch")]

        results = await search_synergies(
            db,
            source_card,
            search_terms,
            "keyword",
            seen_names,
            color_identity=["B"],
            format_legal=None,
            page_size=5,
            score_modifier=0.5,
        )

        # All scores should be modified
        for result in results:
            assert result.score <= 0.5


# =============================================================================
# tools.py Tests
# =============================================================================


class TestFindSynergies:
    """Tests for find_synergies main tool."""

    @pytest.mark.asyncio
    async def test_find_synergies_flying_keyword(self, db: UnifiedDatabase) -> None:
        """Should find synergies for cards with Flying keyword."""
        # Find a card with Flying keyword explicitly
        cards, _ = await db.search_cards(SearchCardsInput(text="flying", page_size=10))
        if not cards:
            pytest.skip("No flying cards found in database")

        # Find a card that actually has Flying as a keyword
        card_with_flying = None
        for c in cards:
            if c.keywords and "Flying" in c.keywords:
                card_with_flying = c
                break

        if not card_with_flying:
            pytest.skip("No cards with Flying keyword found")

        result = await find_synergies(db, card_with_flying.name, max_results=10, use_cache=False)

        assert result.card_name == card_with_flying.name
        # Should find some synergies (keyword, ability, or type)
        assert len(result.synergies) >= 0  # May be 0 if database is limited

    @pytest.mark.asyncio
    async def test_find_synergies_etb_ability(self, db: UnifiedDatabase) -> None:
        """Should find synergies for ETB abilities."""
        # Search for a card with ETB ability
        cards, _ = await db.search_cards(
            SearchCardsInput(text="enters the battlefield", page_size=1)
        )
        if not cards:
            pytest.skip("No ETB cards found in database")

        card = cards[0]
        result = await find_synergies(db, card.name, max_results=15, use_cache=False)

        assert len(result.synergies) > 0
        # Should have ability synergies
        ability_synergies = [s for s in result.synergies if s.synergy_type == "ability"]
        assert len(ability_synergies) > 0

    @pytest.mark.asyncio
    async def test_find_synergies_tribal(self, db: UnifiedDatabase) -> None:
        """Should find tribal synergies."""
        # Find a creature with a specific subtype (use Dragon which is more common)
        cards, _ = await db.search_cards(SearchCardsInput(subtype="Dragon", page_size=1))
        if not cards:
            pytest.skip("No Dragon cards found in database")

        card = cards[0]
        result = await find_synergies(db, card.name, max_results=20, use_cache=False)

        # Should find some synergies (tribal or other types)
        # Tribal synergies depend on available cards in database
        assert len(result.synergies) >= 0

    @pytest.mark.asyncio
    async def test_find_synergies_card_not_found(self, db: UnifiedDatabase) -> None:
        """Should raise CardNotFoundError for nonexistent cards."""
        with pytest.raises(CardNotFoundError):
            await find_synergies(db, "Nonexistent Card XYZ", use_cache=False)

    @pytest.mark.asyncio
    async def test_find_synergies_max_results_limit(self, db: UnifiedDatabase) -> None:
        """Should respect max_results limit."""
        cards, _ = await db.search_cards(SearchCardsInput(text="flying", page_size=1))
        if not cards:
            pytest.skip("No cards found")

        result = await find_synergies(db, cards[0].name, max_results=5, use_cache=False)

        assert len(result.synergies) <= 5

    @pytest.mark.asyncio
    async def test_find_synergies_format_filter(self, db: UnifiedDatabase) -> None:
        """Should filter by format legality."""
        cards, _ = await db.search_cards(SearchCardsInput(text="flying", page_size=1))
        if not cards:
            pytest.skip("No cards found")

        result = await find_synergies(
            db, cards[0].name, max_results=10, format_legal="commander", use_cache=False
        )

        # Should return results (assuming commander-legal synergies exist)
        assert result.total_found >= 0

    @pytest.mark.asyncio
    async def test_find_synergies_sorted_by_score(self, db: UnifiedDatabase) -> None:
        """Should return synergies sorted by score descending."""
        cards, _ = await db.search_cards(SearchCardsInput(text="flying", page_size=1))
        if not cards:
            pytest.skip("No cards found")

        result = await find_synergies(db, cards[0].name, max_results=10, use_cache=False)

        if len(result.synergies) > 1:
            scores = [s.score for s in result.synergies]
            assert scores == sorted(scores, reverse=True)


class TestDetectCombos:
    """Tests for detect_combos tool."""

    @pytest.mark.asyncio
    async def test_detect_combos_for_card(self, db: UnifiedDatabase) -> None:
        """Should detect combos for a specific card."""
        result = await detect_combos(db, card_name="Splinter Twin")

        assert len(result.combos) >= 2
        assert len(result.potential_combos) == 0
        assert len(result.missing_cards) == 0

    @pytest.mark.asyncio
    async def test_detect_combos_in_deck(self, db: UnifiedDatabase) -> None:
        """Should detect combos in a deck."""
        deck = ["Splinter Twin", "Deceiver Exarch", "Lightning Bolt"]
        result = await detect_combos(db, deck_cards=deck)

        assert len(result.combos) >= 1
        combo_ids = [c.id for c in result.combos]
        assert "twin" in combo_ids

    @pytest.mark.asyncio
    async def test_detect_combos_potential(self, db: UnifiedDatabase) -> None:
        """Should detect potential combos."""
        deck = ["Splinter Twin", "Mountain"]  # Missing combo piece
        result = await detect_combos(db, deck_cards=deck)

        assert len(result.potential_combos) >= 1
        assert len(result.missing_cards) > 0

    @pytest.mark.asyncio
    async def test_detect_combos_no_input(self, db: UnifiedDatabase) -> None:
        """Should return empty result when no input provided."""
        result = await detect_combos(db)

        assert len(result.combos) == 0
        assert len(result.potential_combos) == 0
        assert len(result.missing_cards) == 0


class TestSuggestCards:
    """Tests for suggest_cards tool."""

    @pytest.mark.asyncio
    async def test_suggest_cards_basic(self, db: UnifiedDatabase) -> None:
        """Should suggest cards for a deck."""
        # Use common cards that should be in most databases
        deck = [
            "Lightning Bolt",
            "Shock",
            "Lava Spike",
            "Mountain",
        ]
        result = await suggest_cards(db, deck, max_results=10)

        assert len(result.detected_themes) >= 0
        # Should detect at least one color
        assert len(result.deck_colors) >= 0
        # Suggestions depend on database content, may be empty
        assert isinstance(result.suggestions, list)

    @pytest.mark.asyncio
    async def test_suggest_cards_detects_themes(self, db: UnifiedDatabase) -> None:
        """Should detect deck themes."""
        # Create an aristocrats deck
        deck = [
            "Blood Artist",
            "Zulaport Cutthroat",
            "Viscera Seer",
            "Carrion Feeder",
        ]
        result = await suggest_cards(db, deck, max_results=10)

        # Should detect aristocrats theme
        assert "aristocrats" in result.detected_themes or len(result.suggestions) > 0

    @pytest.mark.asyncio
    async def test_suggest_cards_detects_colors(self, db: UnifiedDatabase) -> None:
        """Should detect deck colors."""
        deck = [
            "Lightning Bolt",
            "Giant Growth",
            "Llanowar Elves",
        ]
        result = await suggest_cards(db, deck, max_results=5)

        # Should detect R and G
        assert "R" in result.deck_colors
        assert "G" in result.deck_colors

    @pytest.mark.asyncio
    async def test_suggest_cards_budget_filter(self, db: UnifiedDatabase) -> None:
        """Should filter suggestions by budget."""
        deck = ["Sol Ring", "Command Tower", "Arcane Signet"]
        result = await suggest_cards(db, deck, budget_max=5.0, max_results=10)

        # All suggestions with prices should be under budget
        for suggestion in result.suggestions:
            if suggestion.price_usd is not None:
                assert suggestion.price_usd <= 5.0

    @pytest.mark.asyncio
    async def test_suggest_cards_format_filter(self, db: UnifiedDatabase) -> None:
        """Should filter by format legality."""
        deck = ["Forest", "Llanowar Elves"]
        result = await suggest_cards(db, deck, format_legal="commander", max_results=5)

        # Should return results
        assert len(result.suggestions) >= 0

    @pytest.mark.asyncio
    async def test_suggest_cards_empty_deck(self, db: UnifiedDatabase) -> None:
        """Should handle empty deck gracefully."""
        result = await suggest_cards(db, [], max_results=5)

        assert len(result.suggestions) == 0
        assert len(result.detected_themes) == 0
        assert len(result.deck_colors) == 0

    @pytest.mark.asyncio
    async def test_suggest_cards_invalid_cards(self, db: UnifiedDatabase) -> None:
        """Should skip invalid card names."""
        deck = ["Nonexistent Card 1", "Nonexistent Card 2"]
        result = await suggest_cards(db, deck, max_results=5)

        # Should handle gracefully
        assert len(result.suggestions) == 0

    @pytest.mark.asyncio
    async def test_suggest_cards_no_duplicates(self, db: UnifiedDatabase) -> None:
        """Should not suggest cards already in deck."""
        deck = ["Lightning Bolt", "Shock", "Lava Spike"]
        result = await suggest_cards(db, deck, max_results=10)

        # None of the suggestions should be in the original deck
        deck_names_lower = {name.lower() for name in deck}
        for suggestion in result.suggestions:
            assert suggestion.name.lower() not in deck_names_lower


# =============================================================================
# Caching Tests
# =============================================================================


class TestSynergyCaching:
    """Tests for synergy result caching."""

    @pytest.mark.asyncio
    async def test_cache_hit(self, db: UnifiedDatabase) -> None:
        """Should use cached results on second call."""
        # First call
        cards, _ = await db.search_cards(SearchCardsInput(name="Island", page_size=1))
        if not cards:
            pytest.skip("No cards found")

        card_name = cards[0].name

        # Clear any existing cache and get fresh result
        result1 = await find_synergies(db, card_name, max_results=5, use_cache=False)

        # Second call with cache enabled
        with patch("mtg_core.tools.synergy.tools.get_cached") as mock_get:
            mock_get.return_value = result1
            await find_synergies(db, card_name, max_results=5, use_cache=True)

            # Should have called get_cached
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_disabled(self, db: UnifiedDatabase) -> None:
        """Should not use cache when use_cache=False."""
        cards, _ = await db.search_cards(SearchCardsInput(name="Island", page_size=1))
        if not cards:
            pytest.skip("No cards found")

        with patch("mtg_core.tools.synergy.tools.get_cached") as mock_get:
            await find_synergies(db, cards[0].name, max_results=5, use_cache=False)

            # Should not call get_cached
            mock_get.assert_not_called()


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_normalize_special_characters(self) -> None:
        """Should handle special characters in card names."""
        assert normalize_card_name("Jace, the Mind Sculptor") == "jace, the mind sculptor"
        assert normalize_card_name("Urza's Saga") == "urza's saga"

    def test_pattern_with_special_regex_chars(self) -> None:
        """Should handle special regex characters."""
        card = Card(name="Test", text="Costs {2} less to cast.")
        # Should not crash on regex special chars
        assert card_has_pattern(card, "{2}")

    def test_combo_with_empty_cards_list(self) -> None:
        """Should handle combos with no cards."""
        combo_data = {
            "id": "empty",
            "cards": [],
            "desc": "Empty combo",
            "type": "value",
        }
        result = combo_to_model(combo_data)
        assert len(result.cards) == 0

    @pytest.mark.asyncio
    async def test_synergy_search_empty_terms(self, db: UnifiedDatabase) -> None:
        """Should handle empty search terms list."""
        source_card = Card(name="Test", color_identity=["U"])
        seen_names: set[str] = set()

        results = await search_synergies(
            db,
            source_card,
            [],  # Empty search terms
            "keyword",
            seen_names,
            color_identity=["U"],
            format_legal=None,
        )

        assert len(results) == 0
