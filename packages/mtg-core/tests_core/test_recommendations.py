"""Comprehensive tests for MTG recommendation system."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock

import pytest

from mtg_core.tools.recommendations.features import CardFeatures, DeckFeatures
from mtg_core.tools.recommendations.hybrid import (
    ComboPieceDetector,
    HybridRecommender,
    ScoredRecommendation,
    SynergyScorer,
    calculate_land_need,
    get_target_land_count,
    is_basic_or_simple_land,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# BASIC/SIMPLE LAND DETECTION TESTS
# ============================================================================


class TestBasicOrSimpleLand:
    """Test is_basic_or_simple_land function for scoring reduction."""

    def test_basic_lands_detected(self) -> None:
        """Basic lands should be detected."""
        basic_lands = [
            {"name": "Plains", "type": "Basic Land — Plains", "text": ""},
            {"name": "Island", "type": "Basic Land — Island", "text": ""},
            {"name": "Swamp", "type": "Basic Land — Swamp", "text": ""},
            {"name": "Mountain", "type": "Basic Land — Mountain", "text": ""},
            {"name": "Forest", "type": "Basic Land — Forest", "text": ""},
        ]
        for land in basic_lands:
            assert is_basic_or_simple_land(land), f"{land['name']} should be basic"

    def test_snow_covered_basics_detected(self) -> None:
        """Snow-Covered basics should be detected."""
        snow_lands = [
            {"name": "Snow-Covered Plains", "type": "Basic Snow Land — Plains", "text": ""},
            {"name": "Snow-Covered Island", "type": "Basic Snow Land — Island", "text": ""},
        ]
        for land in snow_lands:
            assert is_basic_or_simple_land(land), f"{land['name']} should be basic"

    def test_simple_mana_lands_detected(self) -> None:
        """Simple lands with only tap for mana should be detected."""
        # These are simplified test fixtures, not actual oracle text.
        # Real City of Brass has damage clause, Ancient Ziggurat has creature restriction.
        simple_lands = [
            # Hypothetical simple land - just taps for mana with short text
            {"name": "Test Mana Land", "type": "Land", "text": "{T}: Add {C}."},
            {"name": "Exotic Orchard", "type": "Land", "text": "{T}: Add one mana of any color."},
        ]
        for land in simple_lands:
            # Short text with just mana production should be considered simple
            assert is_basic_or_simple_land(land), f"{land['name']} should be simple"

    def test_complex_mana_lands_not_simple(self) -> None:
        """Lands with restrictions or damage should NOT be detected as simple."""
        complex_lands = [
            # City of Brass deals damage when tapped
            {
                "name": "City of Brass",
                "type": "Land",
                "text": "Whenever City of Brass becomes tapped, it deals 1 damage to you.\n{T}: Add one mana of any color.",
            },
            # Ancient Ziggurat has creature spell restriction
            {
                "name": "Ancient Ziggurat",
                "type": "Land",
                "text": "{T}: Add one mana of any color. Spend this mana only to cast a creature spell.",
            },
        ]
        for land in complex_lands:
            assert not is_basic_or_simple_land(land), f"{land['name']} should NOT be simple"

    def test_utility_lands_not_detected(self) -> None:
        """Utility lands with special abilities should NOT be detected."""
        utility_lands = [
            {
                "name": "Bojuka Bog",
                "type": "Land",
                "text": "Bojuka Bog enters the battlefield tapped. When Bojuka Bog enters the battlefield, exile all cards from target player's graveyard.",
            },
            {
                "name": "Urza's Saga",
                "type": "Enchantment Land — Urza's Saga",
                "text": 'I, II — Urza\'s Saga gains "{T}: Add {C}." III — Search your library...',
            },
            {
                "name": "Flooded Strand",
                "type": "Land",
                "text": "{T}, Pay 1 life, Sacrifice Flooded Strand: Search your library for a Plains or Island card...",
            },
            {
                "name": "Raging Ravine",
                "type": "Land",
                "text": "Raging Ravine enters the battlefield tapped. {T}: Add {R} or {G}. {2}{R}{G}: Until end of turn, Raging Ravine becomes a 3/3 creature...",
            },
            {
                "name": "Boseiju, Who Endures",
                "type": "Legendary Land",
                "text": "{T}: Add {G}. Channel — {1}{G}, Discard Boseiju...",
            },
        ]
        for land in utility_lands:
            assert not is_basic_or_simple_land(land), f"{land['name']} should NOT be simple"

    def test_non_lands_not_affected(self) -> None:
        """Non-land cards should return False."""
        non_lands = [
            {"name": "Sol Ring", "type": "Artifact", "text": "{T}: Add {C}{C}."},
            {
                "name": "Birds of Paradise",
                "type": "Creature — Bird",
                "text": "{T}: Add one mana of any color.",
            },
        ]
        for card in non_lands:
            assert not is_basic_or_simple_land(card), f"{card['name']} is not a land"


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_card_data() -> dict[str, dict[str, Any]]:
    """Sample card data for testing."""
    return {
        "Sol Ring": {
            "name": "Sol Ring",
            "type": "Artifact",
            "text": "{T}: Add {C}{C}.",
            "colorIdentity": [],
            "edhrecRank": 1,
            "uuid": "sol-ring-uuid",
        },
        "Command Tower": {
            "name": "Command Tower",
            "type": "Land",
            "text": "{T}: Add one mana of any color in your commander's color identity.",
            "colorIdentity": ["W", "U", "B", "R", "G"],
            "edhrecRank": 2,
            "uuid": "command-tower-uuid",
        },
        "Temple Garden": {
            "name": "Temple Garden",
            "type": "Land - Forest Plains",
            "text": "({T}: Add {G} or {W}.)",
            "colorIdentity": ["W", "G"],
            "edhrecRank": 50,
            "uuid": "temple-garden-uuid",
        },
        "Hallowed Fountain": {
            "name": "Hallowed Fountain",
            "type": "Land - Plains Island",
            "text": "({T}: Add {W} or {U}.)",
            "colorIdentity": ["W", "U"],
            "edhrecRank": 60,
            "uuid": "hallowed-fountain-uuid",
        },
        "Godless Shrine": {
            "name": "Godless Shrine",
            "type": "Land - Plains Swamp",
            "text": "({T}: Add {W} or {B}.)",
            "colorIdentity": ["W", "B"],
            "edhrecRank": 70,
            "uuid": "godless-shrine-uuid",
        },
        "Plains": {
            "name": "Plains",
            "type": "Basic Land - Plains",
            "text": "({T}: Add {W}.)",
            "colorIdentity": ["W"],
            "edhrecRank": 100,
            "uuid": "plains-uuid",
        },
        "Island": {
            "name": "Island",
            "type": "Basic Land - Island",
            "text": "({T}: Add {U}.)",
            "colorIdentity": ["U"],
            "edhrecRank": 100,
            "uuid": "island-uuid",
        },
        "Swamp": {
            "name": "Swamp",
            "type": "Basic Land - Swamp",
            "text": "({T}: Add {B}.)",
            "colorIdentity": ["B"],
            "edhrecRank": 100,
            "uuid": "swamp-uuid",
        },
        "Lightning Bolt": {
            "name": "Lightning Bolt",
            "type": "Instant",
            "text": "Lightning Bolt deals 3 damage to any target.",
            "colorIdentity": ["R"],
            "edhrecRank": 100,
            "uuid": "lightning-bolt-uuid",
        },
        "Counterspell": {
            "name": "Counterspell",
            "type": "Instant",
            "text": "Counter target spell.",
            "colorIdentity": ["U"],
            "edhrecRank": 150,
            "uuid": "counterspell-uuid",
        },
    }


@pytest.fixture
def mock_tfidf_recommender(mock_card_data: dict[str, dict[str, Any]]) -> Mock:
    """Mock TF-IDF recommender."""
    from dataclasses import dataclass

    @dataclass
    class TfidfRec:
        name: str
        score: float
        uuid: str | None
        type_line: str | None
        mana_cost: str | None
        colors: list[str] | None

    recommender = Mock()
    recommender._card_data = mock_card_data

    # Default behavior: return non-lands
    def find_similar_side_effect(
        card_names: list[str], n: int = 20, exclude_input: bool = True
    ) -> list[TfidfRec]:
        results = []
        for card_name, card_data in mock_card_data.items():
            if exclude_input and card_name in card_names:
                continue
            if "Land" not in card_data.get("type", ""):
                results.append(
                    TfidfRec(
                        name=card_name,
                        score=0.8,
                        uuid=card_data.get("uuid"),
                        type_line=card_data.get("type"),
                        mana_cost=card_data.get("manaCost"),
                        colors=card_data.get("colors"),
                    )
                )
        return results[:n]

    recommender.find_similar_to_cards = Mock(side_effect=find_similar_side_effect)
    return recommender


@pytest.fixture
def mock_database() -> AsyncMock:
    """Mock database."""
    return AsyncMock()


@pytest.fixture
def hybrid_recommender(
    mock_tfidf_recommender: Mock, mock_card_data: dict[str, dict[str, Any]]
) -> HybridRecommender:
    """Initialized hybrid recommender with mocked dependencies."""
    recommender = HybridRecommender()
    recommender._tfidf = mock_tfidf_recommender
    recommender._card_data = mock_card_data
    recommender._initialized = True
    recommender._scorer = SynergyScorer()
    recommender._combo_detector = None  # Disable combos for basic tests
    recommender._spellbook_detector = None
    recommender._limited_stats = None
    return recommender


def create_deck_cards(
    creature_count: int = 10,
    spell_count: int = 10,
    land_count: int = 20,
    colors: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Helper to create test deck cards."""
    if colors is None:
        colors = ["W", "U"]

    cards = []

    # Add creatures
    for i in range(creature_count):
        cards.append(
            {
                "name": f"Creature {i}",
                "type": "Creature - Human",
                "colorIdentity": colors,
                "cmc": 3,
                "text": "A creature card",
            }
        )

    # Add spells
    for i in range(spell_count):
        cards.append(
            {
                "name": f"Spell {i}",
                "type": "Instant",
                "colorIdentity": colors,
                "cmc": 2,
                "text": "A spell card",
            }
        )

    # Add lands
    for i in range(land_count):
        cards.append(
            {
                "name": f"Land {i}",
                "type": "Land",
                "colorIdentity": colors,
                "text": "A land card",
            }
        )

    return cards


