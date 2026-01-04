"""Tests for SpellbookComboDetector and combo info retrieval."""

from __future__ import annotations

from pathlib import Path

import pytest

from mtg_core.tools.recommendations.spellbook_combos import (
    SpellbookCombo,
    SpellbookComboDetector,
    SpellbookComboMatch,
    get_spellbook_detector,
)
from mtg_core.tools.synergy.tools import _get_combo_info


class TestSpellbookComboDetector:
    """Tests for SpellbookComboDetector class."""

    def test_is_available_no_db(self) -> None:
        """Test is_available returns False when no database exists."""
        detector = SpellbookComboDetector(db_path=Path("/nonexistent/path.sqlite"))
        assert detector.is_available is False

    def test_is_available_with_db(self, tmp_path: Path) -> None:
        """Test is_available returns True when database exists."""
        db_file = tmp_path / "combos.sqlite"
        db_file.touch()
        detector = SpellbookComboDetector(db_path=db_file)
        assert detector.is_available is True

    @pytest.mark.asyncio
    async def test_initialize_no_db(self) -> None:
        """Test initialize returns False when database not available."""
        detector = SpellbookComboDetector(db_path=Path("/nonexistent/path.sqlite"))
        result = await detector.initialize()
        assert result is False

    def test_combo_count_before_init(self) -> None:
        """Test combo_count is 0 before initialization."""
        detector = SpellbookComboDetector(db_path=Path("/nonexistent/path.sqlite"))
        assert detector.combo_count == 0

    @pytest.mark.asyncio
    async def test_find_combos_for_card_not_initialized(self) -> None:
        """Test find_combos_for_card returns empty when not initialized."""
        detector = SpellbookComboDetector(db_path=Path("/nonexistent/path.sqlite"))
        combos = await detector.find_combos_for_card("Test Card")
        assert combos == []


class TestSpellbookComboDetectorWithRealDB:
    """Tests that use the real Commander Spellbook database if available."""

    @pytest.fixture
    async def detector(self) -> SpellbookComboDetector | None:
        """Get detector with real database, or None if not available."""
        detector = SpellbookComboDetector()
        if detector.is_available:
            await detector.initialize()
            return detector
        return None

    @pytest.mark.asyncio
    async def test_find_combos_for_thassas_oracle(
        self, detector: SpellbookComboDetector | None
    ) -> None:
        """Test finding combos for Thassa's Oracle (famous combo piece)."""
        if detector is None:
            pytest.skip("Commander Spellbook database not available")

        combos = await detector.find_combos_for_card("Thassa's Oracle")
        assert len(combos) > 0
        # Thassa's Oracle is a famous combo piece, should have many combos
        assert len(combos) >= 5

        # Verify combo structure
        combo = combos[0]
        assert isinstance(combo, SpellbookCombo)
        assert combo.id
        assert combo.card_names
        assert "Thassa's Oracle" in combo.card_names

    @pytest.mark.asyncio
    async def test_find_combos_for_demonic_consultation(
        self, detector: SpellbookComboDetector | None
    ) -> None:
        """Test finding combos for Demonic Consultation."""
        if detector is None:
            pytest.skip("Commander Spellbook database not available")

        combos = await detector.find_combos_for_card("Demonic Consultation")
        assert len(combos) > 0

    @pytest.mark.asyncio
    async def test_find_combos_for_nonexistent_card(
        self, detector: SpellbookComboDetector | None
    ) -> None:
        """Test finding combos for a card that doesn't exist in combos."""
        if detector is None:
            pytest.skip("Commander Spellbook database not available")

        combos = await detector.find_combos_for_card("Basic Island That Does Nothing Special")
        assert combos == []

    @pytest.mark.asyncio
    async def test_find_missing_pieces(self, detector: SpellbookComboDetector | None) -> None:
        """Test finding missing combo pieces for a deck."""
        if detector is None:
            pytest.skip("Commander Spellbook database not available")

        # Deck with Thassa's Oracle but missing Demonic Consultation
        deck_cards = ["Thassa's Oracle", "Island", "Swamp"]
        matches, missing_map = await detector.find_missing_pieces(deck_cards, max_missing=1)

        # Should find combos that need 1 more card
        assert len(matches) > 0
        # Demonic Consultation should be in missing cards
        missing_cards_lower = {k.lower() for k in missing_map}
        assert "demonic consultation" in missing_cards_lower

    @pytest.mark.asyncio
    async def test_combo_score(self, detector: SpellbookComboDetector | None) -> None:
        """Test combo scoring function."""
        if detector is None:
            pytest.skip("Commander Spellbook database not available")

        combos = await detector.find_combos_for_card("Thassa's Oracle", limit=5)
        if combos:
            score = detector.get_combo_score(combos[0])
            assert 0 <= score <= 100


