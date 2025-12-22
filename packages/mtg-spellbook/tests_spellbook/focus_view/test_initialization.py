"""Tests for FocusView initialization and composition."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Static

from mtg_spellbook.widgets.art_navigator import HAS_IMAGE_SUPPORT
from mtg_spellbook.widgets.art_navigator.focus import FocusView


class TestFocusViewInitialization:
    """Test FocusView initialization and composition."""

    async def test_initialization_with_card_name(self) -> None:
        """Test FocusView initializes with card name."""
        focus = FocusView("Lightning Bolt")

        assert focus._card_name == "Lightning Bolt"
        assert focus._printings == []
        assert focus._current_index == 0
        assert focus.show_art_crop is False

    async def test_composition_creates_all_widgets(self) -> None:
        """Test compose creates all required widgets."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test Card", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            # Check metadata widgets exist
            assert focus.query_one("#focus-card-name", Static)
            assert focus.query_one("#focus-set-info", Static)
            assert focus.query_one("#focus-artist", Static)
            assert focus.query_one("#focus-flavor", Static)
            assert focus.query_one("#focus-prices", Static)

            # Check navigation counter widget exists
            assert focus.query_one("#focus-nav-counter", Static)

    async def test_composition_with_image_support(self) -> None:
        """Test composition includes image widget when support available."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test Card", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            if HAS_IMAGE_SUPPORT:
                # Should have image widget
                from mtg_spellbook.widgets.art_navigator import TImage

                assert focus.query_one("#focus-image", TImage)
            else:
                # Should have placeholder text
                placeholder = focus.query_one(".focus-no-image", Static)
                placeholder_text = placeholder.render()
                assert "not available" in str(placeholder_text).lower()