# ============================================================================
# LAND COUNT CALCULATION TESTS
# ============================================================================


class TestLandCountCalculation:
    """Test land count target and need calculation."""

    @pytest.mark.parametrize(
        "deck_size,expected_min,expected_max",
        [
            (100, 35, 40),  # Commander
            (99, 35, 40),  # Commander (99 + commander)
            (60, 22, 26),  # Standard
            (40, 16, 18),  # Limited
            (30, 7, 10),  # Small deck
            (20, 5, 6),  # Very small
        ],
    )
    def test_get_target_land_count(
        self, deck_size: int, expected_min: int, expected_max: int
    ) -> None:
        """Test target land count calculation for different deck sizes."""
        min_lands, max_lands = get_target_land_count(deck_size)
        assert min_lands == expected_min
        assert max_lands == expected_max

    @pytest.mark.parametrize(
        "deck_size,current_lands,expected_need",
        [
            (60, 24, 0.0),  # Has enough lands
            (60, 22, 0.0),  # At minimum
            (60, 15, 0.7),  # Needs ~7 lands (7/10 = 0.7)
            (60, 10, 1.2),  # Needs 12 lands (capped at 1.5)
            (60, 5, 1.5),  # Critically needs lands (capped)
            (100, 38, 0.0),  # Commander with enough
            (100, 30, 0.5),  # Commander needs 5 lands
            (100, 20, 1.5),  # Commander critically needs lands
        ],
    )
    def test_calculate_land_need(
        self, deck_size: int, current_lands: int, expected_need: float
    ) -> None:
        """Test land need calculation with different scenarios."""
        need = calculate_land_need(deck_size, current_lands)
        assert abs(need - expected_need) < 0.01


