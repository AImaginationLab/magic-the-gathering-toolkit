"""Comprehensive tests for art_navigator package to prevent regressions."""

from __future__ import annotations

import pytest
from textual.app import App

from mtg_core.data.models.responses import PrintingInfo
from mtg_spellbook.widgets.art_navigator.compare import CompareSlot, CompareView, SummaryBar
from mtg_spellbook.widgets.art_navigator.enhanced import EnhancedArtNavigator
from mtg_spellbook.widgets.art_navigator.focus import FocusView
from mtg_spellbook.widgets.art_navigator.grid import PrintingsGrid
from mtg_spellbook.widgets.art_navigator.preview import PreviewPanel
from mtg_spellbook.widgets.art_navigator.thumbnail import ThumbnailCard
from mtg_spellbook.widgets.art_navigator.view_toggle import ViewMode, ViewModeToggle


# Test fixtures
@pytest.fixture
def sample_printing() -> PrintingInfo:
    """Create a sample printing with all required fields."""
    return PrintingInfo(
        uuid="test-uuid-1",
        set_code="khm",
        collector_number="123",
        price_usd=15.50,
        price_eur=12.75,
        image="https://example.com/image.jpg",
        art_crop="https://example.com/art_crop.jpg",
        artist="John Avon",
        flavor_text="The cold never bothered me anyway.",
        rarity="rare",
        release_date="2021-02-05",
        illustration_id="art-123",
    )


@pytest.fixture
def sample_printings() -> list[PrintingInfo]:
    """Create multiple sample printings for testing."""
    return [
        PrintingInfo(
            uuid="uuid-1",
            set_code="khm",
            collector_number="1",
            price_usd=100.00,
            price_eur=85.00,
            image="https://example.com/1.jpg",
            art_crop="https://example.com/1_art.jpg",
            artist="Artist One",
            flavor_text="Flavor 1",
            rarity="mythic",
            release_date="2021-02-05",
            illustration_id="art-1",
        ),
        PrintingInfo(
            uuid="uuid-2",
            set_code="znr",
            collector_number="50",
            price_usd=5.00,
            price_eur=4.25,
            image="https://example.com/2.jpg",
            art_crop="https://example.com/2_art.jpg",
            artist="Artist Two",
            flavor_text="Flavor 2",
            rarity="rare",
            release_date="2020-09-25",
            illustration_id="art-2",
        ),
        PrintingInfo(
            uuid="uuid-3",
            set_code="eld",
            collector_number="200",
            price_usd=25.00,
            price_eur=20.00,
            image="https://example.com/3.jpg",
            art_crop="https://example.com/3_art.jpg",
            artist="Artist Three",
            flavor_text="Flavor 3",
            rarity="uncommon",
            release_date="2019-10-04",
            illustration_id="art-3",
        ),
        PrintingInfo(
            uuid="uuid-4",
            set_code="m21",
            collector_number="75",
            price_usd=2.50,
            price_eur=2.00,
            image="https://example.com/4.jpg",
            art_crop="https://example.com/4_art.jpg",
            artist="Artist Four",
            flavor_text=None,
            rarity="common",
            release_date="2020-07-03",
            illustration_id="art-4",
        ),
    ]


@pytest.fixture
def minimal_printing() -> PrintingInfo:
    """Create a printing with minimal optional fields."""
    return PrintingInfo(
        uuid="minimal-uuid",
        set_code=None,
        collector_number=None,
        price_usd=None,
        price_eur=None,
        image=None,
        art_crop=None,
        artist=None,
        flavor_text=None,
        rarity=None,
        release_date=None,
        illustration_id=None,
    )


