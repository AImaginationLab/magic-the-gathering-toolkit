"""Tests for QuickFilterBar widget - filter toggle behavior testing."""

from __future__ import annotations

from typing import Any

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button

from mtg_spellbook.deck.quick_filter_bar import (
    CMCButton,
    ColorButton,
    QuickFilterBar,
    TypeButton,
)


class FilterBarTestApp(App[None]):
    """Test app for QuickFilterBar testing."""

    def __init__(self) -> None:
        super().__init__()
        self.filters_changed_events: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield QuickFilterBar(id="filter-bar")

    def on_quick_filter_bar_filters_changed(self, event: QuickFilterBar.FiltersChanged) -> None:
        """Track filter change events."""
        self.filters_changed_events.append(event.filters)


class TestQuickFilterBarComposition:
    """Tests for QuickFilterBar composition and structure."""

    @pytest.mark.asyncio
    async def test_filter_bar_has_cmc_buttons(self) -> None:
        """Test that filter bar has CMC toggle buttons (0-6, 7+)."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Should have CMC buttons 0-6 and 7+
            cmc_buttons = list(filter_bar.query(".cmc-btn"))
            assert len(cmc_buttons) == 8  # 0, 1, 2, 3, 4, 5, 6, 7+

    @pytest.mark.asyncio
    async def test_filter_bar_has_color_buttons(self) -> None:
        """Test that filter bar has WUBRG color buttons."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            color_buttons = list(filter_bar.query(".color-btn"))
            assert len(color_buttons) == 5  # W, U, B, R, G

            # Verify correct colors are present
            colors = {btn.color_value for btn in color_buttons if isinstance(btn, ColorButton)}
            assert colors == {"W", "U", "B", "R", "G"}

    @pytest.mark.asyncio
    async def test_filter_bar_has_type_buttons(self) -> None:
        """Test that filter bar has type toggle buttons."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            type_buttons = list(filter_bar.query(".type-btn"))
            assert len(type_buttons) == 5  # Creature, Instant, Sorcery, Artifact, Enchantment

            # Verify correct types are present
            types = {btn.type_value for btn in type_buttons if isinstance(btn, TypeButton)}
            assert types == {"Creature", "Instant", "Sorcery", "Artifact", "Enchantment"}


def _simulate_button_press(button: Button) -> None:
    """Simulate a button press by posting the Pressed message."""
    button.post_message(Button.Pressed(button))


class TestCMCFilterToggle:
    """Tests for CMC filter toggle behavior."""

    @pytest.mark.asyncio
    async def test_press_cmc_button_activates_filter(self) -> None:
        """Test pressing a CMC button activates that filter."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Initially no CMC filter active
            assert filter_bar.active_cmc is None

            # Simulate button press by posting the message directly
            cmc1_btn = filter_bar.query_one("#cmc-1", CMCButton)
            _simulate_button_press(cmc1_btn)
            await pilot.pause()

            # CMC filter should be set to 1
            assert filter_bar.active_cmc == 1

    @pytest.mark.asyncio
    async def test_press_same_cmc_button_deactivates(self) -> None:
        """Test pressing the same CMC button deactivates the filter."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Press CMC 2 to activate
            cmc2_btn = filter_bar.query_one("#cmc-2", CMCButton)
            _simulate_button_press(cmc2_btn)
            await pilot.pause()
            assert filter_bar.active_cmc == 2

            # Press CMC 2 again to deactivate
            _simulate_button_press(cmc2_btn)
            await pilot.pause()
            assert filter_bar.active_cmc is None

    @pytest.mark.asyncio
    async def test_only_one_cmc_filter_active(self) -> None:
        """Test that only one CMC filter can be active at a time."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Press CMC 1
            cmc1_btn = filter_bar.query_one("#cmc-1", CMCButton)
            _simulate_button_press(cmc1_btn)
            await pilot.pause()
            assert filter_bar.active_cmc == 1

            # Press CMC 3 (should replace CMC 1)
            cmc3_btn = filter_bar.query_one("#cmc-3", CMCButton)
            _simulate_button_press(cmc3_btn)
            await pilot.pause()
            assert filter_bar.active_cmc == 3

            # Only CMC 3 button should have -active class
            assert not cmc1_btn.has_class("-active")
            assert cmc3_btn.has_class("-active")

    @pytest.mark.asyncio
    async def test_cmc_7plus_sets_value_to_7(self) -> None:
        """Test that 7+ CMC button sets filter value to 7."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Press 7+ button
            cmc7plus_btn = filter_bar.query_one("#cmc-7plus", CMCButton)
            _simulate_button_press(cmc7plus_btn)
            await pilot.pause()

            assert filter_bar.active_cmc == 7


class TestColorFilterToggle:
    """Tests for color filter toggle behavior."""

    @pytest.mark.asyncio
    async def test_press_color_button_activates_filter(self) -> None:
        """Test pressing a color button activates that color filter."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Initially no colors selected
            assert filter_bar._active_colors == set()

            # Press Red color button
            red_btn = filter_bar.query_one("#color-R", ColorButton)
            _simulate_button_press(red_btn)
            await pilot.pause()

            assert "R" in filter_bar._active_colors

    @pytest.mark.asyncio
    async def test_press_same_color_button_deactivates(self) -> None:
        """Test pressing the same color button toggles it off."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Press Red to activate
            red_btn = filter_bar.query_one("#color-R", ColorButton)
            _simulate_button_press(red_btn)
            await pilot.pause()
            assert "R" in filter_bar._active_colors

            # Press Red again to deactivate
            _simulate_button_press(red_btn)
            await pilot.pause()
            assert "R" not in filter_bar._active_colors

    @pytest.mark.asyncio
    async def test_multiple_colors_can_be_active(self) -> None:
        """Test that multiple color filters can be active simultaneously."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Press multiple colors
            _simulate_button_press(filter_bar.query_one("#color-R", ColorButton))
            await pilot.pause()
            _simulate_button_press(filter_bar.query_one("#color-U", ColorButton))
            await pilot.pause()
            _simulate_button_press(filter_bar.query_one("#color-G", ColorButton))
            await pilot.pause()

            # All three should be active
            assert filter_bar._active_colors == {"R", "U", "G"}

            # Deactivate one
            _simulate_button_press(filter_bar.query_one("#color-U", ColorButton))
            await pilot.pause()
            assert filter_bar._active_colors == {"R", "G"}