# ============================================================================
# LAND CAP TESTS (CRITICAL)
# ============================================================================


class TestLandCap:
    """Test land recommendation capping logic."""

    def test_land_cap_100_recommendations(self, hybrid_recommender: HybridRecommender) -> None:
        """When requesting 100 recommendations, at most 10 should be lands (10%)."""
        # Deck with no lands (needs lands urgently)
        deck_cards = create_deck_cards(creature_count=30, spell_count=30, land_count=0)

        # Request 100 recommendations
        results = hybrid_recommender.recommend_for_deck(deck_cards, n=100, explain=False)

        # Count lands in results
        land_count = sum(1 for rec in results if rec.type_line and "Land" in rec.type_line)

        # Should be capped at 10% = 10 lands max
        assert land_count <= 10, f"Expected max 10 lands, got {land_count}"

    def test_land_cap_50_recommendations(self, hybrid_recommender: HybridRecommender) -> None:
        """When requesting 50 recommendations, at most 5 should be lands."""
        deck_cards = create_deck_cards(creature_count=20, spell_count=20, land_count=0)

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=50, explain=False)
        land_count = sum(1 for rec in results if rec.type_line and "Land" in rec.type_line)

        assert land_count <= 5, f"Expected max 5 lands, got {land_count}"

    def test_land_cap_minimum_3(self, hybrid_recommender: HybridRecommender) -> None:
        """When requesting small number, should get at least 3 lands (if deck needs them)."""
        deck_cards = create_deck_cards(creature_count=15, spell_count=10, land_count=5)

        # Request only 20 recommendations
        results = hybrid_recommender.recommend_for_deck(deck_cards, n=20, explain=False)
        land_count = sum(1 for rec in results if rec.type_line and "Land" in rec.type_line)

        # max(20 // 10, 3) = 3
        # But also depends on availability and scoring
        assert land_count <= 3, f"Expected max 3 lands, got {land_count}"

    def test_land_cap_with_10_recommendations(self, hybrid_recommender: HybridRecommender) -> None:
        """With only 10 recommendations, cap should be 3 lands."""
        deck_cards = create_deck_cards(creature_count=10, spell_count=10, land_count=0)

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=10, explain=False)
        land_count = sum(1 for rec in results if rec.type_line and "Land" in rec.type_line)

        # max(10 // 10, 3) = 3
        assert land_count <= 3, f"Expected max 3 lands, got {land_count}"