class TestGetComboInfo:
    """Tests for _get_combo_info function."""

    @pytest.mark.asyncio
    async def test_get_combo_info_with_none(self) -> None:
        """Test _get_combo_info returns (0, None) with None input."""
        count, preview = await _get_combo_info(None, "Test Card")
        assert count == 0
        assert preview is None

    @pytest.mark.asyncio
    async def test_get_combo_info_with_wrong_type(self) -> None:
        """Test _get_combo_info returns (0, None) with wrong type."""
        count, preview = await _get_combo_info("not a detector", "Test Card")
        assert count == 0
        assert preview is None

    @pytest.mark.asyncio
    async def test_get_combo_info_with_real_detector(self) -> None:
        """Test _get_combo_info with real detector instance."""
        detector = SpellbookComboDetector()

        if not detector.is_available:
            pytest.skip("Commander Spellbook database not available")

        await detector.initialize()

        # Test with a known combo card
        count, preview = await _get_combo_info(detector, "Thassa's Oracle")

        # Thassa's Oracle is a famous combo piece
        assert count > 0
        assert preview is not None
        assert isinstance(preview, str)

    @pytest.mark.asyncio
    async def test_get_combo_info_truncates_long_description(self) -> None:
        """Test that long descriptions are truncated."""
        # Create a real detector instance for isinstance to pass
        detector = SpellbookComboDetector()

        # If not available, skip
        if not detector.is_available:
            pytest.skip("Commander Spellbook database not available")

        await detector.initialize()

        # Find a card with combos
        _count, preview = await _get_combo_info(detector, "Thassa's Oracle")

        if preview:
            # Preview should be max 200 chars
            assert len(preview) <= 200


class TestGetSpellbookDetector:
    """Tests for get_spellbook_detector singleton function."""

    @pytest.mark.asyncio
    async def test_returns_detector_instance(self) -> None:
        """Test that get_spellbook_detector returns a SpellbookComboDetector."""
        detector = await get_spellbook_detector()
        assert isinstance(detector, SpellbookComboDetector)

    @pytest.mark.asyncio
    async def test_returns_same_instance(self) -> None:
        """Test that get_spellbook_detector returns the same instance."""
        detector1 = await get_spellbook_detector()
        detector2 = await get_spellbook_detector()
        assert detector1 is detector2


class TestSpellbookComboMatch:
    """Tests for SpellbookComboMatch dataclass."""

    def test_missing_count(self) -> None:
        """Test missing_count property."""
        combo = SpellbookCombo(
            id="test",
            card_names=["A", "B", "C"],
            description="Test",
            bracket_tag="C",
            popularity=100,
            identity="U",
            produces=[],
        )
        match = SpellbookComboMatch(
            combo=combo,
            present_cards=["A"],
            missing_cards=["B", "C"],
            completion_ratio=0.33,
        )
        assert match.missing_count == 2

    def test_is_complete_true(self) -> None:
        """Test is_complete returns True when no missing cards."""
        combo = SpellbookCombo(
            id="test",
            card_names=["A", "B"],
            description="Test",
            bracket_tag="C",
            popularity=100,
            identity="U",
            produces=[],
        )
        match = SpellbookComboMatch(
            combo=combo,
            present_cards=["A", "B"],
            missing_cards=[],
            completion_ratio=1.0,
        )
        assert match.is_complete is True

    def test_is_complete_false(self) -> None:
        """Test is_complete returns False when cards are missing."""
        combo = SpellbookCombo(
            id="test",
            card_names=["A", "B"],
            description="Test",
            bracket_tag="C",
            popularity=100,
            identity="U",
            produces=[],
        )
        match = SpellbookComboMatch(
            combo=combo,
            present_cards=["A"],
            missing_cards=["B"],
            completion_ratio=0.5,
        )
        assert match.is_complete is False
