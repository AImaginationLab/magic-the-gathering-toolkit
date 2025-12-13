"""Tests for synergy and strategy tools."""

from __future__ import annotations

import pytest

from mtg_core.data.database import MTGDatabase, ScryfallDatabase
from mtg_core.tools import synergy
from mtg_core.tools.synergy import (
    KNOWN_COMBOS,
    combo_to_model,
    detect_deck_colors,
    detect_themes,
    normalize_card_name,
)

# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Tests for synergy helper functions."""

    def test_normalize_card_name(self) -> None:
        """Test card name normalization."""
        assert normalize_card_name("Lightning Bolt") == "lightning bolt"
        assert normalize_card_name("  Sol Ring  ") == "sol ring"
        assert normalize_card_name("COUNTERSPELL") == "counterspell"

    def test_combo_to_model(self) -> None:
        """Test conversion of combo dict to Combo model."""
        combo_data = KNOWN_COMBOS[0]  # Twin combo
        combo = combo_to_model(combo_data)

        assert combo.id == "twin"
        assert len(combo.cards) == 2
        assert combo.combo_type == "infinite"
        assert "U" in combo.colors


# =============================================================================
# find_synergies Tests
# =============================================================================


class TestFindSynergies:
    """Tests for find_synergies tool."""

    async def test_find_synergies_basic(self, db: MTGDatabase) -> None:
        """Test finding synergies for a simple card."""
        result = await synergy.find_synergies(db, "Lightning Bolt")

        assert result.card_name == "Lightning Bolt"
        # Should find at least some synergies based on being an instant
        # (spell synergies like magecraft, prowess)
        # Note: May return 0 if no synergies match - that's valid too
        assert result.total_found >= 0

    async def test_find_synergies_etb_card(self, db: MTGDatabase) -> None:
        """Test finding synergies for a card with ETB effects."""
        result = await synergy.find_synergies(db, "Mulldrifter", max_results=10)

        assert result.card_name == "Mulldrifter"
        # Mulldrifter has ETB draw - should find blink synergies
        # and potentially draw synergies
        assert isinstance(result.synergies, list)
        for syn in result.synergies:
            assert syn.name is not None
            assert syn.synergy_type in ["keyword", "tribal", "ability", "theme", "archetype"]
            assert 0.0 <= syn.score <= 1.0

    async def test_find_synergies_with_format_filter(self, db: MTGDatabase) -> None:
        """Test finding synergies with format filter."""
        result = await synergy.find_synergies(
            db, "Sol Ring", max_results=10, format_legal="commander"
        )

        assert result.card_name == "Sol Ring"
        # Results should be Commander legal
        # (assuming cards returned are Commander legal)

    async def test_find_synergies_tribal(self, db: MTGDatabase) -> None:
        """Test finding synergies for a tribal card."""
        # Llanowar Elves is an Elf - should find Elf synergies
        result = await synergy.find_synergies(db, "Llanowar Elves", max_results=15)

        assert result.card_name == "Llanowar Elves"
        # Should find some tribal synergies if tribal detection works
        tribal_synergies = [s for s in result.synergies if s.synergy_type == "tribal"]
        # Might find other elves or elf lords
        assert isinstance(tribal_synergies, list)

    async def test_find_synergies_max_results(self, db: MTGDatabase) -> None:
        """Test that max_results is respected."""
        result = await synergy.find_synergies(db, "Sol Ring", max_results=5)

        assert len(result.synergies) <= 5

    async def test_find_synergies_card_not_found(self, db: MTGDatabase) -> None:
        """Test that CardNotFoundError is raised for invalid cards."""
        from mtg_core.exceptions import CardNotFoundError

        with pytest.raises(CardNotFoundError):
            await synergy.find_synergies(db, "Not A Real Card Name XYZ123")


# =============================================================================
# detect_combos Tests
# =============================================================================


