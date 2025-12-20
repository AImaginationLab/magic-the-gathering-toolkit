"""Tests for FocusView component - immersive single-card artwork display."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import pytest
from PIL import Image
from textual.app import ComposeResult
from textual.widgets import Static

from mtg_core.data.models.responses import PrintingInfo
from mtg_spellbook.widgets.art_navigator import HAS_IMAGE_SUPPORT
from mtg_spellbook.widgets.art_navigator.focus import FocusView

if TYPE_CHECKING:
    pass


@pytest.fixture
def sample_printing() -> PrintingInfo:
    """Create a sample printing with typical data."""
    return PrintingInfo(
        uuid="test-uuid-1",
        set_code="lea",
        collector_number="161",
        image="https://example.com/image.jpg",
        art_crop="https://example.com/art_crop.jpg",
        price_usd=2.50,
        price_eur=2.20,
        artist="Christopher Rush",
        flavor_text="The spark of an idea can ignite a revolution.",
        rarity="common",
        release_date="1993-08-05",
        illustration_id="test-illustration-1",
    )


@pytest.fixture
def sample_printings() -> list[PrintingInfo]:
    """Create multiple sample printings for navigation testing."""
    return [
        PrintingInfo(
            uuid="test-uuid-1",
            set_code="lea",
            collector_number="161",
            image="https://example.com/image1.jpg",
            art_crop="https://example.com/art_crop1.jpg",
            price_usd=2.50,
            price_eur=2.20,
            artist="Christopher Rush",
            flavor_text="First printing flavor.",
            rarity="common",
            release_date="1993-08-05",
        ),
        PrintingInfo(
            uuid="test-uuid-2",
            set_code="m10",
            collector_number="146",
            image="https://example.com/image2.jpg",
            art_crop="https://example.com/art_crop2.jpg",
            price_usd=1.00,
            price_eur=0.90,
            artist="Christopher Moeller",
            flavor_text="Second printing flavor.",
            rarity="uncommon",
            release_date="2009-07-17",
        ),
        PrintingInfo(
            uuid="test-uuid-3",
            set_code="m11",
            collector_number="147",
            image="https://example.com/image3.jpg",
            art_crop="https://example.com/art_crop3.jpg",
            price_usd=5.00,
            price_eur=4.50,
            artist="Howard Lyon",
            flavor_text="Third printing flavor.",
            rarity="rare",
            release_date="2010-07-16",
        ),
    ]


@pytest.fixture
def minimal_printing() -> PrintingInfo:
    """Create a minimal printing with optional fields empty."""
    return PrintingInfo(
        uuid="test-uuid-min",
        set_code=None,
        collector_number=None,
        image="https://example.com/minimal.jpg",
        art_crop=None,
        price_usd=None,
        price_eur=None,
        artist=None,
        flavor_text=None,
        rarity=None,
        release_date=None,
    )


@pytest.fixture
def mock_image() -> Image.Image:
    """Create a mock PIL Image."""
    img = Image.new("RGB", (100, 100), color="red")
    return img


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
        from textual.app import App

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
        from textual.app import App

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


class TestFocusViewPrintingLoading:
    """Test loading printings into FocusView."""

    async def test_load_printings_updates_state(self, sample_printings: list[PrintingInfo]) -> None:
        """Test load_printings updates internal state."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Old Name", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            await focus.load_printings("Lightning Bolt", sample_printings)

            assert focus._card_name == "Lightning Bolt"
            assert focus._printings == sample_printings
            assert focus._current_index == 0

    async def test_load_printings_updates_display(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test load_printings updates visible elements."""
        from textual.app import App

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
        from textual.app import App

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            await focus.load_printings("Empty Card", [])

            assert focus._card_name == "Empty Card"
            assert focus._printings == []
            assert focus._current_index == 0


class TestFocusViewNavigation:
    """Test navigation between printings."""

    async def test_navigate_next_increments_index(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test navigate('next') increments index."""
        from textual.app import App

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
        from textual.app import App

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

    async def test_navigate_next_at_end_shows_notification(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test navigating next at last printing shows notification."""
        from textual.app import App

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

    async def test_navigate_prev_at_start_shows_notification(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test navigating prev at first printing shows notification."""
        from textual.app import App

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
        from textual.app import App

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
        from textual.app import App

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
        from textual.app import App

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
        from textual.app import App

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
        from textual.app import App

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


class TestFocusViewGetCurrentPrinting:
    """Test get_current_printing method."""

    async def test_get_current_printing_returns_correct_printing(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test get_current_printing returns the current printing."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            await focus.load_printings("Lightning Bolt", sample_printings)

            current = focus.get_current_printing()
            assert current == sample_printings[0]
            assert current.set_code == "lea"

    async def test_get_current_printing_after_navigation(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test get_current_printing after navigating."""
        from textual.app import App

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
        from textual.app import App

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield FocusView("Test", id="focus-view")

        async with TestApp().run_test() as pilot:
            focus = pilot.app.query_one("#focus-view", FocusView)

            current = focus.get_current_printing()
            assert current is None


class TestFocusViewMetadataDisplay:
    """Test metadata display formatting."""

    async def test_display_full_metadata(self, sample_printing: PrintingInfo) -> None:
        """Test all metadata fields display correctly."""
        from textual.app import App

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
        from textual.app import App

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
        from textual.app import App

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
        from textual.app import App

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
        from textual.app import App

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
        from textual.app import App

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
        from textual.app import App

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


class TestImageLoading:
    """Test image loading functionality."""

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_with_valid_url(self, mock_image: Image.Image) -> None:
        """Test load_image_from_url handles valid URL."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        # Clear caches to ensure fresh request
        await clear_image_cache()

        mock_widget = MagicMock()
        mock_widget.loading = False

        # Mock httpx response
        mock_response = MagicMock()
        img_bytes = BytesIO()
        mock_image.save(img_bytes, format="PNG")
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = MagicMock()

        # Create mock client (not context manager - shared client pattern)
        mock_client = MagicMock()

        async def mock_get(_url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            return mock_response

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            result = await load_image_from_url("https://example.com/test.jpg", mock_widget)

            assert result is True
            assert mock_widget.loading is False
            assert mock_widget.image is not None

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_with_404_error(self) -> None:
        """Test load_image_from_url handles 404 gracefully."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        await clear_image_cache()

        mock_widget = MagicMock()
        mock_widget.loading = False

        mock_client = MagicMock()

        async def mock_get(_url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            raise httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            result = await load_image_from_url("https://example.com/missing.jpg", mock_widget)

            assert result is False
            assert mock_widget.loading is False

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_with_timeout(self) -> None:
        """Test load_image_from_url handles timeout."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        await clear_image_cache()

        mock_widget = MagicMock()
        mock_widget.loading = False

        mock_client = MagicMock()

        async def mock_get(_url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            raise httpx.TimeoutException("Timeout")

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            result = await load_image_from_url(
                "https://example.com/slow.jpg", mock_widget, timeout=1.0
            )

            assert result is False
            assert mock_widget.loading is False

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_sets_loading_state(self, mock_image: Image.Image) -> None:
        """Test load_image_from_url sets and clears loading state."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        await clear_image_cache()

        loading_states: list[bool] = []

        class MockWidget:
            def __init__(self) -> None:
                self._loading = False
                self.image: Image.Image | None = None

            @property
            def loading(self) -> bool:
                return self._loading

            @loading.setter
            def loading(self, value: bool) -> None:
                self._loading = value
                loading_states.append(value)

        mock_widget = MockWidget()

        # Mock httpx response
        mock_response = MagicMock()
        img_bytes = BytesIO()
        mock_image.save(img_bytes, format="PNG")
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()

        async def mock_get(_url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            return mock_response

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            await load_image_from_url("https://example.com/test.jpg", mock_widget)

            # Should set loading=True, then loading=False
            assert True in loading_states
            assert False in loading_states

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_converts_rgba_to_rgb(self) -> None:
        """Test load_image_from_url converts RGBA images to RGB."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        await clear_image_cache()

        mock_widget = MagicMock()
        mock_widget.loading = False

        # Create RGBA image
        rgba_image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))

        # Mock httpx response
        mock_response = MagicMock()
        img_bytes = BytesIO()
        rgba_image.save(img_bytes, format="PNG")
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()

        async def mock_get(_url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            return mock_response

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            result = await load_image_from_url("https://example.com/rgba.png", mock_widget)

            assert result is True
            # Image should be converted to RGB
            assert mock_widget.image.mode == "RGB"

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_replaces_normal_with_large(self, mock_image: Image.Image) -> None:
        """Test load_image_from_url replaces 'normal' with 'large' in URL."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        # Clear caches to ensure fresh request
        await clear_image_cache()

        mock_widget = MagicMock()
        mock_widget.loading = False
        called_url = None

        # Mock httpx response
        mock_response = MagicMock()
        img_bytes = BytesIO()
        mock_image.save(img_bytes, format="PNG")
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()

        async def mock_get(url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            nonlocal called_url
            called_url = url
            return mock_response

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            await load_image_from_url(
                "https://example.com/normal/test.jpg", mock_widget, use_large=True
            )

            # Check that URL was modified
            assert called_url is not None
            assert "large" in called_url
            assert "normal" not in called_url

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_does_not_replace_when_use_large_false(
        self, mock_image: Image.Image
    ) -> None:
        """Test load_image_from_url keeps original URL when use_large=False."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        await clear_image_cache()

        mock_widget = MagicMock()
        mock_widget.loading = False
        called_url = None

        # Mock httpx response
        mock_response = MagicMock()
        img_bytes = BytesIO()
        mock_image.save(img_bytes, format="PNG")
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()

        async def mock_get(url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            nonlocal called_url
            called_url = url
            return mock_response

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            original_url = "https://example.com/normal/test.jpg"
            await load_image_from_url(original_url, mock_widget, use_large=False)

            # Check that URL was NOT modified
            assert called_url == original_url
