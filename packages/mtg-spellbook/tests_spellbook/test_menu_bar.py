"""Tests for MenuBar widget."""

from __future__ import annotations

from typing import ClassVar

import pytest
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Input

from mtg_spellbook.widgets.menu import (
    MenuActionRequested,
    MenuBar,
    MenuItem,
    MenuToggled,
)


class MenuBarTestApp(App[None]):
    """Test app with MenuBar widget."""

    messages_received: ClassVar[list[MenuActionRequested | MenuToggled]] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="main-container"):
            yield MenuBar(id="menu-bar")

    def on_menu_action_requested(self, event: MenuActionRequested) -> None:
        """Capture menu action messages."""
        MenuBarTestApp.messages_received.append(event)

    def on_menu_toggled(self, event: MenuToggled) -> None:
        """Capture menu toggle messages."""
        MenuBarTestApp.messages_received.append(event)


class MenuBarFocusTestApp(App[None]):
    """Test app with MenuBar and focusable widgets for focus testing."""

    def compose(self) -> ComposeResult:
        with Vertical(id="main-container"):
            yield MenuBar(id="menu-bar")
            yield Input(placeholder="First input", id="input-1")
            yield Input(placeholder="Second input", id="input-2")
            yield Button("Test Button", id="button-1")


class TestMenuBarWidget:
    """Tests for MenuBar widget functionality."""

    @pytest.fixture(autouse=True)
    def reset_messages(self) -> None:
        """Reset captured messages before each test."""
        MenuBarTestApp.messages_received = []

    @pytest.mark.asyncio
    async def test_menu_starts_collapsed(self) -> None:
        """Test that menu starts in collapsed state."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            assert menu.is_expanded is False

    @pytest.mark.asyncio
    async def test_menu_has_trigger(self) -> None:
        """Test that menu has a trigger element."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)
            trigger = menu.query_one("#menu-trigger")

            assert trigger is not None

    @pytest.mark.asyncio
    async def test_toggle_expands_menu(self) -> None:
        """Test that toggle() expands the menu."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            assert menu.is_expanded is False
            menu.toggle()
            await pilot.pause()

            assert menu.is_expanded is True

    @pytest.mark.asyncio
    async def test_toggle_collapses_expanded_menu(self) -> None:
        """Test that toggle() collapses an expanded menu."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            menu.expand_menu()
            await pilot.pause()
            assert menu.is_expanded is True

            menu.toggle()
            await pilot.pause()
            assert menu.is_expanded is False

    @pytest.mark.asyncio
    async def test_escape_collapses_menu(self) -> None:
        """Test that escape key collapses the menu."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            menu.expand_menu()
            await pilot.pause()
            assert menu.is_expanded is True

            menu.focus()
            await pilot.press("escape")
            await pilot.pause()

            assert menu.is_expanded is False

    @pytest.mark.asyncio
    async def test_f10_toggles_menu(self) -> None:
        """Test that F10 key toggles the menu."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            menu.focus()
            assert menu.is_expanded is False

            await pilot.press("f10")
            await pilot.pause()

            assert menu.is_expanded is True

    @pytest.mark.asyncio
    async def test_ctrl_m_toggles_menu(self) -> None:
        """Test that Ctrl+M key toggles the menu."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            menu.focus()
            assert menu.is_expanded is False

            await pilot.press("ctrl+m")
            await pilot.pause()

            assert menu.is_expanded is True

    @pytest.mark.asyncio
    async def test_menu_has_items(self) -> None:
        """Test that menu contains expected items."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            # Query menu items
            items = list(menu.query(MenuItem))

            # Should have items for browse and actions
            assert len(items) >= 5  # At minimum: artists, sets, decks, collection, random

    @pytest.mark.asyncio
    async def test_menu_items_have_correct_actions(self) -> None:
        """Test that menu items have correct action strings."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            artists_item = menu.query_one("#menu-artists", MenuItem)
            sets_item = menu.query_one("#menu-sets", MenuItem)

            assert artists_item.action == "browse_artists"
            assert sets_item.action == "browse_sets"

    @pytest.mark.asyncio
    async def test_arrow_down_navigates_items(self) -> None:
        """Test that down arrow navigates to next item."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            menu.expand_menu()
            await pilot.pause()

            # First item should be focused
            assert menu._selected_index == 0

            # Press down to go to next item
            await pilot.press("down")
            await pilot.pause()

            assert menu._selected_index == 1

    @pytest.mark.asyncio
    async def test_arrow_up_navigates_items(self) -> None:
        """Test that up arrow navigates to previous item."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            menu.expand_menu()
            await pilot.pause()

            # Navigate down first
            await pilot.press("down")
            await pilot.pause()
            assert menu._selected_index == 1

            # Navigate back up
            await pilot.press("up")
            await pilot.pause()
            assert menu._selected_index == 0

    @pytest.mark.asyncio
    async def test_enter_selects_item_and_posts_message(self) -> None:
        """Test that Enter key selects item and posts MenuActionRequested."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            menu.expand_menu()
            await pilot.pause()

            # Press enter to select first item (Search)
            await pilot.press("enter")
            await pilot.pause()

            # Should have received action message
            action_messages = [
                m for m in MenuBarTestApp.messages_received if isinstance(m, MenuActionRequested)
            ]
            assert len(action_messages) >= 1
            assert action_messages[-1].action == "show_search"

    @pytest.mark.asyncio
    async def test_menu_collapses_after_selection(self) -> None:
        """Test that menu collapses after item is selected."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            menu.expand_menu()
            await pilot.pause()
            assert menu.is_expanded is True

            await pilot.press("enter")
            await pilot.pause()

            assert menu.is_expanded is False

    @pytest.mark.asyncio
    async def test_menu_posts_toggle_message(self) -> None:
        """Test that menu posts MenuToggled message on expand/collapse."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            menu.toggle()
            await pilot.pause()

            toggle_messages = [
                m for m in MenuBarTestApp.messages_received if isinstance(m, MenuToggled)
            ]
            assert len(toggle_messages) >= 1
            assert toggle_messages[-1].expanded is True

    @pytest.mark.asyncio
    async def test_menu_shows_hotkeys_inline(self) -> None:
        """Test that menu items display hotkey hints."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            artists_item = menu.query_one("#menu-artists", MenuItem)

            # Check that hotkey is set
            assert artists_item.hotkey == "a"

    @pytest.mark.asyncio
    async def test_vim_keys_navigate(self) -> None:
        """Test that j/k keys navigate like down/up."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            menu.expand_menu()
            await pilot.pause()

            assert menu._selected_index == 0

            await pilot.press("j")  # vim down
            await pilot.pause()
            assert menu._selected_index == 1

            await pilot.press("k")  # vim up
            await pilot.pause()
            assert menu._selected_index == 0