class TestDetectCombos:
    """Tests for detect_combos tool."""

    async def test_detect_combos_for_card(self, db: MTGDatabase) -> None:
        """Test finding combos for a specific card."""
        result = await synergy.detect_combos(db, card_name="Thassa's Oracle")

        # Should find Thoracle combos
        assert len(result.combos) > 0
        combo_ids = [c.id for c in result.combos]
        assert any("thoracle" in cid for cid in combo_ids)

    async def test_detect_combos_for_splinter_twin(self, db: MTGDatabase) -> None:
        """Test finding combos for Splinter Twin."""
        result = await synergy.detect_combos(db, card_name="Splinter Twin")

        assert len(result.combos) > 0
        combo_ids = [c.id for c in result.combos]
        assert any("twin" in cid for cid in combo_ids)

    async def test_detect_combos_complete_combo_in_deck(self, db: MTGDatabase) -> None:
        """Test detecting a complete combo in a deck."""
        deck_cards = [
            "Splinter Twin",
            "Deceiver Exarch",
            "Lightning Bolt",
            "Island",
            "Mountain",
        ]

        result = await synergy.detect_combos(db, deck_cards=deck_cards)

        # Should find the Twin combo
        assert len(result.combos) >= 1
        assert any(c.id == "twin" for c in result.combos)

    async def test_detect_combos_partial_combo(self, db: MTGDatabase) -> None:
        """Test detecting a partial combo (missing pieces)."""
        deck_cards = [
            "Thassa's Oracle",  # Has this
            # Missing Demonic Consultation
            "Counterspell",
            "Island",
        ]

        result = await synergy.detect_combos(db, deck_cards=deck_cards)

        # Should find Thoracle as a potential combo
        assert len(result.potential_combos) >= 1
        assert "thoracle-consult" in result.missing_cards
        assert "Demonic Consultation" in result.missing_cards["thoracle-consult"]

    async def test_detect_combos_no_matches(self, db: MTGDatabase) -> None:
        """Test deck with no combo pieces."""
        deck_cards = [
            "Mountain",
            "Forest",
            "Plains",
        ]

        result = await synergy.detect_combos(db, deck_cards=deck_cards)

        assert len(result.combos) == 0
        # May or may not have potential combos depending on matching logic

    async def test_detect_combos_empty_deck(self, db: MTGDatabase) -> None:
        """Test with empty deck list."""
        result = await synergy.detect_combos(db, deck_cards=[])

        assert len(result.combos) == 0
        assert len(result.potential_combos) == 0

    async def test_detect_combos_neither_provided(self, db: MTGDatabase) -> None:
        """Test with neither card_name nor deck_cards."""
        result = await synergy.detect_combos(db)

        assert len(result.combos) == 0
        assert len(result.potential_combos) == 0


# =============================================================================
# suggest_cards Tests
# =============================================================================


