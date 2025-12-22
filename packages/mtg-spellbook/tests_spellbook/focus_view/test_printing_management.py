"""Tests for FocusView printing loading and retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from textual.app import App, ComposeResult
from textual.widgets import Static

from mtg_spellbook.widgets.art_navigator.focus import FocusView

if TYPE_CHECKING:
    from mtg_core.data.models.responses import PrintingInfo


class TestFocusViewPrintingLoading:
    """Test loading printings into FocusView."""

    async def test_load_printings_updates_state(self, sample_printings: list[PrintingInfo]) -> None:
        """Test load_printings updates internal state."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Old Name", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)

                assert focus._card_name == "Lightning Bolt"
                assert focus._printings == sample_printings
                assert focus._current_index == 0

    async def test_load_printings_updates_display(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test load_printings updates visible elements."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)
                await pilot.pause(0.2)

                # Check card name updated
                name_widget = focus.query_one("#focus-card-name", Static)
                name_text = name_widget.render()
                assert "Lightning Bolt" in str(name_text)

                # Check counter shows correct pagination
                counter = focus.query_one("#focus-nav-counter", Static)
                counter_text = counter.render()
                assert "1" in str(counter_text) and "3" in str(counter_text)

                # Check set info displays
                set_info = focus.query_one("#focus-set-info", Static)
                set_text = set_info.render()
                assert "LEA" in str(set_text).upper()

    async def test_load_empty_printings(self) -> None:
        """Test loading empty printings list."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Empty Card", [])

                assert focus._card_name == "Empty Card"
                assert focus._printings == []
                assert focus._current_index == 0


class TestFocusViewGetCurrentPrinting:
    """Test get_current_printing method."""

    async def test_get_current_printing_returns_correct_printing(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test get_current_printing returns the current printing."""
        assert len(sample_printings) > 0, "Test requires non-empty sample_printings fixture"

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)

                current = focus.get_current_printing()
                assert current == sample_printings[0]
                assert current.set_code == "lea"

    async def test_get_current_printing_after_navigation(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test get_current_printing after navigating."""
        assert len(sample_printings) >= 2, "Test requires at least 2 elements in sample_printings"

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)
                await focus.navigate("next")

                current = focus.get_current_printing()
                assert current == sample_printings[1]
                assert current.set_code == "m10"

    async def test_get_current_printing_with_no_printings(self) -> None:
        """Test get_current_printing returns None when no printings loaded."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            current = focus.get_current_printing()
            assert current is None