# ============================================================================
# LAND PENALTY TESTS
# ============================================================================


class TestLandPenalty:
    """Test land penalty when deck doesn't need lands."""

    def test_penalty_applied_when_deck_has_enough_lands(
        self, hybrid_recommender: HybridRecommender
    ) -> None:
        """When land_need <= 0, lands should get -0.5 penalty."""
        # Deck with plenty of lands (24 in 60-card deck)
        deck_cards = create_deck_cards(creature_count=20, spell_count=16, land_count=24)

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=50, explain=True)

        # Find land recommendations
        land_recs = [rec for rec in results if rec.type_line and "Land" in rec.type_line]

        for rec in land_recs:
            # Land score should be negative (-0.5 penalty)
            assert rec.land_score == -0.5, (
                f"Expected land_score=-0.5 for {rec.name}, got {rec.land_score}"
            )

    def test_lands_deprioritized_when_not_needed(
        self, hybrid_recommender: HybridRecommender
    ) -> None:
        """Lands should be ranked lower when deck has enough."""
        deck_cards = create_deck_cards(creature_count=20, spell_count=16, land_count=24)

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=30, explain=False)

        # Find position of first land
        first_land_position = None
        for i, rec in enumerate(results):
            if rec.type_line and "Land" in rec.type_line:
                first_land_position = i
                break

        # First land should NOT be in top 10 (since deck doesn't need lands)
        if first_land_position is not None:
            assert first_land_position >= 10, (
                f"Land appeared at position {first_land_position}, should be deprioritized"
            )