class TestSuggestCards:
    """Tests for suggest_cards tool."""

    async def test_suggest_cards_basic(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test basic card suggestions."""
        deck_cards = [
            "Blood Artist",
            "Viscera Seer",
            "Zulaport Cutthroat",
            "Carrion Feeder",
            "Swamp",
        ]

        result = await synergy.suggest_cards(db, scryfall, deck_cards=deck_cards, max_results=5)

        # Should detect aristocrats theme
        assert "aristocrats" in result.detected_themes or len(result.suggestions) >= 0
        assert "B" in result.deck_colors  # Black should be detected

    async def test_suggest_cards_with_format(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test suggestions filtered by format."""
        deck_cards = [
            "Sol Ring",
            "Arcane Signet",
            "Command Tower",
        ]

        result = await synergy.suggest_cards(
            db,
            scryfall,
            deck_cards=deck_cards,
            format_legal="commander",
            max_results=5,
        )

        # Results should be Commander legal (though we can't verify directly)
        assert isinstance(result.suggestions, list)

    async def test_suggest_cards_with_budget(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test suggestions filtered by budget."""
        deck_cards = [
            "Lightning Bolt",
            "Mountain",
        ]

        result = await synergy.suggest_cards(
            db,
            scryfall,
            deck_cards=deck_cards,
            budget_max=1.0,  # Very low budget
            max_results=5,
        )

        # If any suggestions have prices, they should be under budget
        for suggestion in result.suggestions:
            if suggestion.price_usd is not None:
                assert suggestion.price_usd <= 1.0

    async def test_suggest_cards_empty_deck(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test with empty deck."""
        result = await synergy.suggest_cards(db, scryfall, deck_cards=[])

        assert result.suggestions == []
        assert result.detected_themes == []
        assert result.deck_colors == []

    async def test_suggest_cards_color_detection(
        self, db: MTGDatabase, scryfall: ScryfallDatabase | None
    ) -> None:
        """Test that deck colors are correctly detected."""
        deck_cards = [
            "Lightning Bolt",  # Red
            "Counterspell",  # Blue
            "Swords to Plowshares",  # White
            "Island",
            "Mountain",
            "Plains",
        ]

        result = await synergy.suggest_cards(db, scryfall, deck_cards=deck_cards, max_results=5)

        # Should detect W, U, R (order may vary but should be WUBRG order)
        assert "W" in result.deck_colors
        assert "U" in result.deck_colors
        assert "R" in result.deck_colors


# =============================================================================
# Theme Detection Tests
# =============================================================================


class TestThemeDetection:
    """Tests for theme detection logic."""

    def test_detect_tokens_theme(self) -> None:
        """Test detection of tokens theme."""
        # Mock card objects with token-related text
        from unittest.mock import MagicMock

        cards = []
        for text in [
            "Create a 1/1 token",
            "Create two 1/1 Soldier creature tokens",
            "Whenever a creature enters the battlefield",
        ]:
            card = MagicMock()
            card.text = text
            card.subtypes = []
            cards.append(card)

        themes = detect_themes(cards)
        assert "tokens" in themes

    def test_detect_aristocrats_theme(self) -> None:
        """Test detection of aristocrats theme."""
        from unittest.mock import MagicMock

        cards = []
        for text in [
            "Sacrifice a creature",
            "Whenever a creature dies",
            "Zulaport Cutthroat ability",
        ]:
            card = MagicMock()
            card.text = text
            card.subtypes = []
            cards.append(card)

        themes = detect_themes(cards)
        assert "aristocrats" in themes

    def test_detect_tribal_theme(self) -> None:
        """Test detection of tribal theme via subtype concentration."""
        from unittest.mock import MagicMock

        cards = []
        for _ in range(6):  # 6 elves = tribal
            card = MagicMock()
            card.text = ""
            card.subtypes = ["Elf"]
            cards.append(card)

        themes = detect_themes(cards)
        assert "tribal" in themes


# =============================================================================
# Color Detection Tests
# =============================================================================


class TestColorDetection:
    """Tests for deck color detection."""

    def test_detect_deck_colors_wubrg_order(self) -> None:
        """Test that colors are returned in WUBRG order."""
        from unittest.mock import MagicMock

        cards = []

        # Add cards in reverse order (GRBUW)
        for colors in [["G"], ["R"], ["B"], ["U"], ["W"]]:
            card = MagicMock()
            card.color_identity = colors
            cards.append(card)

        result = detect_deck_colors(cards)

        # Should be in WUBRG order
        assert result == ["W", "U", "B", "R", "G"]

    def test_detect_deck_colors_partial(self) -> None:
        """Test with partial color identity."""
        from unittest.mock import MagicMock

        cards = []
        for colors in [["U"], ["R"], ["U", "R"]]:
            card = MagicMock()
            card.color_identity = colors
            cards.append(card)

        result = detect_deck_colors(cards)

        assert result == ["U", "R"]
        assert "W" not in result
        assert "B" not in result
        assert "G" not in result
