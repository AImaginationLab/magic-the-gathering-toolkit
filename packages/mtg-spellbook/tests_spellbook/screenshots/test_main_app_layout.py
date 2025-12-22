"""Layout tests for the main MTGSpellbook app.

Tests verify that header and footer remain visible (sticky) across all views.
Uses the real MTGSpellbook app to ensure proper CSS and styles.
"""

from __future__ import annotations

import asyncio

import pytest
from textual.widgets import Footer, Static

from mtg_spellbook.app import MTGSpellbook
from mtg_spellbook.widgets import MenuBar


class TestMainAppLayout:
    """Tests for main app layout - header and footer must be sticky."""

    @pytest.mark.asyncio
    async def test_header_visible_at_top(self) -> None:
        """Header must be visible at the top of the screen."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.5)

            header = pilot.app.query_one("#header-content", Static)

            # Header must have non-zero height
            assert header.region.height > 0, f"Header has zero height: {header.region}"

            # Header must be at top (y should be 0 or very near)
            assert header.region.y <= 1, f"Header not at top. Header y: {header.region.y}"

    @pytest.mark.asyncio
    async def test_footer_visible_at_bottom(self) -> None:
        """Footer must be visible at the bottom of the screen."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.5)

            footer = pilot.app.query_one(Footer)

            # Footer must have non-zero height
            assert footer.region.height > 0, f"Footer has zero height: {footer.region}"

            # Footer should be near the bottom of the screen
            screen_height = 40
            footer_bottom = footer.region.y + footer.region.height
            assert footer_bottom >= screen_height - 2, (
                f"Footer not at bottom. Footer bottom: {footer_bottom}, "
                f"Screen height: {screen_height}"
            )

    @pytest.mark.asyncio
    async def test_menu_bar_below_header(self) -> None:
        """Menu bar must be visible below the header."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.5)

            header = pilot.app.query_one("#header-content", Static)
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            # Menu must have non-zero height
            assert menu.region.height > 0, f"Menu bar has zero height: {menu.region}"

            # Menu must be below header
            header_bottom = header.region.y + header.region.height
            assert menu.region.y >= header_bottom - 1, (
                f"Menu not below header. Header bottom: {header_bottom}, Menu y: {menu.region.y}"
            )

    @pytest.mark.asyncio
    async def test_elements_in_proper_vertical_order(self) -> None:
        """Elements should be stacked: header -> menu -> content -> footer."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.5)

            header = pilot.app.query_one("#header-content", Static)
            menu = pilot.app.query_one("#menu-bar", MenuBar)
            main = pilot.app.query_one("#main-container")
            footer = pilot.app.query_one(Footer)

            # Verify vertical ordering
            assert header.region.y < menu.region.y, (
                f"Header (y={header.region.y}) should be above menu (y={menu.region.y})"
            )
            assert menu.region.y < main.region.y, (
                f"Menu (y={menu.region.y}) should be above main (y={main.region.y})"
            )
            assert main.region.y < footer.region.y, (
                f"Main (y={main.region.y}) should be above footer (y={footer.region.y})"
            )

    @pytest.mark.asyncio
    async def test_main_content_fills_available_space(self) -> None:
        """Main content should fill space between menu and footer."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.5)

            main = pilot.app.query_one("#main-container")
            footer = pilot.app.query_one(Footer)

            # Main content should have substantial height
            assert main.region.height >= 20, (
                f"Main content height too small: {main.region.height}. "
                f"Expected >= 20 for a 40-line terminal."
            )

            # Main content bottom should touch footer top
            main_bottom = main.region.y + main.region.height
            assert main_bottom <= footer.region.y + 1, (
                f"Main content (bottom={main_bottom}) should touch footer (top={footer.region.y})"
            )

    @pytest.mark.asyncio
    async def test_collection_screen_menu_visible_and_opens(self) -> None:
        """On Collection screen, menu must be visible and all items visible when opened."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.5)

            # Navigate to Collection screen via menu (Search=0, Artists=1, Sets=2, Decks=3, Collection=4)
            await pilot.press("f10")
            await asyncio.sleep(0.3)
            for _ in range(4):
                await pilot.press("down")
            await pilot.press("enter")
            await asyncio.sleep(1.0)  # Wait for screen to load

            # Verify we're on Collection screen
            screen = pilot.app.screen
            screen_name = type(screen).__name__
            stack_info = [type(s).__name__ for s in pilot.app.screen_stack]

            assert "Collection" in screen_name, (
                f"Expected Collection screen, got {screen_name}. Screen stack: {stack_info}"
            )

            # Collection screen (BaseScreen) has its own menu bar with id #screen-menu-bar
            # Query on the screen directly, not pilot.app
            try:
                menu = screen.query_one("#screen-menu-bar", MenuBar)
            except Exception as e:
                # Debug: show what widgets exist in the screen
                all_widgets = list(screen.query("*"))
                widget_ids = [w.id for w in all_widgets if w.id]
                raise AssertionError(
                    f"Could not find #screen-menu-bar. Error: {e}. "
                    f"Screen: {screen_name}. Widget IDs in screen: {widget_ids[:20]}"
                ) from e
            assert menu.region.height > 0, "Menu bar should be visible on Collection screen"

            # Menu should be at the top of the screen (y = 0)
            assert menu.region.y == 0, (
                f"Menu bar should be at top of screen (y=0). Menu y: {menu.region.y}"
            )

            # Verify footer is at bottom
            footer = pilot.app.query_one(Footer)
            screen_height = 40
            footer_bottom = footer.region.y + footer.region.height
            assert footer_bottom >= screen_height - 2, (
                f"Footer not at bottom on Collection screen. Footer bottom: {footer_bottom}"
            )

            # Open menu with F10
            await pilot.press("f10")
            await asyncio.sleep(0.3)

            # Verify menu is expanded
            assert menu.is_expanded, "Menu should be expanded after F10"

            # Get all menu items and verify they're all visible on screen
            from mtg_spellbook.widgets.menu import MenuItem

            menu_items = list(pilot.app.query(MenuItem))
            assert len(menu_items) > 0, "Should have menu items"

            # All menu items should be within screen bounds (y >= 0 and y < screen_height)
            for item in menu_items:
                assert item.region.y >= 0, (
                    f"Menu item '{item.id}' is above screen (y={item.region.y})"
                )
                assert item.region.y < screen_height, (
                    f"Menu item '{item.id}' is below screen (y={item.region.y})"
                )

            # First menu item should be near the top
            first_item = menu_items[0]
            assert first_item.region.y < 15, (
                f"First menu item too far down (y={first_item.region.y}). "
                f"Menu may have scrolled out of view."
            )