class TestMenuItem:
    """Tests for MenuItem widget."""

    @pytest.mark.asyncio
    async def test_item_renders_label_and_hotkey(self) -> None:
        """Test that menu item renders correctly."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)
            artists_item = menu.query_one("#menu-artists", MenuItem)

            assert artists_item.label == "Artists"
            assert artists_item.hotkey == "a"
            assert artists_item.action == "browse_artists"

    @pytest.mark.asyncio
    async def test_item_can_be_disabled(self) -> None:
        """Test that menu item can be disabled."""
        async with MenuBarTestApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)
            artists_item = menu.query_one("#menu-artists", MenuItem)

            assert artists_item.is_disabled is False

            artists_item.is_disabled = True
            await pilot.pause()

            assert artists_item.is_disabled is True


class TestMenuFocusRestoration:
    """Tests for menu focus restoration after collapse."""

    @pytest.mark.asyncio
    async def test_tab_works_after_menu_escape(self) -> None:
        """Test that Tab navigation works after opening menu and pressing Escape.

        This tests bug: after using menu and pressing Escape, Tab doesn't work.
        """
        async with MenuBarFocusTestApp().run_test() as pilot:
            # Focus the first input
            input1 = pilot.app.query_one("#input-1", Input)
            input1.focus()
            await pilot.pause()
            assert input1.has_focus, "Input 1 should have focus initially"

            # Open menu (expand it programmatically since F10 requires menu focus)
            menu = pilot.app.query_one("#menu-bar", MenuBar)
            menu.expand_menu()
            await pilot.pause()
            assert menu.is_expanded, "Menu should be expanded"

            # Close menu with Escape (menu items have focus when expanded)
            await pilot.press("escape")
            await pilot.pause()
            assert not menu.is_expanded, "Menu should be collapsed"

            # Now Tab should move focus to the next widget
            await pilot.press("tab")
            await pilot.pause()

            # Check that focus moved to a different widget (not stuck on menu item)
            focused = pilot.app.focused
            assert focused is not None, "Something should have focus after Tab"
            assert focused.id in ("input-1", "input-2", "button-1"), (
                f"Focus should be on a main widget, not '{focused.id}'"
            )

    @pytest.mark.asyncio
    async def test_focus_restored_to_previous_widget_after_escape(self) -> None:
        """Test that focus returns to the previously focused widget after Escape."""
        async with MenuBarFocusTestApp().run_test() as pilot:
            # Focus the second input
            input2 = pilot.app.query_one("#input-2", Input)
            input2.focus()
            await pilot.pause()
            assert input2.has_focus, "Input 2 should have focus initially"

            # Open menu (expand it programmatically)
            menu = pilot.app.query_one("#menu-bar", MenuBar)
            menu.expand_menu()
            await pilot.pause()

            assert menu.is_expanded, "Menu should be expanded"
            # Menu item should now have focus
            assert not input2.has_focus, "Input 2 should not have focus when menu is open"

            # Close menu with Escape
            await pilot.press("escape")
            await pilot.pause()

            # Focus should return to input2
            assert input2.has_focus, (
                "Focus should return to the previously focused widget (input-2)"
            )


class TestMenuFocusRestorationInScreen:
    """Tests for menu focus restoration in pushed screens (like FullCollectionScreen).

    This tests the real-world scenario using the actual MTGSpellbook app
    and FullCollectionScreen to ensure focus is properly restored after
    closing the menu with Escape.
    """

    @pytest.mark.asyncio
    async def test_focus_restored_in_collection_screen(self) -> None:
        """Test that focus is restored to search input after menu Escape.

        Uses the real MTGSpellbook app and FullCollectionScreen:
        1. Navigate to collection screen via menu
        2. Focus the search input
        3. Open menu with F10
        4. Close menu with Escape
        5. Focus should return to search input
        """
        from mtg_spellbook.app import MTGSpellbook

        async with MTGSpellbook().run_test() as pilot:
            # Navigate to collection screen via menu
            await pilot.press("f10")
            await pilot.pause(delay=0.3)
            # Collection is 5th item (index 4): Search, Artists, Sets, Decks, Collection
            for _ in range(4):
                await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause(delay=2.0)  # Allow screen to fully load

            # Verify we're on the collection screen
            screen = pilot.app.screen
            assert "Collection" in type(screen).__name__, (
                f"Expected Collection screen, got {type(screen).__name__}"
            )

            # Focus the search input in the screen
            search_input = screen.query_one("#collection-search-input", Input)
            search_input.focus()
            await pilot.pause()
            assert search_input.has_focus, "Search input should have focus"

            # Open menu with F10
            await pilot.press("f10")
            await pilot.pause()

            menu = screen.query_one("#screen-menu-bar", MenuBar)
            assert menu.is_expanded, "Menu should be expanded"
            assert not search_input.has_focus, "Search should not have focus when menu open"

            # Close menu with Escape
            await pilot.press("escape")
            await pilot.pause()

            # Menu should be closed
            assert not menu.is_expanded, "Menu should be collapsed"

            # Focus should return to the search input in the screen
            assert search_input.has_focus, (
                "Focus should return to the screen's search input after Escape"
            )

    @pytest.mark.asyncio
    async def test_tab_works_after_menu_escape_in_collection_screen(self) -> None:
        """Test that Tab navigation works in collection screen after menu Escape."""
        from mtg_spellbook.app import MTGSpellbook

        async with MTGSpellbook().run_test() as pilot:
            # Navigate to collection screen via menu
            # Collection is 5th item (index 4): Search, Artists, Sets, Decks, Collection
            await pilot.press("f10")
            await pilot.pause(delay=0.3)
            for _ in range(4):
                await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause(delay=2.0)

            screen = pilot.app.screen
            search_input = screen.query_one("#collection-search-input", Input)
            search_input.focus()
            await pilot.pause()

            # Open and close menu
            await pilot.press("f10")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

            # Tab should move focus to next widget
            await pilot.press("tab")
            await pilot.pause()

            # Focus should be on a screen widget, not a menu item
            focused = pilot.app.focused
            assert focused is not None, "Something should have focus"
            # Should be on collection search or another focusable widget in the screen
            assert focused.id is None or "menu-" not in focused.id, (
                f"Focus should be on a screen widget, not menu item '{focused.id}'"
            )