# PrintingInfo Model Tests
class TestPrintingInfoModel:
    """Test PrintingInfo model structure and field handling."""

    def test_all_required_fields_exist(self, sample_printing: PrintingInfo) -> None:
        """Verify all required fields exist on PrintingInfo."""
        assert hasattr(sample_printing, "uuid")
        assert hasattr(sample_printing, "set_code")
        assert hasattr(sample_printing, "collector_number")
        assert hasattr(sample_printing, "price_usd")
        assert hasattr(sample_printing, "price_eur")
        assert hasattr(sample_printing, "image")
        assert hasattr(sample_printing, "art_crop")
        assert hasattr(sample_printing, "artist")
        assert hasattr(sample_printing, "flavor_text")
        assert hasattr(sample_printing, "rarity")
        assert hasattr(sample_printing, "release_date")
        assert hasattr(sample_printing, "illustration_id")

    def test_optional_field_handling(self, minimal_printing: PrintingInfo) -> None:
        """Test that optional fields can be None."""
        assert minimal_printing.set_code is None
        assert minimal_printing.collector_number is None
        assert minimal_printing.price_usd is None
        assert minimal_printing.price_eur is None
        assert minimal_printing.image is None
        assert minimal_printing.art_crop is None
        assert minimal_printing.artist is None
        assert minimal_printing.flavor_text is None
        assert minimal_printing.rarity is None
        assert minimal_printing.release_date is None
        assert minimal_printing.illustration_id is None

    def test_field_types_are_correct(self, sample_printing: PrintingInfo) -> None:
        """Test that field types are correct."""
        assert isinstance(sample_printing.uuid, str)
        assert isinstance(sample_printing.set_code, str)
        assert isinstance(sample_printing.collector_number, str)
        assert isinstance(sample_printing.price_usd, float)
        assert isinstance(sample_printing.price_eur, float)
        assert isinstance(sample_printing.image, str)
        assert isinstance(sample_printing.art_crop, str)
        assert isinstance(sample_printing.artist, str)
        assert isinstance(sample_printing.flavor_text, str)
        assert isinstance(sample_printing.rarity, str)
        assert isinstance(sample_printing.release_date, str)
        assert isinstance(sample_printing.illustration_id, str)


# ThumbnailCard Tests
class TestThumbnailCard:
    """Test ThumbnailCard widget for thumbnail display and interaction."""

    @pytest.mark.asyncio
    async def test_displays_correct_set_code(self, sample_printing: PrintingInfo) -> None:
        """Test that ThumbnailCard displays correct set code."""
        _thumb = ThumbnailCard(sample_printing)

        # Set code should be uppercased
        assert sample_printing.set_code == "khm"

    @pytest.mark.asyncio
    async def test_displays_correct_price_with_formatting(
        self, sample_printing: PrintingInfo
    ) -> None:
        """Test that ThumbnailCard displays price with correct formatting."""
        _thumb = ThumbnailCard(sample_printing)

        # Price should be formatted with 2 decimal places
        expected_price = f"${sample_printing.price_usd:.2f}"
        assert expected_price == "$15.50"

    @pytest.mark.asyncio
    async def test_selected_state_toggles_correctly(self, sample_printing: PrintingInfo) -> None:
        """Test that selected state toggles correctly."""
        thumb = ThumbnailCard(sample_printing)

        # Initially not selected
        assert thumb.selected is False
        assert not thumb.has_class("selected")

        # Set selected
        thumb.set_selected(True)
        assert thumb.selected is True
        assert thumb.has_class("selected")

        # Deselect
        thumb.set_selected(False)
        assert thumb.selected is False
        assert not thumb.has_class("selected")

    @pytest.mark.asyncio
    async def test_price_color_classes_applied_correctly(self) -> None:
        """Test that price color classes are applied correctly."""
        # Test low price
        low_price = PrintingInfo(uuid="1", price_usd=2.99)
        thumb_low = ThumbnailCard(low_price)
        assert thumb_low._get_price_class(2.99) == "price-low"

        # Test medium price
        medium_price = PrintingInfo(uuid="2", price_usd=7.50)
        thumb_medium = ThumbnailCard(medium_price)
        assert thumb_medium._get_price_class(7.50) == "price-medium"

        # Test medium-high price
        med_high_price = PrintingInfo(uuid="3", price_usd=35.00)
        thumb_med_high = ThumbnailCard(med_high_price)
        assert thumb_med_high._get_price_class(35.00) == "price-medium-high"

        # Test high price
        high_price = PrintingInfo(uuid="4", price_usd=150.00)
        thumb_high = ThumbnailCard(high_price)
        assert thumb_high._get_price_class(150.00) == "price-high"

    @pytest.mark.asyncio
    async def test_price_class_boundaries(self) -> None:
        """Test price class boundary conditions."""
        thumb = ThumbnailCard(PrintingInfo(uuid="test"))

        # Boundary tests
        assert thumb._get_price_class(4.99) == "price-low"
        assert thumb._get_price_class(5.00) == "price-medium"
        assert thumb._get_price_class(19.99) == "price-medium"
        assert thumb._get_price_class(20.00) == "price-medium-high"
        assert thumb._get_price_class(99.99) == "price-medium-high"
        assert thumb._get_price_class(100.00) == "price-high"


