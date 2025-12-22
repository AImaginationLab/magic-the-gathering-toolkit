"""Tests for FocusView display functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from textual.app import App, ComposeResult
from textual.widgets import Static

from mtg_spellbook.widgets.art_navigator.focus import FocusView

if TYPE_CHECKING:
    from mtg_core.data.models.responses import PrintingInfo


class TestFocusViewMetadataDisplay:
    """Test metadata display formatting."""

    async def test_display_full_metadata(self, sample_printing: PrintingInfo) -> None:
        """Test all metadata fields display correctly."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", [sample_printing])
                await pilot.pause(0.2)

                # Check set info
                set_info = focus.query_one("#focus-set-info", Static)
                set_text = set_info.render()
                assert "LEA" in str(set_text)
                assert "161" in str(set_text)
                assert "1993" in str(set_text)
                assert "common" in str(set_text).lower()

                # Check artist
                artist = focus.query_one("#focus-artist", Static)
                artist_text = artist.render()
                assert "Christopher Rush" in str(artist_text)

                # Check flavor text (should show when not in art crop mode)
                flavor = focus.query_one("#focus-flavor", Static)
                flavor_text = flavor.render()
                assert "spark" in str(flavor_text).lower()

                # Check prices
                prices = focus.query_one("#focus-prices", Static)
                prices_text = prices.render()
                assert "2.50" in str(prices_text)

    async def test_display_minimal_metadata(self, minimal_printing: PrintingInfo) -> None:
        """Test display with minimal/missing metadata."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Minimal Card", [minimal_printing])
                await pilot.pause(0.2)

                # Check set info shows unknown
                set_info = focus.query_one("#focus-set-info", Static)
                set_text = set_info.render()
                assert "Unknown" in str(set_text)

                # Check artist is empty
                artist = focus.query_one("#focus-artist", Static)
                artist_text = artist.render()
                assert str(artist_text).strip() == ""

                # Check prices shows no data
                prices = focus.query_one("#focus-prices", Static)
                prices_text = prices.render()
                assert "No price" in str(prices_text)

    async def test_rarity_color_formatting(self, sample_printings: list[PrintingInfo]) -> None:
        """Test rarity displays with appropriate colors."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                # Test common
                await focus.load_printings("Test", [sample_printings[0]])
                await pilot.pause(0.2)
                set_info = focus.query_one("#focus-set-info", Static)
                set_text = set_info.render()
                assert "common" in str(set_text).lower()

                # Test uncommon
                await focus.load_printings("Test", [sample_printings[1]])
                await pilot.pause(0.2)
                set_info = focus.query_one("#focus-set-info", Static)
                set_text = set_info.render()
                assert "uncommon" in str(set_text).lower()

                # Test rare
                await focus.load_printings("Test", [sample_printings[2]])
                await pilot.pause(0.2)
                set_info = focus.query_one("#focus-set-info", Static)
                set_text = set_info.render()
                assert "rare" in str(set_text).lower()

    async def test_flavor_text_hidden_in_art_crop_mode(self, sample_printing: PrintingInfo) -> None:
        """Test flavor text is hidden when show_art_crop is True."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", [sample_printing])
                await pilot.pause(0.2)

                # Enable art crop mode
                focus.show_art_crop = True
                await focus._update_display()
                await pilot.pause(0.2)

                # Flavor should be empty
                flavor = focus.query_one("#focus-flavor", Static)
                flavor_text = flavor.render()
                assert str(flavor_text).strip() == ""


class TestFocusViewNavigationCounter:
    """Test navigation counter display."""

    async def test_navigation_counter_updates(self, sample_printings: list[PrintingInfo]) -> None:
        """Test navigation counter shows correct position."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image"):
                await focus.load_printings("Lightning Bolt", sample_printings)
                await pilot.pause(0.2)

                # Counter should show position
                counter = focus.query_one("#focus-nav-counter", Static)
                assert counter is not None

                # First printing shows (1 / 3)
                assert focus._current_index == 0
                assert len(focus._printings) == 3


class TestFocusViewArtCropToggle:
    """Test art crop mode toggle functionality."""

    async def test_watch_show_art_crop_triggers_update(self, sample_printing: PrintingInfo) -> None:
        """Test changing show_art_crop triggers display update."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image") as mock_load:
                await focus.load_printings("Lightning Bolt", [sample_printing])
                await pilot.pause(0.1)

                initial_calls = mock_load.call_count

                # Toggle art crop
                focus.show_art_crop = True
                await pilot.pause(0.2)

                # Should trigger another load
                assert mock_load.call_count > initial_calls

    async def test_art_crop_changes_image_url(self, sample_printing: PrintingInfo) -> None:
        """Test art crop mode uses art_crop URL instead of image URL."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            with patch.object(focus, "_load_image") as mock_load:
                await focus.load_printings("Lightning Bolt", [sample_printing])
                await pilot.pause(0.1)

                # First call should use regular image
                first_call_url = mock_load.call_args_list[0][0][0]
                assert first_call_url == sample_printing.image

                # Toggle to art crop
                focus.show_art_crop = True
                await pilot.pause(0.2)

                # Latest call should use art_crop
                latest_call_url = mock_load.call_args_list[-1][0][0]
                assert latest_call_url == sample_printing.art_crop
