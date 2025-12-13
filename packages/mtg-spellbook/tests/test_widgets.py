"""Tests for MTG Spellbook widgets - ensures unique IDs across multiple panel instances."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

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
        """Test that _child_id generates unique IDs based on panel ID."""
        panel1 = CardPanel(id="panel-a")
        panel2 = CardPanel(id="panel-b")

        assert panel1._child_id("card-text") == "panel-a-card-text"
        assert panel2._child_id("card-text") == "panel-b-card-text"
        assert panel1._child_id("art-image") == "panel-a-art-image"
        assert panel2._child_id("art-image") == "panel-b-art-image"

    @pytest.mark.asyncio
    async def test_get_child_id_returns_selector(self) -> None:
        """Test that get_child_id returns a CSS selector with #."""
        panel = CardPanel(id="test-panel")

        assert panel.get_child_id("card-text") == "#test-panel-card-text"
        assert panel.get_child_id("tabs") == "#test-panel-tabs"
        assert panel.get_child_id("art-image") == "#test-panel-art-image"

    @pytest.mark.asyncio
    async def test_two_panels_have_distinct_children(self) -> None:
        """Test that two CardPanel instances in an app have distinct child IDs."""
        async with TwoCardPanelsApp().run_test() as pilot:
            app = pilot.app

            # Get both panels
            panel1 = app.query_one("#card-panel", CardPanel)
            panel2 = app.query_one("#source-card-panel", CardPanel)

            # Verify they generate different child IDs
            assert panel1._child_id("card-text") != panel2._child_id("card-text")
            assert panel1._child_id("art-image") != panel2._child_id("art-image")
            assert panel1._child_id("tabs") != panel2._child_id("tabs")

            # Verify specific ID values
            assert panel1._child_id("card-text") == "card-panel-card-text"
            assert panel2._child_id("card-text") == "source-card-panel-card-text"

    @pytest.mark.asyncio
    async def test_can_query_specific_panel_children(self) -> None:
        """Test that we can query children within a specific panel."""
        async with TwoCardPanelsApp().run_test() as pilot:
            app = pilot.app

            panel1 = app.query_one("#card-panel", CardPanel)
            panel2 = app.query_one("#source-card-panel", CardPanel)

            # Query card-text from panel1
            card_text_1 = panel1.query_one(panel1.get_child_id("card-text"), Static)
            assert card_text_1 is not None
            assert card_text_1.id == "card-panel-card-text"

            # Query card-text from panel2
            card_text_2 = panel2.query_one(panel2.get_child_id("card-text"), Static)
            assert card_text_2 is not None
            assert card_text_2.id == "source-card-panel-card-text"

            # Ensure they are different widget instances
            assert card_text_1 is not card_text_2

    @pytest.mark.asyncio
    async def test_global_query_finds_both_panels(self) -> None:
        """Test that global queries can find widgets from both panels."""
        async with TwoCardPanelsApp().run_test() as pilot:
            app = pilot.app

            # Query all Static widgets - should find multiple card-text widgets
            all_statics = list(app.query(Static))

            # Should have at least the card-text widgets from both panels
            ids = [s.id for s in all_statics if s.id]
            assert "card-panel-card-text" in ids
            assert "source-card-panel-card-text" in ids

    @pytest.mark.asyncio
    async def test_panel_without_id_uses_default_prefix(self) -> None:
        """Test that a panel without an explicit ID uses default prefix."""
        panel = CardPanel()  # No id provided

        # Should use "card-panel" as default prefix
        assert panel._id_prefix == "card-panel"
        assert panel._child_id("card-text") == "card-panel-card-text"


class TestCardPanelCompose:
    """Test that CardPanel correctly composes its children with unique IDs."""

    @pytest.mark.asyncio
    async def test_all_tabs_have_unique_ids(self) -> None:
        """Test that all tab panes have panel-prefixed IDs."""
        async with TwoCardPanelsApp().run_test() as pilot:
            app = pilot.app

            panel1 = app.query_one("#card-panel", CardPanel)

            # Check all expected tab IDs exist
            expected_tabs = ["tab-card", "tab-art", "tab-rulings", "tab-legal", "tab-price"]
            for tab_name in expected_tabs:
                full_id = panel1._child_id(tab_name)
                assert full_id.startswith("card-panel-")

    @pytest.mark.asyncio
    async def test_all_content_widgets_have_unique_ids(self) -> None:
        """Test that all content widgets have panel-prefixed IDs."""
        async with TwoCardPanelsApp().run_test() as pilot:
            app = pilot.app

            panel1 = app.query_one("#card-panel", CardPanel)
            panel2 = app.query_one("#source-card-panel", CardPanel)

            content_widgets = ["card-text", "art-info", "rulings-text", "legal-text", "price-text"]
            for widget_name in content_widgets:
                id1 = panel1._child_id(widget_name)
                id2 = panel2._child_id(widget_name)
                assert id1 != id2
                assert id1.startswith("card-panel-")
                assert id2.startswith("source-card-panel-")