class TestTypeFilterToggle:
    """Tests for type filter toggle behavior."""

    @pytest.mark.asyncio
    async def test_press_type_button_activates_filter(self) -> None:
        """Test pressing a type button activates that type filter."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Initially no type filter
            assert filter_bar.active_type is None

            # Press Creature button
            creature_btn = filter_bar.query_one("#type-creature", TypeButton)
            _simulate_button_press(creature_btn)
            await pilot.pause()

            assert filter_bar.active_type == "Creature"

    @pytest.mark.asyncio
    async def test_press_same_type_button_deactivates(self) -> None:
        """Test pressing the same type button deactivates the filter."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Press Instant to activate
            instant_btn = filter_bar.query_one("#type-instant", TypeButton)
            _simulate_button_press(instant_btn)
            await pilot.pause()
            assert filter_bar.active_type == "Instant"

            # Press Instant again to deactivate
            _simulate_button_press(instant_btn)
            await pilot.pause()
            assert filter_bar.active_type is None

    @pytest.mark.asyncio
    async def test_only_one_type_filter_active(self) -> None:
        """Test that only one type filter can be active at a time."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Press Creature
            _simulate_button_press(filter_bar.query_one("#type-creature", TypeButton))
            await pilot.pause()
            assert filter_bar.active_type == "Creature"

            # Press Sorcery (should replace Creature)
            _simulate_button_press(filter_bar.query_one("#type-sorcery", TypeButton))
            await pilot.pause()
            assert filter_bar.active_type == "Sorcery"


class TestFilterCombination:
    """Tests for combining multiple filters."""

    @pytest.mark.asyncio
    async def test_combine_cmc_and_color_filters(self) -> None:
        """Test that CMC and color filters combine correctly."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Set CMC filter
            _simulate_button_press(filter_bar.query_one("#cmc-2", CMCButton))
            await pilot.pause()

            # Set color filter
            _simulate_button_press(filter_bar.query_one("#color-R", ColorButton))
            await pilot.pause()

            filters = filter_bar.get_filters()
            assert filters["cmc"] == 2
            assert filters["colors"] == ["R"]

    @pytest.mark.asyncio
    async def test_combine_all_filter_types(self) -> None:
        """Test that all filter types combine correctly."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Set CMC filter
            _simulate_button_press(filter_bar.query_one("#cmc-3", CMCButton))
            await pilot.pause()

            # Set color filters (multiple)
            _simulate_button_press(filter_bar.query_one("#color-U", ColorButton))
            await pilot.pause()
            _simulate_button_press(filter_bar.query_one("#color-B", ColorButton))
            await pilot.pause()

            # Set type filter
            _simulate_button_press(filter_bar.query_one("#type-instant", TypeButton))
            await pilot.pause()

            filters = filter_bar.get_filters()
            assert filters["cmc"] == 3
            assert set(filters["colors"]) == {"U", "B"}
            assert filters["type"] == "Instant"


class TestClearFilters:
    """Tests for clearing all filters."""

    @pytest.mark.asyncio
    async def test_clear_filters_resets_all(self) -> None:
        """Test that clear_filters() resets all active filters."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Set various filters
            _simulate_button_press(filter_bar.query_one("#cmc-2", CMCButton))
            _simulate_button_press(filter_bar.query_one("#color-R", ColorButton))
            _simulate_button_press(filter_bar.query_one("#color-G", ColorButton))
            _simulate_button_press(filter_bar.query_one("#type-creature", TypeButton))
            await pilot.pause()

            # Verify filters are set
            filters = filter_bar.get_filters()
            assert len(filters) > 0

            # Clear all filters
            filter_bar.clear_filters()
            await pilot.pause()

            # All filters should be empty
            filters = filter_bar.get_filters()
            assert filters == {}

    @pytest.mark.asyncio
    async def test_clear_filters_removes_active_class(self) -> None:
        """Test that clear_filters() removes -active class from buttons."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            # Set CMC filter
            cmc1_btn = filter_bar.query_one("#cmc-1", CMCButton)
            _simulate_button_press(cmc1_btn)
            await pilot.pause()
            assert cmc1_btn.has_class("-active")

            # Clear filters
            filter_bar.clear_filters()
            await pilot.pause()

            # Button should no longer have -active class
            assert not cmc1_btn.has_class("-active")


class TestFiltersChangedMessage:
    """Tests for FiltersChanged message emission."""

    @pytest.mark.asyncio
    async def test_cmc_change_emits_message(self) -> None:
        """Test that CMC filter change emits FiltersChanged message."""
        async with FilterBarTestApp().run_test() as pilot:
            app = pilot.app
            assert isinstance(app, FilterBarTestApp)
            filter_bar = app.query_one("#filter-bar", QuickFilterBar)

            # Press CMC button
            _simulate_button_press(filter_bar.query_one("#cmc-1", CMCButton))
            await pilot.pause()

            # Should have received a filter change event
            assert len(app.filters_changed_events) >= 1
            assert app.filters_changed_events[-1].get("cmc") == 1

    @pytest.mark.asyncio
    async def test_color_change_emits_message(self) -> None:
        """Test that color filter change emits FiltersChanged message."""
        async with FilterBarTestApp().run_test() as pilot:
            app = pilot.app
            assert isinstance(app, FilterBarTestApp)
            filter_bar = app.query_one("#filter-bar", QuickFilterBar)

            # Press color button
            _simulate_button_press(filter_bar.query_one("#color-B", ColorButton))
            await pilot.pause()

            # Should have received a filter change event
            assert len(app.filters_changed_events) >= 1
            assert "B" in app.filters_changed_events[-1].get("colors", [])

    @pytest.mark.asyncio
    async def test_type_change_emits_message(self) -> None:
        """Test that type filter change emits FiltersChanged message."""
        async with FilterBarTestApp().run_test() as pilot:
            app = pilot.app
            assert isinstance(app, FilterBarTestApp)
            filter_bar = app.query_one("#filter-bar", QuickFilterBar)

            # Press type button
            _simulate_button_press(filter_bar.query_one("#type-sorcery", TypeButton))
            await pilot.pause()

            # Should have received a filter change event
            assert len(app.filters_changed_events) >= 1
            assert app.filters_changed_events[-1].get("type") == "Sorcery"


class TestButtonTypes:
    """Tests for individual button type widgets."""

    @pytest.mark.asyncio
    async def test_cmc_button_stores_value(self) -> None:
        """Test that CMCButton stores its CMC value."""
        btn = CMCButton(3)
        assert btn.cmc_value == 3

        btn7plus = CMCButton("7+")
        assert btn7plus.cmc_value == "7+"

    @pytest.mark.asyncio
    async def test_color_button_stores_value(self) -> None:
        """Test that ColorButton stores its color value."""
        btn = ColorButton("R")
        assert btn.color_value == "R"

    @pytest.mark.asyncio
    async def test_type_button_stores_value_and_short_label(self) -> None:
        """Test that TypeButton stores full type and uses short label."""
        btn = TypeButton("Creature")
        assert btn.type_value == "Creature"
        # Label should be shortened
        assert btn.label == "Cre"

        btn2 = TypeButton("Enchantment")
        assert btn2.type_value == "Enchantment"
        assert btn2.label == "Enc"

        btn3 = TypeButton("Planeswalker")
        assert btn3.type_value == "Planeswalker"
        assert btn3.label == "PW"


class TestGetFiltersMethod:
    """Tests for the get_filters() method."""

    @pytest.mark.asyncio
    async def test_get_filters_returns_empty_dict_initially(self) -> None:
        """Test that get_filters() returns empty dict when no filters set."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)
            filters = filter_bar.get_filters()
            assert filters == {}

    @pytest.mark.asyncio
    async def test_get_filters_returns_cmc_only(self) -> None:
        """Test get_filters() with only CMC set."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            _simulate_button_press(filter_bar.query_one("#cmc-4", CMCButton))
            await pilot.pause()

            filters = filter_bar.get_filters()
            assert filters == {"cmc": 4}

    @pytest.mark.asyncio
    async def test_get_filters_returns_colors_as_list(self) -> None:
        """Test that get_filters() returns colors as a list."""
        async with FilterBarTestApp().run_test() as pilot:
            filter_bar = pilot.app.query_one("#filter-bar", QuickFilterBar)

            _simulate_button_press(filter_bar.query_one("#color-W", ColorButton))
            await pilot.pause()

            filters = filter_bar.get_filters()
            assert "colors" in filters
            assert isinstance(filters["colors"], list)
            assert "W" in filters["colors"]
