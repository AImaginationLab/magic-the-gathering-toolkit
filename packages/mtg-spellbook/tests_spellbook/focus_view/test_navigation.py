"""Tests for FocusView navigation functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from textual.app import App, ComposeResult
from textual.widgets import Static

from mtg_spellbook.widgets.art_navigator.focus import FocusView

if TYPE_CHECKING:
    from mtg_core.data.models.responses import PrintingInfo


class TestFocusViewNavigation:
    """Test navigation between printings."""

    async def test_navigate_next_increments_index(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test navigate('next') increments index."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)
                await pilot.pause(0.2)

                # Navigate to next
                await focus.navigate("next")
                await pilot.pause(0.2)

                assert focus._current_index == 1

                # Verify display updated
                counter = focus.query_one("#focus-nav-counter", Static)
                counter_text = counter.render()
                assert "2" in str(counter_text) and "3" in str(counter_text)

    async def test_navigate_prev_decrements_index(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test navigate('prev') decrements index."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)
                focus._current_index = 2
                await focus._update_display()
                await pilot.pause(0.1)

                # Navigate to previous
                await focus.navigate("prev")
                await pilot.pause(0.1)

                assert focus._current_index == 1

    async def test_navigate_next_at_end_stays_at_last(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test navigating next at last printing stays at last index."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)
                focus._current_index = 2  # Last printing
                await focus._update_display()

                # Navigate next at end
                await focus.navigate("next")
                await pilot.pause(0.1)

                # Should stay at same index
                assert focus._current_index == 2

    async def test_navigate_prev_at_start_stays_at_first(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test navigating prev at first printing stays at first index."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)
                await pilot.pause(0.1)

                # Navigate prev at start (index 0)
                await focus.navigate("prev")
                await pilot.pause(0.1)

                # Should stay at index 0
                assert focus._current_index == 0

    async def test_navigate_with_no_printings(self) -> None:
        """Test navigation does nothing when no printings loaded."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            # Try to navigate with no printings
            await focus.navigate("next")
            await focus.navigate("prev")

            # Should remain at 0
            assert focus._current_index == 0


class TestFocusViewSyncToIndex:
    """Test sync_to_index functionality."""

    async def test_sync_to_valid_index(self, sample_printings: list[PrintingInfo]) -> None:
        """Test sync_to_index jumps to specific printing."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)
                await pilot.pause(0.2)

                # Sync to index 2
                await focus.sync_to_index(2)
                await pilot.pause(0.2)

                assert focus._current_index == 2

                # Verify display updated
                counter = focus.query_one("#focus-nav-counter", Static)
                counter_text = counter.render()
                assert "3" in str(counter_text)

    async def test_sync_to_index_zero(self, sample_printings: list[PrintingInfo]) -> None:
        """Test sync_to_index works with index 0."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)
                focus._current_index = 2
                await focus._update_display()

                # Sync back to first
                await focus.sync_to_index(0)
                await pilot.pause(0.1)

                assert focus._current_index == 0

    async def test_sync_to_invalid_index_negative(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test sync_to_index ignores negative index."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)
                await pilot.pause(0.1)

                original_index = focus._current_index

                # Try negative index
                await focus.sync_to_index(-1)

                # Should not change
                assert focus._current_index == original_index

    async def test_sync_to_invalid_index_too_large(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test sync_to_index ignores out-of-bounds index."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)
                await pilot.pause(0.1)

                original_index = focus._current_index

                # Try index beyond range
                await focus.sync_to_index(999)

                # Should not change
                assert focus._current_index == original_index