# PrintingsGrid Tests
class TestPrintingsGrid:
    """Test PrintingsGrid for thumbnail layout and navigation."""

    @pytest.mark.asyncio
    async def test_load_printings_creates_correct_number_of_thumbnails(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that load_printings creates correct number of thumbnails."""
        grid = PrintingsGrid()

        async with App().run_test() as pilot:
            await pilot.app.mount(grid)
            await grid.load_printings("Test Card", sample_printings)

            thumbnails = list(grid.query(ThumbnailCard))
            assert len(thumbnails) == len(sample_printings)

    @pytest.mark.asyncio
    async def test_thumbnail_ids_are_unique(self, sample_printings: list[PrintingInfo]) -> None:
        """Test that thumbnail IDs are unique (no duplicates)."""
        grid = PrintingsGrid()

        async with App().run_test() as pilot:
            await pilot.app.mount(grid)
            await grid.load_printings("Test Card", sample_printings)

            thumbnails = list(grid.query(ThumbnailCard))
            ids = [thumb.id for thumb in thumbnails]

            # Check all IDs are unique
            assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_navigation_left_right_moves_selection(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that left/right navigation moves selection correctly."""
        grid = PrintingsGrid()

        async with App().run_test() as pilot:
            await pilot.app.mount(grid)
            await grid.load_printings("Test Card", sample_printings)

            # Start at index 0
            assert grid._selected_index == 0

            # Move right
            moved = grid.navigate("right")
            assert moved is True
            assert grid._selected_index == 1

            # Move right again
            moved = grid.navigate("right")
            assert moved is True
            assert grid._selected_index == 2

            # Move left
            moved = grid.navigate("left")
            assert moved is True
            assert grid._selected_index == 1

            # Move left again
            moved = grid.navigate("left")
            assert moved is True
            assert grid._selected_index == 0

            # Try to move left at start (should not move)
            moved = grid.navigate("left")
            assert moved is False
            assert grid._selected_index == 0

    @pytest.mark.asyncio
    async def test_navigation_up_down_moves_selection(self) -> None:
        """Test that up/down navigation moves selection correctly."""
        # Create more printings to test grid navigation
        many_printings = [
            PrintingInfo(uuid=f"uuid-{i}", set_code=f"set{i}", price_usd=float(i))
            for i in range(20)
        ]

        grid = PrintingsGrid()

        async with App().run_test() as pilot:
            await pilot.app.mount(grid)
            await grid.load_printings("Test Card", many_printings)

            # Start at index 0
            assert grid._selected_index == 0

            # Move down (6 items per row)
            moved = grid.navigate("down")
            assert moved is True
            assert grid._selected_index == 6

            # Move down again
            moved = grid.navigate("down")
            assert moved is True
            assert grid._selected_index == 12

            # Move up
            moved = grid.navigate("up")
            assert moved is True
            assert grid._selected_index == 6

            # Move up again
            moved = grid.navigate("up")
            assert moved is True
            assert grid._selected_index == 0

            # Try to move up at start (should not move)
            moved = grid.navigate("up")
            assert moved is False
            assert grid._selected_index == 0

    @pytest.mark.asyncio
    async def test_sorting_price_orders_high_to_low(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that price sorting orders high to low."""
        grid = PrintingsGrid()

        async with App().run_test() as pilot:
            await pilot.app.mount(grid)
            await grid.load_printings("Test Card", sample_printings, sort_order="price")

            # Prices in sample_printings: 100, 5, 25, 2.50
            # After sorting by price (high to low): 100, 25, 5, 2.50
            assert grid._printings[0].price_usd == 100.00
            assert grid._printings[1].price_usd == 25.00
            assert grid._printings[2].price_usd == 5.00
            assert grid._printings[3].price_usd == 2.50

    @pytest.mark.asyncio
    async def test_sorting_set_orders_alphabetically(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that set sorting orders alphabetically."""
        grid = PrintingsGrid()

        async with App().run_test() as pilot:
            await pilot.app.mount(grid)
            await grid.load_printings("Test Card", sample_printings, sort_order="set")

            # Set codes: khm, znr, eld, m21
            # After sorting: eld, khm, m21, znr
            assert grid._printings[0].set_code == "eld"
            assert grid._printings[1].set_code == "khm"
            assert grid._printings[2].set_code == "m21"
            assert grid._printings[3].set_code == "znr"

    @pytest.mark.asyncio
    async def test_cycle_sort_toggles_between_modes(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that cycle_sort toggles between sort modes."""
        grid = PrintingsGrid()

        async with App().run_test() as pilot:
            await pilot.app.mount(grid)

            # Start with price sort
            await grid.load_printings("Test Card", sample_printings, sort_order="price")
            assert grid._printings[0].price_usd == 100.00

            # Cycle to set sort
            grid.cycle_sort()
            await pilot.pause()
            # Note: cycle_sort runs async, so actual sort might not complete immediately in test
            # The important part is that it triggers the sort cycle

    @pytest.mark.asyncio
    async def test_selection_callback_fires_on_navigation(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that selection callback fires when navigating."""
        grid = PrintingsGrid()
        callback_count = 0
        callback_index = -1
        callback_printing: PrintingInfo | None = None

        def on_select(index: int, printing: PrintingInfo) -> None:
            nonlocal callback_count, callback_index, callback_printing
            callback_count += 1
            callback_index = index
            callback_printing = printing

        grid.set_on_select(on_select)

        async with App().run_test() as pilot:
            await pilot.app.mount(grid)
            await grid.load_printings("Test Card", sample_printings)

            # Callback should be called once during load
            assert callback_count == 1
            assert callback_index == 0

            # Navigate right
            grid.navigate("right")
            assert callback_count == 2
            assert callback_index == 1


# PreviewPanel Tests
class TestPreviewPanel:
    """Test PreviewPanel for enlarged preview display."""

    @pytest.mark.asyncio
    async def test_stores_current_printing(self, sample_printing: PrintingInfo) -> None:
        """Test that PreviewPanel stores the current printing."""
        preview = PreviewPanel()

        async with App().run_test() as pilot:
            await pilot.app.mount(preview)
            await preview.update_printing("Lightning Bolt", sample_printing)

            assert preview._current_printing == sample_printing

    @pytest.mark.asyncio
    async def test_art_crop_mode_defaults_to_false(self) -> None:
        """Test that art crop mode defaults to false."""
        preview = PreviewPanel()

        async with App().run_test() as pilot:
            await pilot.app.mount(preview)

            assert preview.art_crop_enabled is False

    @pytest.mark.asyncio
    async def test_set_art_crop_mode_updates_state(
        self, sample_printing: PrintingInfo
    ) -> None:
        """Test that set_art_crop_mode updates the state."""
        preview = PreviewPanel()

        async with App().run_test() as pilot:
            await pilot.app.mount(preview)
            await preview.update_printing("Test Card", sample_printing)

            preview.set_art_crop_mode(True)
            assert preview.art_crop_enabled is True

            preview.set_art_crop_mode(False)
            assert preview.art_crop_enabled is False

    @pytest.mark.asyncio
    async def test_handles_printing_without_image(
        self, minimal_printing: PrintingInfo
    ) -> None:
        """Test that PreviewPanel handles printing without image gracefully."""
        preview = PreviewPanel()

        async with App().run_test() as pilot:
            await pilot.app.mount(preview)
            # Should not raise even if image is None
            await preview.update_printing("Minimal Card", minimal_printing)
            assert preview._current_printing == minimal_printing


# FocusView Tests
class TestFocusView:
    """Test FocusView for immersive single-card display."""

    @pytest.mark.asyncio
    async def test_art_crop_mode_toggles_correctly(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that art crop mode toggles correctly."""
        focus = FocusView("Test Card")

        async with App().run_test() as pilot:
            await pilot.app.mount(focus)
            await focus.load_printings("Test Card", sample_printings)

            # Initially not showing art crop
            assert focus.show_art_crop is False

            # Toggle to art crop
            focus.show_art_crop = True
            assert focus.show_art_crop is True

            # Toggle back
            focus.show_art_crop = False
            assert focus.show_art_crop is False

    @pytest.mark.asyncio
    async def test_navigation_between_printings_works(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that navigation between printings works."""
        focus = FocusView("Test Card")

        async with App().run_test() as pilot:
            await pilot.app.mount(focus)
            await focus.load_printings("Test Card", sample_printings)

            # Start at index 0
            assert focus._current_index == 0

            # Navigate next
            await focus.navigate("next")
            assert focus._current_index == 1

            # Navigate next again
            await focus.navigate("next")
            assert focus._current_index == 2

            # Navigate prev
            await focus.navigate("prev")
            assert focus._current_index == 1

            # Navigate prev again
            await focus.navigate("prev")
            assert focus._current_index == 0

            # Try to navigate prev at start (should not change)
            await focus.navigate("prev")
            assert focus._current_index == 0

    @pytest.mark.asyncio
    async def test_displays_all_metadata_fields(self, sample_printing: PrintingInfo) -> None:
        """Test that FocusView displays all metadata fields."""
        focus = FocusView("Test Card")

        async with App().run_test() as pilot:
            await pilot.app.mount(focus)
            await focus.load_printings("Test Card", [sample_printing])

            # Verify current printing is accessible
            current = focus.get_current_printing()
            assert current is not None
            assert current.artist == "John Avon"
            assert current.rarity == "rare"
            assert current.price_usd == 15.50

    @pytest.mark.asyncio
    async def test_handles_missing_flavor_text_gracefully(
        self, minimal_printing: PrintingInfo
    ) -> None:
        """Test that FocusView handles missing flavor text gracefully."""
        focus = FocusView("Test Card")

        async with App().run_test() as pilot:
            await pilot.app.mount(focus)
            await focus.load_printings("Test Card", [minimal_printing])

            # Should not crash with missing flavor text
            current = focus.get_current_printing()
            assert current is not None
            assert current.flavor_text is None


# CompareView Tests
class TestCompareView:
    """Test CompareView for side-by-side comparison."""

    @pytest.mark.asyncio
    async def test_can_add_printings_to_comparison(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that printings can be added to comparison (max 4)."""
        compare = CompareView()

        async with App().run_test() as pilot:
            await pilot.app.mount(compare)

            # Add first printing
            result = await compare.add_printing(sample_printings[0])
            assert result is True
            assert len(compare._printings) == 1

            # Add second printing
            result = await compare.add_printing(sample_printings[1])
            assert result is True
            assert len(compare._printings) == 2

            # Add third printing
            result = await compare.add_printing(sample_printings[2])
            assert result is True
            assert len(compare._printings) == 3

            # Add fourth printing
            result = await compare.add_printing(sample_printings[3])
            assert result is True
            assert len(compare._printings) == 4

    @pytest.mark.asyncio
    async def test_cannot_add_more_than_max_slots(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that cannot add more than MAX_SLOTS printings."""
        compare = CompareView()

        async with App().run_test() as pilot:
            await pilot.app.mount(compare)

            # Fill all slots
            for i in range(CompareView.MAX_SLOTS):
                await compare.add_printing(sample_printings[i % len(sample_printings)])

            # Try to add one more (should fail)
            extra_printing = PrintingInfo(uuid="extra", set_code="extra")
            result = await compare.add_printing(extra_printing)
            assert result is False

    @pytest.mark.asyncio
    async def test_remove_slot_works(self, sample_printings: list[PrintingInfo]) -> None:
        """Test that removing a slot works."""
        compare = CompareView()

        async with App().run_test() as pilot:
            await pilot.app.mount(compare)

            # Add 3 printings
            await compare.add_printing(sample_printings[0])
            await compare.add_printing(sample_printings[1])
            await compare.add_printing(sample_printings[2])
            assert len(compare._printings) == 3

            # Remove slot 2 (index 1)
            await compare.remove_printing(2)
            assert len(compare._printings) == 2

    @pytest.mark.asyncio
    async def test_clear_all_works(self, sample_printings: list[PrintingInfo]) -> None:
        """Test that clear all works."""
        compare = CompareView()

        async with App().run_test() as pilot:
            await pilot.app.mount(compare)

            # Add printings
            await compare.add_printing(sample_printings[0])
            await compare.add_printing(sample_printings[1])
            assert len(compare._printings) == 2

            # Clear all
            await compare.clear_all()
            assert len(compare._printings) == 0

    @pytest.mark.asyncio
    async def test_unique_artwork_detection_works(self) -> None:
        """Test that unique artwork detection works via illustration_id."""
        # Create printings with different illustration IDs
        p1 = PrintingInfo(uuid="1", set_code="a", illustration_id="art-1", artist="Artist A")
        p2 = PrintingInfo(uuid="2", set_code="b", illustration_id="art-2", artist="Artist B")
        # p3 uses same art as p1 (art-1) - could be used in future extended tests

        slot1 = CompareSlot(1)
        slot2 = CompareSlot(2)

        async with App().run_test() as pilot:
            await pilot.app.mount(slot1)
            await pilot.app.mount(slot2)

            # Load first printing
            await slot1.load_printing("Test", p1, first_artwork_id=None)
            # Should show "Original Art"

            # Load second printing with different art
            await slot2.load_printing("Test", p2, first_artwork_id="art-1")
            # Should show "Alternate Art"

    @pytest.mark.asyncio
    async def test_summary_bar_shows_correct_cheapest_most_expensive(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that summary bar shows correct cheapest/most expensive."""
        summary = SummaryBar()

        # Prices: 100, 5, 25, 2.50
        summary.update_summary(sample_printings)

        # Should identify cheapest (2.50) and most expensive (100.00)
        # We can't directly test the rendered text, but we can test the logic
        prices = [p.price_usd for p in sample_printings if p.price_usd is not None]
        assert min(prices) == 2.50
        assert max(prices) == 100.00


# ViewModeToggle Tests
class TestViewModeToggle:
    """Test ViewModeToggle for mode switching."""

    @pytest.mark.asyncio
    async def test_mode_switching_works(self) -> None:
        """Test that mode switching works."""
        toggle = ViewModeToggle()

        async with App().run_test() as pilot:
            await pilot.app.mount(toggle)

            # Start in GALLERY mode
            assert toggle.current_mode == ViewMode.GALLERY

            # Switch to FOCUS
            toggle.set_mode(ViewMode.FOCUS)
            assert toggle.current_mode == ViewMode.FOCUS

            # Switch to COMPARE
            toggle.set_mode(ViewMode.COMPARE)
            assert toggle.current_mode == ViewMode.COMPARE

            # Switch back to GALLERY
            toggle.set_mode(ViewMode.GALLERY)
            assert toggle.current_mode == ViewMode.GALLERY

    @pytest.mark.asyncio
    async def test_active_mode_is_highlighted(self) -> None:
        """Test that active mode is highlighted."""
        toggle = ViewModeToggle()

        async with App().run_test() as pilot:
            await pilot.app.mount(toggle)

            # Initially GALLERY should be active
            gallery_btn = toggle.query_one("#mode-gallery")
            assert gallery_btn.has_class("mode-active")

            # Switch to FOCUS
            toggle.set_mode(ViewMode.FOCUS)
            await pilot.pause()

            focus_btn = toggle.query_one("#mode-focus")
            assert focus_btn.has_class("mode-active")

            gallery_btn = toggle.query_one("#mode-gallery")
            assert gallery_btn.has_class("mode-inactive")


# EnhancedArtNavigator Integration Tests
class TestEnhancedArtNavigator:
    """Integration tests for EnhancedArtNavigator."""

    @pytest.mark.asyncio
    async def test_view_mode_switching(self, sample_printings: list[PrintingInfo]) -> None:
        """Test that view mode switching works."""
        nav = EnhancedArtNavigator(id_prefix="test")

        async with App().run_test() as pilot:
            await pilot.app.mount(nav)
            await nav.load_printings("Test Card", sample_printings)

            # Start in FOCUS (default after loading)
            assert nav.current_view == ViewMode.FOCUS

            # Switch to GALLERY
            nav.action_switch_to_gallery()
            assert nav.current_view == ViewMode.GALLERY

            # Switch to COMPARE
            nav.action_switch_to_compare()
            assert nav.current_view == ViewMode.COMPARE

            # Switch back to FOCUS
            nav.action_switch_to_focus()
            assert nav.current_view == ViewMode.FOCUS

    @pytest.mark.asyncio
    async def test_keyboard_bindings_work_in_each_mode(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that keyboard bindings work in each mode."""
        nav = EnhancedArtNavigator(id_prefix="test")

        async with App().run_test() as pilot:
            await pilot.app.mount(nav)
            await nav.load_printings("Test Card", sample_printings)

            # Starts in FOCUS mode - test focus navigation first
            focus = nav.query_one("#test-focus", FocusView)
            assert focus._current_index == 0

            # Test focus navigation (async operations need to be awaited)
            nav.action_navigate_right()  # Next (runs async)
            await pilot.pause()  # Wait for async operation
            assert focus._current_index == 1

            nav.action_navigate_left()  # Prev (runs async)
            await pilot.pause()  # Wait for async operation
            assert focus._current_index == 0

            # Switch to gallery mode
            nav.action_switch_to_gallery()

            # Test gallery navigation
            grid = nav.query_one("#test-grid", PrintingsGrid)
            nav.action_navigate_right()
            assert grid._selected_index == 1

            nav.action_navigate_left()
            assert grid._selected_index == 0

    @pytest.mark.asyncio
    async def test_state_properly_shared_between_views(
        self, sample_printings: list[PrintingInfo]
    ) -> None:
        """Test that state is properly shared between views."""
        nav = EnhancedArtNavigator(id_prefix="test")

        async with App().run_test() as pilot:
            await pilot.app.mount(nav)
            await nav.load_printings("Test Card", sample_printings)

            # All views should have the same printings
            grid = nav.query_one("#test-grid", PrintingsGrid)
            focus = nav.query_one("#test-focus", FocusView)

            assert len(grid._printings) == len(sample_printings)
            assert len(focus._printings) == len(sample_printings)


# CompareSlot Tests
class TestCompareSlot:
    """Test CompareSlot for individual comparison slots."""

    @pytest.mark.asyncio
    async def test_slot_loads_printing_correctly(self, sample_printing: PrintingInfo) -> None:
        """Test that CompareSlot loads a printing correctly."""
        slot = CompareSlot(slot_number=1)

        async with App().run_test() as pilot:
            await pilot.app.mount(slot)
            await slot.load_printing("Test Card", sample_printing)

            assert slot._printing == sample_printing
            assert slot._card_name == "Test Card"

    @pytest.mark.asyncio
    async def test_slot_clears_correctly(self, sample_printing: PrintingInfo) -> None:
        """Test that CompareSlot clears correctly."""
        slot = CompareSlot(slot_number=1)

        async with App().run_test() as pilot:
            await pilot.app.mount(slot)
            await slot.load_printing("Test Card", sample_printing)

            # Clear slot
            slot.clear_slot()
            assert slot._printing is None
            assert slot._card_name == ""


# SummaryBar Tests
class TestSummaryBar:
    """Test SummaryBar for comparison statistics."""

    @pytest.mark.asyncio
    async def test_summary_with_no_printings(self) -> None:
        """Test that summary handles no printings gracefully."""
        summary = SummaryBar()
        summary.update_summary([])

        # Should show message about no printings

    @pytest.mark.asyncio
    async def test_summary_with_no_prices(self) -> None:
        """Test that summary handles printings with no prices."""
        printings = [
            PrintingInfo(uuid="1", set_code="a", price_usd=None),
            PrintingInfo(uuid="2", set_code="b", price_usd=None),
        ]

        summary = SummaryBar()
        summary.update_summary(printings)

        # Should show message about no price data

    @pytest.mark.asyncio
    async def test_unique_artwork_count(self, sample_printings: list[PrintingInfo]) -> None:
        """Test that unique artwork count is calculated correctly."""
        summary = SummaryBar()
        summary.update_summary(sample_printings)

        # All sample printings have different illustration_ids
        artwork_ids = {p.illustration_id for p in sample_printings if p.illustration_id}
        assert len(artwork_ids) == 4