# ============================================================================
# LAND BOOST TESTS
# ============================================================================


class TestLandBoost:
    """Test land boost when deck needs lands."""

    def test_lands_boosted_when_deck_needs_them(
        self, hybrid_recommender: HybridRecommender
    ) -> None:
        """When land_need > 0, lands should get positive land_score."""
        # Deck with very few lands
        deck_cards = create_deck_cards(creature_count=25, spell_count=20, land_count=10)

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=30, explain=True)

        # Find land recommendations
        land_recs = [rec for rec in results if rec.type_line and "Land" in rec.type_line]

        for rec in land_recs:
            # Land score should be positive
            assert rec.land_score > 0, (
                f"Expected positive land_score for {rec.name}, got {rec.land_score}"
            )

    def test_matching_color_lands_get_bonus(self, hybrid_recommender: HybridRecommender) -> None:
        """Lands matching deck colors should get higher scores."""
        # Esper deck (W/U/B)
        deck_cards = create_deck_cards(
            creature_count=25, spell_count=20, land_count=10, colors=["W", "U", "B"]
        )

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=30, explain=True)

        # Find specific dual lands
        temple_garden = next(
            (r for r in results if r.name == "Temple Garden"), None
        )  # W/G (1 match)
        hallowed_fountain = next(
            (r for r in results if r.name == "Hallowed Fountain"), None
        )  # W/U (2 matches)
        # Esper lands should score higher than off-color lands
        if hallowed_fountain and temple_garden:
            assert hallowed_fountain.land_score > temple_garden.land_score, (
                "Hallowed Fountain (W/U) should score higher than Temple Garden (W/G) in Esper deck"
            )


# ============================================================================
# SCORE CALCULATION TESTS
# ============================================================================


class TestScoreCalculation:
    """Test total score calculation with different components."""

    def test_total_score_combines_all_components(
        self, hybrid_recommender: HybridRecommender
    ) -> None:
        """Total score should combine all weighted components."""
        deck_cards = create_deck_cards(creature_count=20, spell_count=15, land_count=15)

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=10, explain=True)

        for rec in results:
            # Calculate expected total
            expected = (
                rec.tfidf_score * hybrid_recommender.tfidf_weight
                + rec.synergy_score * hybrid_recommender.synergy_weight
                + rec.popularity_score * hybrid_recommender.popularity_weight
                + rec.combo_score * hybrid_recommender.combo_weight
                + rec.limited_score * hybrid_recommender.limited_weight
                + rec.land_score * hybrid_recommender.land_weight
            )

            assert abs(rec.total_score - expected) < 0.001, (
                f"Score mismatch for {rec.name}: expected {expected:.3f}, got {rec.total_score:.3f}"
            )

    def test_combo_score_contributes_to_total(self, hybrid_recommender: HybridRecommender) -> None:
        """Combo completion should boost total score."""
        # Mock combo detector
        mock_combo = Mock()
        mock_combo.find_missing_pieces = Mock(
            return_value=(
                [],
                {"sol ring": ["combo-1"]},  # Sol Ring completes a combo (lowercase)
            )
        )
        mock_combo._combo_meta = {"combo-1": {"type": "value"}}
        mock_combo.get_combo_type_score = Mock(return_value=0.5)
        hybrid_recommender._combo_detector = mock_combo

        deck_cards = create_deck_cards(creature_count=20, spell_count=15, land_count=15)

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=10, explain=True)

        # Find Sol Ring in results
        sol_ring = next((r for r in results if r.name == "Sol Ring"), None)

        if sol_ring:
            assert sol_ring.combo_score > 0, "Sol Ring should have combo_score > 0"
            assert len(sol_ring.completes_combos) > 0, "Sol Ring should list completed combos"


# ============================================================================
# LAND CANDIDATE GENERATION TESTS
# ============================================================================


