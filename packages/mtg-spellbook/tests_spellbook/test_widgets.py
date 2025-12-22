"""Tests for MTG Spellbook widgets - ensures unique IDs across multiple panel instances."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.containers import Horizontal

from mtg_spellbook.widgets import CardPanel


class TwoCardPanelsApp(App[None]):
    """Test app with two CardPanel instances (simulates synergy mode)."""

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield CardPanel(id="card-panel")
            yield CardPanel(id="source-card-panel")


class TestCardPanelUniqueIds:
    """Test that multiple CardPanel instances have unique child widget IDs."""

    @pytest.mark.asyncio
    async def test_child_id_generation(self) -> None:
        """Test that _child_id generates unique IDs based on panel ID (internal format)."""
        panel1 = CardPanel(id="panel-a")
        panel2 = CardPanel(id="panel-b")

        # Test internal _child_id format (no # prefix)
        assert panel1._child_id("art-navigator") == "panel-a-art-navigator"
        assert panel2._child_id("art-navigator") == "panel-b-art-navigator"
        assert panel1._child_id("focus") == "panel-a-focus"
        assert panel2._child_id("focus") == "panel-b-focus"

    @pytest.mark.asyncio
    async def test_get_child_name_returns_id_without_selector(self) -> None:
        """Test that get_child_name returns the ID without # selector."""
        panel = CardPanel(id="test-panel")

        assert panel.get_child_name("art-navigator") == "test-panel-art-navigator"
        assert panel.get_child_name("focus") == "test-panel-focus"
        assert panel.get_child_name("grid") == "test-panel-grid"

    @pytest.mark.asyncio
    async def test_get_child_id_returns_selector(self) -> None:
        """Test that get_child_id returns a CSS selector with #."""
        panel = CardPanel(id="test-panel")

        assert panel.get_child_id("art-navigator") == "#test-panel-art-navigator"
        assert panel.get_child_id("focus") == "#test-panel-focus"
        assert panel.get_child_id("grid") == "#test-panel-grid"

    @pytest.mark.asyncio
    async def test_two_panels_have_distinct_children(self) -> None:
        """Test that two CardPanel instances in an app have distinct child IDs."""
        async with TwoCardPanelsApp().run_test() as pilot:
            app = pilot.app

            # Get both panels
            panel1 = app.query_one("#card-panel", CardPanel)
            panel2 = app.query_one("#source-card-panel", CardPanel)

            # Verify they generate different child IDs (using public API)
            assert panel1.get_child_name("art-navigator") != panel2.get_child_name("art-navigator")
            assert panel1.get_child_name("focus") != panel2.get_child_name("focus")
            assert panel1.get_child_name("grid") != panel2.get_child_name("grid")

            # Verify specific ID values (using public API)
            assert panel1.get_child_name("art-navigator") == "card-panel-art-navigator"
            assert panel2.get_child_name("art-navigator") == "source-card-panel-art-navigator"

    @pytest.mark.asyncio
    async def test_can_query_specific_panel_children(self) -> None:
        """Test that we can query children within a specific panel."""
        from mtg_spellbook.widgets.art_navigator import EnhancedArtNavigator

        async with TwoCardPanelsApp().run_test() as pilot:
            app = pilot.app

            panel1 = app.query_one("#card-panel", CardPanel)
            panel2 = app.query_one("#source-card-panel", CardPanel)

            # Query art-navigator from panel1
            art_nav_1 = panel1.query_one(panel1.get_child_id("art-navigator"), EnhancedArtNavigator)
            assert art_nav_1 is not None
            assert art_nav_1.id == "card-panel-art-navigator"

            # Query art-navigator from panel2
            art_nav_2 = panel2.query_one(panel2.get_child_id("art-navigator"), EnhancedArtNavigator)
            assert art_nav_2 is not None
            assert art_nav_2.id == "source-card-panel-art-navigator"

            # Ensure they are different widget instances
            assert art_nav_1 is not art_nav_2

    @pytest.mark.asyncio
    async def test_global_query_finds_both_panels(self) -> None:
        """Test that global queries can find widgets from both panels."""
        from mtg_spellbook.widgets.art_navigator import EnhancedArtNavigator

        async with TwoCardPanelsApp().run_test() as pilot:
            app = pilot.app

            # Query all EnhancedArtNavigator widgets - should find from both panels
            all_navs = list(app.query(EnhancedArtNavigator))

            # Should have art navigators from both panels
            ids = [n.id for n in all_navs if n.id]
            assert "card-panel-art-navigator" in ids
            assert "source-card-panel-art-navigator" in ids

    @pytest.mark.asyncio
    async def test_panel_without_id_uses_default_prefix(self) -> None:
        """Test that a panel without an explicit ID uses default prefix."""
        panel = CardPanel()  # No id provided

        # Should use "card-panel" as default prefix
        assert panel._id_prefix == "card-panel"
        assert panel.get_child_name("art-navigator") == "card-panel-art-navigator"


class TestCardPanelCompose:
    """Test that CardPanel correctly composes its children with unique IDs."""

    @pytest.mark.asyncio
    async def test_art_navigator_has_unique_id(self) -> None:
        """Test that art navigator has panel-prefixed ID."""
        async with TwoCardPanelsApp().run_test() as pilot:
            app = pilot.app

            panel1 = app.query_one("#card-panel", CardPanel)

            # Check art navigator ID exists (using public API)
            nav_id = panel1.get_child_name("art-navigator")
            assert nav_id.startswith("card-panel-")
            assert nav_id == "card-panel-art-navigator"

    @pytest.mark.asyncio
    async def test_all_content_widgets_have_unique_ids(self) -> None:
        """Test that all content widgets have panel-prefixed IDs."""
        async with TwoCardPanelsApp().run_test() as pilot:
            app = pilot.app

            panel1 = app.query_one("#card-panel", CardPanel)
            panel2 = app.query_one("#source-card-panel", CardPanel)

            # Art navigator components have prefixed IDs
            content_widgets = ["art-navigator", "focus", "grid", "preview"]
            for widget_name in content_widgets:
                id1 = panel1.get_child_name(widget_name)
                id2 = panel2.get_child_name(widget_name)
                assert id1 != id2
                assert id1.startswith("card-panel-")
                assert id2.startswith("source-card-panel-")
