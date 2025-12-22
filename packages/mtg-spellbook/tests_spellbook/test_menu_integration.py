"""Integration tests for MenuBar in the main app."""

from __future__ import annotations

from typing import ClassVar

import pytest
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer

from mtg_spellbook.widgets.menu import MenuActionRequested, MenuBar


class MockApp(App[None]):
    """Minimal app for testing menu integration."""

    messages_received: ClassVar[list[MenuActionRequested]] = []
    actions_called: ClassVar[list[str]] = []

    def compose(self) -> ComposeResult:
        yield MenuBar(id="menu-bar")
        with Vertical(id="main-content"):
            pass
        yield Footer()

    def on_menu_action_requested(self, event: MenuActionRequested) -> None:
        """Route menu actions to existing action handlers."""
        MockApp.messages_received.append(event)
        action_method = getattr(self, f"action_{event.action}", None)
        if action_method:
            action_method()

    def action_show_search(self) -> None:
        MockApp.actions_called.append("show_search")

    def action_browse_artists(self) -> None:
        MockApp.actions_called.append("browse_artists")

    def action_browse_sets(self) -> None:
        MockApp.actions_called.append("browse_sets")

    def action_browse_decks(self) -> None:
        MockApp.actions_called.append("browse_decks")

    def action_browse_collection(self) -> None:
        MockApp.actions_called.append("browse_collection")

    def action_random_card(self) -> None:
        MockApp.actions_called.append("random_card")

    def action_synergy_current(self) -> None:
        MockApp.actions_called.append("synergy_current")


class TestMenuIntegration:
    """Test menu integration with the app."""

    @pytest.fixture(autouse=True)
    def reset_state(self) -> None:
        """Reset state before each test."""
        MockApp.messages_received = []
        MockApp.actions_called = []

    @pytest.mark.asyncio
    async def test_menu_bar_renders_in_app(self) -> None:
        """Test that menu bar renders in the app."""
        async with MockApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)
            assert menu is not None

    @pytest.mark.asyncio
    async def test_f10_toggles_menu_in_app(self) -> None:
        """Test that F10 toggles the menu."""
        async with MockApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)
            menu.focus()

            assert menu.is_expanded is False
            await pilot.press("f10")
            await pilot.pause()
            assert menu.is_expanded is True

    @pytest.mark.asyncio
    async def test_menu_action_triggers_show_search(self) -> None:
        """Test that selecting Search item triggers action_show_search."""
        async with MockApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            # Expand menu and select first item (Search)
            menu.expand_menu()
            await pilot.pause()

            await pilot.press("enter")
            await pilot.pause()

            # Verify message was received and action called
            assert len(MockApp.messages_received) >= 1
            assert MockApp.messages_received[-1].action == "show_search"
            assert "show_search" in MockApp.actions_called

    @pytest.mark.asyncio
    async def test_menu_action_triggers_browse_artists(self) -> None:
        """Test that selecting Artists item triggers action_browse_artists."""
        async with MockApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            # Expand menu and navigate to Artists (second item, after Search)
            menu.expand_menu()
            await pilot.pause()

            await pilot.press("down")  # Move to Artists
            await pilot.pause()

            await pilot.press("enter")
            await pilot.pause()

            # Verify message was received and action called
            assert len(MockApp.messages_received) >= 1
            assert MockApp.messages_received[-1].action == "browse_artists"
            assert "browse_artists" in MockApp.actions_called

    @pytest.mark.asyncio
    async def test_menu_action_triggers_browse_sets(self) -> None:
        """Test that selecting Sets item triggers action_browse_sets."""
        async with MockApp().run_test() as pilot:
            menu = pilot.app.query_one("#menu-bar", MenuBar)

            # Expand menu and navigate to Sets (third item)
            menu.expand_menu()
            await pilot.pause()

            await pilot.press("down")  # Move to Artists
            await pilot.press("down")  # Move to Sets
            await pilot.pause()

            await pilot.press("enter")
            await pilot.pause()

            # Verify message was received and action called
            assert len(MockApp.messages_received) >= 1
            assert MockApp.messages_received[-1].action == "browse_sets"
            assert "browse_sets" in MockApp.actions_called

    @pytest.mark.asyncio
    async def test_hotkeys_still_work_with_menu(self) -> None:
        """Test that direct hotkeys still work alongside menu."""
        async with MockApp().run_test() as pilot:
            # Focus on the main content, not the menu
            main = pilot.app.query_one("#main-content")
            main.focus()

            # Menu should be collapsed
            menu = pilot.app.query_one("#menu-bar", MenuBar)
            assert menu.is_expanded is False

            # Menu hotkeys (F10) should still work
            await pilot.press("f10")
            await pilot.pause()
            assert menu.is_expanded is True

    @pytest.mark.asyncio
    async def test_footer_visible_with_menu(self) -> None:
        """Test that footer is visible alongside menu."""
        async with MockApp().run_test() as pilot:
            footer = pilot.app.query_one(Footer)
            assert footer is not None
            assert footer.display is True