class TestLandCandidateGeneration:
    """Test _get_land_candidates method."""

    def test_land_candidates_match_color_identity(
        self, hybrid_recommender: HybridRecommender
    ) -> None:
        """Land candidates should match deck's color identity."""
        deck_colors = {"W", "U"}
        exclude = set()

        candidates = hybrid_recommender._get_land_candidates(deck_colors, exclude, max_lands=10)

        for candidate in candidates:
            # Get card data
            card_data = hybrid_recommender._card_data.get(candidate.name)
            assert card_data is not None

            card_identity = set(card_data.get("colorIdentity", []))

            # Should be subset of deck colors
            if card_identity:
                assert card_identity.issubset(deck_colors), (
                    f"{candidate.name} has identity {card_identity}, not subset of {deck_colors}"
                )

    def test_land_candidates_edhrec_scoring(self, hybrid_recommender: HybridRecommender) -> None:
        """Land candidates should be scored by EDHRec rank."""
        deck_colors = {"W", "U", "B"}
        exclude = set()

        candidates = hybrid_recommender._get_land_candidates(deck_colors, exclude, max_lands=10)

        # Command Tower (rank 2) should score higher than basic lands (rank 100)
        command_tower = next((c for c in candidates if c.name == "Command Tower"), None)
        plains = next((c for c in candidates if c.name == "Plains"), None)

        if command_tower and plains:
            assert command_tower.score > plains.score, (
                "Command Tower should score higher than Plains"
            )

    def test_multicolor_land_bonus(self, hybrid_recommender: HybridRecommender) -> None:
        """Multi-color lands matching deck should get bonus."""
        deck_colors = {"W", "U"}
        exclude = set()

        candidates = hybrid_recommender._get_land_candidates(deck_colors, exclude, max_lands=10)

        # Hallowed Fountain (W/U) should get multi-color bonus
        hallowed = next((c for c in candidates if c.name == "Hallowed Fountain"), None)

        if hallowed:
            # Should have received bonus (base score + 0.2 * 1 for 2 matching colors)
            assert hallowed.score > 0.5, (
                f"Hallowed Fountain should get multi-color bonus, got {hallowed.score}"
            )


# ============================================================================
# SYNERGY SCORER TESTS
# ============================================================================


class TestSynergyScorer:
    """Test SynergyScorer functionality."""

    def test_theme_synergy_scoring(self) -> None:
        """Test theme-based synergy scoring."""
        scorer = SynergyScorer()

        # Create candidate with sacrifice theme
        candidate = CardFeatures(
            name="Blood Artist",
            cmc=2.0,
            color_identity={"B"},
            is_creature=True,
            subtypes=["Vampire"],
            synergy_themes={"death_trigger", "aristocrats"},
        )

        # Create deck with sacrifice theme
        deck = DeckFeatures(
            card_count=40,
            color_identity={"B", "R"},
            synergy_themes={"sacrifice": 5, "aristocrats": 3},
        )

        score, reasons = scorer._score_theme_synergy(candidate, deck)

        assert score > 0, "Should have positive synergy score"
        assert any("aristocrats" in r.lower() for r in reasons), (
            "Should mention aristocrats synergy"
        )

    def test_tribal_synergy_scoring(self) -> None:
        """Test tribal synergy detection."""
        scorer = SynergyScorer()

        # Elf candidate
        candidate = CardFeatures(
            name="Llanowar Elves",
            cmc=1.0,
            color_identity={"G"},
            is_creature=True,
            subtypes=["Elf", "Druid"],
        )

        # Elf deck (subtype_counts drives dominant_tribe property)
        deck = DeckFeatures(
            card_count=40,
            color_identity={"G"},
            subtype_counts={"Elf": 15},  # 15 Elves makes it a tribal deck
        )

        score, reason = scorer._score_tribal(candidate, deck)

        assert score == 1.0, "Same tribe should get perfect score"
        assert reason and "elf" in reason.lower(), "Should mention Elf tribe"

    def test_curve_fit_scoring(self) -> None:
        """Test mana curve fit scoring."""
        scorer = SynergyScorer()

        # 3-drop candidate
        candidate = CardFeatures(
            name="Test Card",
            cmc=3.0,
            color_identity={"U"},
            is_creature=True,
        )

        # Deck with gap at 3 CMC
        # cmc_distribution is ratios [0, 1, 2, 3, 4, 5, 6+]
        # Ideal at 3 is 0.20, we have 0.05 -> gap of 0.15
        # Score = gap * 2 = 0.15 * 2 = 0.30
        deck = DeckFeatures(
            card_count=40,
            color_identity={"U"},
            cmc_distribution=[0.05, 0.15, 0.25, 0.05, 0.15, 0.10, 0.10],  # Gap at index 3
        )

        score, reason = scorer._score_curve_fit(candidate, deck)

        # Should boost cards that fill curve gaps (score = gap * 2)
        assert score > 0.2, "Should boost cards that fill curve gaps"
        assert abs(score - 0.3) < 0.01, "Score should be gap * 2 = 0.15 * 2 = 0.3"
        if reason:
            assert "curve gap" in reason.lower() or "3" in reason, "Should mention curve gap"


