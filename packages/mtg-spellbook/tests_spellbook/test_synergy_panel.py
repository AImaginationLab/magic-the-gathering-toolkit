"""Tests for the Enhanced Synergy Panel widgets.

These tests focus on widget initialization and basic logic that doesn't
require mounting in a Textual App context.
"""

from __future__ import annotations

import pytest

from mtg_core.data.models.responses import SynergyResult
from mtg_spellbook.widgets.synergy import (
    EnhancedSynergyPanel,
    SortOrder,
    SynergyCardItem,
    SynergyListHeader,
    TypeIndex,
)
from mtg_spellbook.widgets.synergy.messages import (
    CategoryChanged,
    SynergyCompareAdd,
    SynergyPanelClosed,
    SynergySelected,
)


@pytest.fixture
def sample_synergy() -> SynergyResult:
    """Create a sample synergy result for testing."""
    return SynergyResult(
        name="Doubling Season",
        mana_cost="{4}{G}",
        type_line="Enchantment",
        synergy_type="ability",
        reason="Doubles +1/+1 counters",
        score=0.85,
    )


@pytest.fixture
def sample_synergies() -> list[SynergyResult]:
    """Create a list of sample synergy results for testing."""
    return [
        SynergyResult(
            name="Panharmonicon",
            mana_cost="{4}",
            type_line="Artifact",
            synergy_type="ability",
            reason="Double ETB triggers",
            score=0.90,
        ),
        SynergyResult(
            name="Elvish Archdruid",
            mana_cost="{1}{G}{G}",
            type_line="Creature - Elf Druid",
            synergy_type="tribal",
            reason="Elf tribal lord",
            score=0.75,
        ),
        SynergyResult(
            name="Flying Men",
            mana_cost="{U}",
            type_line="Creature - Human",
            synergy_type="keyword",
            reason="Flying synergy",
            score=0.60,
        ),
        SynergyResult(
            name="Token Doublers",
            mana_cost="{3}{W}",
            type_line="Enchantment",
            synergy_type="theme",
            reason="Token theme support",
            score=0.70,
        ),
    ]


class TestSynergyCardItem:
    """Tests for SynergyCardItem widget."""

    def test_synergy_stored(self, sample_synergy: SynergyResult) -> None:
        """Test SynergyCardItem stores synergy correctly."""
        item = SynergyCardItem(sample_synergy)
        assert item.synergy == sample_synergy
        assert item.synergy.name == "Doubling Season"

    def test_type_labels_defined(self) -> None:
        """Test TYPE_LABELS dictionary is defined with expected keys."""
        assert "keyword" in SynergyCardItem.TYPE_LABELS
        assert "tribal" in SynergyCardItem.TYPE_LABELS
        assert "ability" in SynergyCardItem.TYPE_LABELS
        assert "theme" in SynergyCardItem.TYPE_LABELS
        assert "combo" in SynergyCardItem.TYPE_LABELS
        assert "archetype" in SynergyCardItem.TYPE_LABELS

    def test_type_labels_values(self) -> None:
        """Test TYPE_LABELS dictionary values are human-readable."""
        assert SynergyCardItem.TYPE_LABELS["keyword"] == "Keyword"
        assert SynergyCardItem.TYPE_LABELS["tribal"] == "Tribal"
        assert SynergyCardItem.TYPE_LABELS["ability"] == "Ability"
        assert SynergyCardItem.TYPE_LABELS["theme"] == "Theme"
        assert SynergyCardItem.TYPE_LABELS["archetype"] == "Theme"  # archetype maps to Theme


class TestSynergyListHeader:
    """Tests for SynergyListHeader widget."""

    def test_initialization(self) -> None:
        """Test SynergyListHeader initializes correctly."""
        header = SynergyListHeader("All", count=25)
        assert header.category == "All"
        assert header.count == 25

    def test_update_count(self) -> None:
        """Test count can be updated."""
        header = SynergyListHeader("Tribal", count=10)
        header.update_count(30)
        assert header.count == 30


class TestTypeIndex:
    """Tests for TypeIndex widget."""

    def test_initialization(self) -> None:
        """Test TypeIndex initializes correctly."""
        index = TypeIndex()
        assert index._active_type == "all"
        assert index._type_counts == {}

    def test_update_counts(self) -> None:
        """Test update_counts updates internal state."""
        index = TypeIndex()
        counts = {"all": 100, "combo": 20, "keyword": 30, "tribal": 25, "ability": 15, "theme": 10}

        index.update_counts(counts, active="tribal")

        assert index._type_counts == counts
        assert index._active_type == "tribal"


class TestSortOrder:
    """Tests for SortOrder enum."""

    def test_sort_order_values(self) -> None:
        """Test SortOrder enum has expected values."""
        assert SortOrder.OWNED_FIRST.value == "owned"
        assert SortOrder.SCORE_DESC.value == "score"
        assert SortOrder.CMC_ASC.value == "cmc"
        assert SortOrder.NAME_ASC.value == "name"

    def test_sort_order_count(self) -> None:
        """Test correct number of sort options."""
        assert len(SortOrder) == 4


class TestEnhancedSynergyPanel:
    """Tests for EnhancedSynergyPanel widget."""

    def test_bindings_defined(self) -> None:
        """Test EnhancedSynergyPanel has required bindings."""
        bindings = EnhancedSynergyPanel.BINDINGS
        assert len(bindings) > 0
        # Check some key bindings exist
        binding_keys = [b.key for b in bindings]
        assert "escape,q" in binding_keys
        assert "enter" in binding_keys
        assert "s" in binding_keys  # Cycle sort
        assert "/" in binding_keys  # Focus search

    def test_default_sort_order(self) -> None:
        """Test default sort order is SCORE_DESC."""
        panel = EnhancedSynergyPanel()
        assert panel.current_sort == SortOrder.SCORE_DESC

    def test_initial_state(self) -> None:
        """Test panel initializes with empty state."""
        panel = EnhancedSynergyPanel()
        assert panel._source_card is None
        assert panel._all_synergies == []
        assert panel._filtered_synergies == []
        assert panel._active_type == "all"


class TestMessages:
    """Tests for synergy panel messages."""

    def test_synergy_selected_message(self, sample_synergy: SynergyResult) -> None:
        """Test SynergySelected message."""
        msg = SynergySelected(sample_synergy)
        assert msg.synergy == sample_synergy

    def test_synergy_compare_add_message(self, sample_synergy: SynergyResult) -> None:
        """Test SynergyCompareAdd message."""
        msg = SynergyCompareAdd(sample_synergy)
        assert msg.synergy == sample_synergy

    def test_category_changed_message(self) -> None:
        """Test CategoryChanged message."""
        msg = CategoryChanged("tribal")
        assert msg.category == "tribal"

    def test_synergy_panel_closed_message(self) -> None:
        """Test SynergyPanelClosed message."""
        msg = SynergyPanelClosed()
        assert msg is not None
