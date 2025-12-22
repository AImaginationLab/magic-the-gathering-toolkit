"""Visual regression tests for MTG Spellbook app states.

These tests capture SVG screenshots of various UI states to serve as both
documentation and regression tests for visual changes.

Run with: uv run pytest packages/mtg-spellbook/tests/screenshots/ -v
Update snapshots: uv run pytest packages/mtg-spellbook/tests/screenshots/ --snapshot-update
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from mtg_spellbook.app import MTGSpellbook

from .conftest import MENU_ARTISTS, MENU_COLLECTION, MENU_SETS, navigate_via_menu

# Skip all tests if pytest-textual-snapshot is not installed
pytest.importorskip("pytest_textual_snapshot")

if TYPE_CHECKING:
    from textual.pilot import Pilot


@pytest.mark.usefixtures("mock_database_for_snapshots")
class TestMTGSpellbookScreenshots:
    """Visual regression tests for MTG Spellbook app.

    These tests use mock database data for deterministic snapshots.
    """

    def test_initial_state(self, snap_compare: Any) -> None:
        """Screenshot of the app immediately after loading."""
        assert snap_compare(
            MTGSpellbook(),
            terminal_size=(120, 40),
        )

    def test_menu_expanded(self, snap_compare: Any) -> None:
        """Screenshot with the menu bar expanded (F10)."""
        assert snap_compare(
            MTGSpellbook(),
            press=["f10"],
            terminal_size=(120, 40),
        )

    def test_menu_browse_section(self, snap_compare: Any) -> None:
        """Screenshot with menu expanded and navigated to browse options."""
        # F10 to open menu, then navigate down to see browse section
        assert snap_compare(
            MTGSpellbook(),
            press=["f10", "down", "down"],
            terminal_size=(120, 40),
        )

    def test_search_input_focused(self, snap_compare: Any) -> None:
        """Screenshot with search input focused and ready for typing."""
        # Press escape to ensure focus goes to search input
        assert snap_compare(
            MTGSpellbook(),
            press=["escape"],
            terminal_size=(120, 40),
        )

    def test_search_with_query(self, snap_compare: Any) -> None:
        """Screenshot after typing a search query."""

        async def type_search(pilot: Pilot[None]) -> None:
            """Type a search query into the search box."""
            # Focus search input
            await pilot.press("escape")
            await pilot.pause()
            # Type search query
            await pilot.press("l", "i", "g", "h", "t", "n", "i", "n", "g")
            await pilot.pause()

        assert snap_compare(
            MTGSpellbook(),
            run_before=type_search,
            terminal_size=(120, 40),
        )

    def test_search_results_displayed(self, snap_compare: Any) -> None:
        """Screenshot showing search results after pressing Enter."""

        async def perform_search(pilot: Pilot[None]) -> None:
            """Type a search query and execute it."""
            # Focus search input
            await pilot.press("escape")
            await pilot.pause()
            # Type search query for a common card
            await pilot.press("l", "i", "g", "h", "t", "n", "i", "n", "g", " ", "b", "o", "l", "t")
            await pilot.pause()
            # Execute search
            await pilot.press("enter")
            # Wait for results to load
            await pilot.pause(delay=0.5)

        assert snap_compare(
            MTGSpellbook(),
            run_before=perform_search,
            terminal_size=(120, 40),
        )

    def test_card_selected_in_results(self, snap_compare: Any) -> None:
        """Screenshot with a card selected from search results."""

        async def select_card(pilot: Pilot[None]) -> None:
            """Search for a specific card and select it from results."""
            await pilot.press("escape")
            await pilot.pause()
            # Search for Lightning Bolt - consistent results
            for char in "lightning bolt":
                await pilot.press(char)
            await pilot.press("enter")
            # Longer pause to ensure results fully load
            await pilot.pause(delay=1.0)
            # Navigate to results (Tab to results list)
            await pilot.press("tab")
            await pilot.pause(delay=0.3)

        assert snap_compare(
            MTGSpellbook(),
            run_before=select_card,
            terminal_size=(120, 40),
        )

    def test_card_detail_display(self, snap_compare: Any) -> None:
        """Screenshot showing a specific card's details."""

        async def show_card(pilot: Pilot[None]) -> None:
            """Search for a specific card to show its details."""
            await pilot.press("escape")
            await pilot.pause()
            # Search for a well-known card with consistent data
            for char in "sol ring":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause(delay=0.5)

        assert snap_compare(
            MTGSpellbook(),
            run_before=show_card,
            terminal_size=(120, 40),
        )

    def test_artists_browser(self, snap_compare: Any) -> None:
        """Screenshot of the Artists screen via menu navigation."""

        async def open_artists(pilot: Pilot[None]) -> None:
            await navigate_via_menu(pilot, MENU_ARTISTS, delay=0.5)
            # Wait for content to load
            await pilot.pause(delay=0.5)

            # Verify artists screen is visible
            from mtg_spellbook.screens import ArtistsScreen

            screen = pilot.app.screen
            assert isinstance(screen, ArtistsScreen), (
                f"Expected ArtistsScreen, got {type(screen).__name__}"
            )

            # Verify content is rendering (list should have items)
            from textual.widgets import Static

            statics = list(pilot.app.query(Static))
            # Should have more than just header and statusbar - need list items
            assert len(statics) > 10, (
                f"Expected artists list to have content, only found {len(statics)} text elements"
            )

        assert snap_compare(
            MTGSpellbook(),
            run_before=open_artists,
            terminal_size=(120, 40),
        )

    def test_sets_browser(self, snap_compare: Any) -> None:
        """Screenshot of the Sets screen via menu navigation."""

        async def open_sets(pilot: Pilot[None]) -> None:
            await navigate_via_menu(pilot, MENU_SETS, delay=0.5)
            # Wait for content to load
            await pilot.pause(delay=0.5)

            # Verify sets screen is visible
            from mtg_spellbook.screens import SetsScreen

            screen = pilot.app.screen
            assert isinstance(screen, SetsScreen), (
                f"Expected SetsScreen, got {type(screen).__name__}"
            )

            # Verify content is rendering (list should have items)
            from textual.widgets import Static

            statics = list(pilot.app.query(Static))
            # Should have more than just header and statusbar - need list items
            assert len(statics) > 10, (
                f"Expected sets list to have content, only found {len(statics)} text elements"
            )

        assert snap_compare(
            MTGSpellbook(),
            run_before=open_sets,
            terminal_size=(120, 40),
        )

    def test_deck_panel_toggle(self, snap_compare: Any) -> None:
        """Screenshot with deck panel toggled visible."""

        async def toggle_deck(pilot: Pilot[None]) -> None:
            """Press ctrl+n to toggle deck panel."""
            await pilot.press("ctrl+n")
            await pilot.pause(delay=0.3)

        assert snap_compare(
            MTGSpellbook(),
            run_before=toggle_deck,
            terminal_size=(140, 40),
        )

    def test_synergy_mode(self, snap_compare: Any) -> None:
        """Screenshot of synergy mode after selecting a card and pressing ctrl+s."""

        async def enter_synergy_mode(pilot: Pilot[None]) -> None:
            """Search for a specific card and enter synergy mode."""
            await pilot.press("escape")
            await pilot.pause()
            # Search for a card with known synergies
            for char in "lightning bolt":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause(delay=0.5)
            # Enter synergy mode
            await pilot.press("ctrl+s")
            await pilot.pause(delay=0.5)

        assert snap_compare(
            MTGSpellbook(),
            run_before=enter_synergy_mode,
            terminal_size=(140, 45),
        )

    def test_collection_screen(self, snap_compare: Any) -> None:
        """Screenshot of the collection screen via menu navigation."""

        async def open_collection(pilot: Pilot[None]) -> None:
            await navigate_via_menu(pilot, MENU_COLLECTION, delay=2.0)
            # Allow widgets to be fully mounted and populated
            await pilot.pause(delay=0.5)
            # Debug: print current screen type
            screen = pilot.app.screen
            screen_type = type(screen).__name__
            assert "Collection" in screen_type, f"Expected Collection screen, got {screen_type}"

        assert snap_compare(
            MTGSpellbook(),
            run_before=open_collection,
            terminal_size=(140, 40),
        )

    def test_collection_screen_with_menu(self, snap_compare: Any) -> None:
        """Screenshot of collection screen with menu expanded."""

        async def open_collection_menu(pilot: Pilot[None]) -> None:
            await navigate_via_menu(pilot, MENU_COLLECTION, delay=0.5)
            # Open menu again on the collection screen
            await pilot.press("f10")
            await pilot.pause(delay=0.3)

        assert snap_compare(
            MTGSpellbook(),
            run_before=open_collection_menu,
            terminal_size=(140, 40),
        )

    @pytest.mark.skip(reason="Textual pilot times out with FullDeckScreen's complex widget tree")
    def test_decks_screen(self, snap_compare: Any) -> None:
        """Screenshot of the decks screen.

        Note: This test is skipped because Textual's pilot._wait_for_screen()
        times out with FullDeckScreen's complex widget tree. The screen itself
        works correctly - verified via direct action call tests and manual testing.
        The timeout is a limitation of the testing framework, not the screen.
        """
        import asyncio

        async def open_decks(pilot: Pilot[None]) -> None:
            await asyncio.sleep(0.5)

            # Use direct action call instead of menu navigation
            pilot.app.action_browse_decks()  # type: ignore[attr-defined]
            await asyncio.sleep(1.5)

            # Verify deck screen loaded
            from mtg_spellbook.deck.full_screen import FullDeckScreen

            screen = pilot.app.screen
            assert isinstance(screen, FullDeckScreen), (
                f"Expected FullDeckScreen, got {type(screen).__name__}"
            )

        assert snap_compare(
            MTGSpellbook(),
            run_before=open_decks,
            terminal_size=(140, 40),
        )

    @pytest.mark.skip(reason="Textual pilot times out with FullDeckScreen's complex widget tree")
    def test_decks_screen_with_menu(self, snap_compare: Any) -> None:
        """Screenshot of decks screen with menu expanded.

        Note: Skipped due to Textual pilot timeout - same issue as test_decks_screen.
        """
        import asyncio

        from textual.events import Key

        async def open_decks_menu(pilot: Pilot[None]) -> None:
            await asyncio.sleep(0.5)

            pilot.app.action_browse_decks()  # type: ignore[attr-defined]
            await asyncio.sleep(1.5)

            pilot.app.post_message(Key("f10", "f10"))
            await asyncio.sleep(0.5)

        assert snap_compare(
            MTGSpellbook(),
            run_before=open_decks_menu,
            terminal_size=(140, 40),
        )