# ============================================================================
# COMBO PIECE DETECTOR TESTS
# ============================================================================


class TestComboPieceDetector:
    """Test ComboPieceDetector functionality."""

    def test_find_missing_pieces_one_card_away(self) -> None:
        """Test finding combos missing 1 card."""
        detector = ComboPieceDetector()

        # Deck with some combo pieces (depends on KNOWN_COMBOS)
        # This is a basic test - real combo data comes from constants
        deck_cards = ["Exquisite Blood", "Sanguine Bond"]

        matches, _missing_to_combos = detector.find_missing_pieces(deck_cards, max_missing=1)

        # Should find combos that are 1 card away
        for match in matches:
            assert match.missing_count <= 1
            assert match.completion_ratio > 0.5  # At least half complete

    def test_combo_type_scoring(self) -> None:
        """Test combo type score calculation."""
        detector = ComboPieceDetector()

        assert detector.get_combo_type_score("win") == 1.0
        assert detector.get_combo_type_score("infinite") == 0.9
        assert detector.get_combo_type_score("lock") == 0.7
        assert detector.get_combo_type_score("value") == 0.5
        assert detector.get_combo_type_score("unknown") == 0.3


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestRecommendationIntegration:
    """Integration tests for full recommendation flow."""

    def test_recommend_for_deck_basic(self, hybrid_recommender: HybridRecommender) -> None:
        """Test basic deck recommendation flow."""
        deck_cards = create_deck_cards(creature_count=20, spell_count=15, land_count=20)

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=10, explain=True)

        assert len(results) <= 10, "Should return requested number of recommendations"
        assert all(isinstance(r, ScoredRecommendation) for r in results), (
            "All results should be ScoredRecommendation"
        )

        # Results should be sorted by score
        scores = [r.total_score for r in results]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by score"

    def test_color_identity_filtering(self, hybrid_recommender: HybridRecommender) -> None:
        """Test that recommendations respect color identity."""
        # Mono-white deck
        deck_cards = create_deck_cards(
            creature_count=20, spell_count=15, land_count=20, colors=["W"]
        )

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=20, explain=False)

        for rec in results:
            card_data = hybrid_recommender._card_data.get(rec.name)
            if card_data:
                card_identity = set(card_data.get("colorIdentity", []))
                # Card should fit in mono-white
                if card_identity:
                    assert card_identity.issubset({"W"}), (
                        f"{rec.name} has identity {card_identity}, doesn't fit mono-white deck"
                    )

    def test_explanation_reasons_provided(self, hybrid_recommender: HybridRecommender) -> None:
        """Test that explanations are provided when requested."""
        deck_cards = create_deck_cards(creature_count=20, spell_count=15, land_count=10)

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=10, explain=True)

        # At least some results should have reasons
        has_reasons = any(len(r.reasons) > 0 for r in results)
        assert has_reasons, "Should provide explanations when explain=True"

    def test_no_duplicate_deck_cards_in_results(
        self, hybrid_recommender: HybridRecommender
    ) -> None:
        """Test that deck cards are excluded from recommendations."""
        deck_cards = create_deck_cards(creature_count=20, spell_count=15, land_count=20)
        deck_names = {c["name"] for c in deck_cards}

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=20, explain=False)

        for rec in results:
            assert rec.name not in deck_names, f"{rec.name} is already in deck, should be excluded"


# ============================================================================
# EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_deck(self, hybrid_recommender: HybridRecommender) -> None:
        """Test recommendations for empty deck."""
        results = hybrid_recommender.recommend_for_deck([], n=10, explain=False)

        # Should still return results (generic popular cards)
        assert isinstance(results, list)

    def test_very_small_deck(self, hybrid_recommender: HybridRecommender) -> None:
        """Test with very small deck."""
        deck_cards = create_deck_cards(creature_count=2, spell_count=2, land_count=1)

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=5, explain=False)

        assert isinstance(results, list)
        assert len(results) <= 5

    def test_request_more_than_available(self, hybrid_recommender: HybridRecommender) -> None:
        """Test requesting more recommendations than available."""
        deck_cards = create_deck_cards(creature_count=5, spell_count=5, land_count=5)

        # Request 1000 recommendations
        results = hybrid_recommender.recommend_for_deck(deck_cards, n=1000, explain=False)

        # Should return what's available (limited by card pool)
        assert isinstance(results, list)
        # Land cap should still apply: max(1000 // 10, 3) = 100 lands max
        land_count = sum(1 for r in results if r.type_line and "Land" in r.type_line)
        assert land_count <= 100


# ============================================================================
# PROPERTY-BASED TESTS
# ============================================================================


class TestInvariants:
    """Test system invariants that should always hold."""

    def test_land_cap_invariant(self, hybrid_recommender: HybridRecommender) -> None:
        """Land cap formula should always be respected."""
        test_cases = [10, 20, 30, 50, 100, 200]

        for n in test_cases:
            deck_cards = create_deck_cards(creature_count=20, spell_count=20, land_count=0)

            results = hybrid_recommender.recommend_for_deck(deck_cards, n=n, explain=False)

            land_count = sum(1 for r in results if r.type_line and "Land" in r.type_line)
            max_lands = max(n // 10, 3)

            assert land_count <= max_lands, (
                f"Land cap violated for n={n}: {land_count} > {max_lands}"
            )

    def test_scores_are_numeric(self, hybrid_recommender: HybridRecommender) -> None:
        """All score components should be numeric."""
        deck_cards = create_deck_cards(creature_count=20, spell_count=15, land_count=20)

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=20, explain=True)

        for rec in results:
            assert isinstance(rec.total_score, (int, float))
            assert isinstance(rec.tfidf_score, (int, float))
            assert isinstance(rec.synergy_score, (int, float))
            assert isinstance(rec.popularity_score, (int, float))
            assert isinstance(rec.combo_score, (int, float))
            assert isinstance(rec.limited_score, (int, float))
            assert isinstance(rec.land_score, (int, float))

            # Scores should be finite
            assert not any(
                [
                    abs(rec.total_score) == float("inf"),
                    abs(rec.tfidf_score) == float("inf"),
                    abs(rec.synergy_score) == float("inf"),
                ]
            )

    def test_sorted_by_total_score(self, hybrid_recommender: HybridRecommender) -> None:
        """Results should always be sorted by total_score descending."""
        deck_cards = create_deck_cards(creature_count=20, spell_count=15, land_count=20)

        results = hybrid_recommender.recommend_for_deck(deck_cards, n=30, explain=False)

        for i in range(len(results) - 1):
            assert results[i].total_score >= results[i + 1].total_score, (
                f"Results not sorted: position {i} score {results[i].total_score} < "
                f"position {i + 1} score {results[i + 1].total_score}"
            )
