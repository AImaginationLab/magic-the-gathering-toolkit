"""User flow tests that mimic real user behavior.

These tests verify complete user journeys through the application,
capturing screenshots at key transition points to ensure the UI
responds correctly to user actions.

Run with: uv run pytest packages/mtg-spellbook/tests/screenshots/test_user_flows.py -v
Update snapshots: uv run pytest packages/mtg-spellbook/tests/screenshots/test_user_flows.py --snapshot-update
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from mtg_spellbook.app import MTGSpellbook

from .conftest import MENU_ARTISTS, navigate_via_menu

if TYPE_CHECKING:
    from textual.pilot import Pilot


# Only import for snapshot tests (these require pytest-textual-snapshot)
try:
    pytest.importorskip("pytest_textual_snapshot")
    _HAS_SNAPSHOT_SUPPORT = True
except pytest.skip.Exception:
    _HAS_SNAPSHOT_SUPPORT = False


@pytest.mark.skipif(not _HAS_SNAPSHOT_SUPPORT, reason="pytest-textual-snapshot not installed")
@pytest.mark.usefixtures("mock_database_for_snapshots")
class TestUserFlowScreenshots:
    """User flow tests that mimic real user behavior.

    These tests use mock database data for deterministic snapshots.
    """

    def test_artist_flow_open_browser(self, snap_compare: Any) -> None:
        """Step 1: User opens the Artists browser via menu."""

        async def open_artists_browser(pilot: Pilot[None]) -> None:
            await navigate_via_menu(pilot, MENU_ARTISTS, delay=0.5)
            await pilot.pause(delay=0.3)

            # Verify we're on the Artists screen
            from mtg_spellbook.screens import ArtistsScreen

            screen = pilot.app.screen
            assert isinstance(screen, ArtistsScreen), (
                f"Expected ArtistsScreen, got {type(screen).__name__}"
            )

        assert snap_compare(
            MTGSpellbook(),
            run_before=open_artists_browser,
            terminal_size=(120, 40),
        )

    def test_artist_flow_navigate_list(self, snap_compare: Any) -> None:
        """Step 2: User navigates down in the artist list to find an artist."""

        async def navigate_artist_list(pilot: Pilot[None]) -> None:
            await navigate_via_menu(pilot, MENU_ARTISTS, delay=0.5)
            await pilot.pause(delay=0.3)

            # Navigate down a few items to show list navigation
            for _ in range(3):
                await pilot.press("down")
                await pilot.pause(delay=0.1)

        assert snap_compare(
            MTGSpellbook(),
            run_before=navigate_artist_list,
            terminal_size=(120, 40),
        )

    @pytest.mark.asyncio
    async def test_artist_flow_select_artist(self) -> None:
        """Step 3: User selects an artist and sees their cards in results.

        Note: This test verifies behavior functionally rather than via snapshot
        because the card results are inherently non-deterministic (card order,
        scroll position, etc.). The functional assertions validate the flow.
        """
        import asyncio

        app = MTGSpellbook()
        async with app.run_test(size=(140, 45)) as pilot:
            await navigate_via_menu(pilot, MENU_ARTISTS, delay=0.5)
            await pilot.pause(delay=0.3)

            # Navigate down a few items
            for _ in range(2):
                await pilot.press("down")
                await pilot.pause(delay=0.1)

            # Select the artist (Enter key)
            await pilot.press("enter")

            # Wait for cards to load and screen to transition
            await asyncio.sleep(1.5)

            # Verify we're back on main screen (not ArtistsScreen anymore)
            from mtg_spellbook.screens import ArtistsScreen

            screen = pilot.app.screen
            # Should NOT be on ArtistsScreen after selection
            assert not isinstance(screen, ArtistsScreen), (
                "Should have dismissed ArtistsScreen after selection"
            )

            # Verify results are visible
            from mtg_spellbook.widgets import ResultsList

            results = pilot.app.query_one("#results-list", ResultsList)
            # Should have cards from the artist
            assert len(results.children) > 0, "Results list should contain artist's cards"

    def test_artist_flow_view_card_from_results(self, snap_compare: Any) -> None:
        """Step 4: User views a card from the artist's search results."""
        import asyncio

        async def view_artist_card(pilot: Pilot[None]) -> None:
            await navigate_via_menu(pilot, MENU_ARTISTS, delay=0.5)
            await pilot.pause(delay=0.5)

            # Navigate down and select an artist
            for _ in range(2):
                await pilot.press("down")
                await pilot.pause(delay=0.2)
            await pilot.press("enter")
            await asyncio.sleep(2.0)

            # Navigate to a specific card in results
            for _ in range(3):
                await pilot.press("down")
                await pilot.pause(delay=0.3)

            # Wait for card panel to update
            await pilot.pause(delay=0.5)

            # Card panel should update with the selected card
            from mtg_spellbook.widgets import CardPanel

            panel = pilot.app.query_one("#card-panel", CardPanel)
            # Panel should have content
            assert panel is not None, "Card panel should exist"

        assert snap_compare(
            MTGSpellbook(),
            run_before=view_artist_card,
            terminal_size=(140, 45),
        )


class TestUserFlowFunctional:
    """Functional tests for user flows that verify behavior without screenshots.

    These tests ensure the application responds correctly to user actions
    even when we can't capture visual snapshots.
    """

    @pytest.mark.asyncio
    async def test_artist_selection_loads_cards(self) -> None:
        """Verify selecting an artist loads their cards into results."""
        import asyncio

        from mtg_spellbook.screens import ArtistsScreen
        from mtg_spellbook.widgets import ResultsList

        app = MTGSpellbook()
        async with app.run_test(size=(140, 45)) as pilot:
            await asyncio.sleep(0.5)

            # Open Artists screen via menu (Search=0, Artists=1)
            await pilot.press("f10")
            await asyncio.sleep(0.3)
            await pilot.press("down")  # Navigate past Search to Artists
            await pilot.press("enter")
            await asyncio.sleep(0.5)

            # Verify we're on Artists screen
            assert isinstance(pilot.app.screen, ArtistsScreen), (
                f"Expected ArtistsScreen, got {type(pilot.app.screen).__name__}"
            )

            # Navigate down to an artist
            for _ in range(2):
                await pilot.press("down")
                await asyncio.sleep(0.1)

            # Select the artist
            await pilot.press("enter")
            await asyncio.sleep(2.0)  # Wait for cards to load

            # Verify we're back on main screen
            assert not isinstance(pilot.app.screen, ArtistsScreen), (
                "Should have dismissed ArtistsScreen after selection"
            )

            # Verify results list has cards
            results = pilot.app.query_one("#results-list", ResultsList)
            assert len(results.children) > 0, (
                f"Results should contain cards, but found {len(results.children)} items"
            )

            # Verify artist mode is active
            assert pilot.app._artist_mode, "App should be in artist mode"

    @pytest.mark.asyncio
    async def test_artist_random_selection_loads_cards(self) -> None:
        """Verify pressing 'r' for random artist loads their cards."""
        import asyncio

        from mtg_spellbook.screens import ArtistsScreen
        from mtg_spellbook.widgets import ResultsList

        app = MTGSpellbook()
        async with app.run_test(size=(140, 45)) as pilot:
            await asyncio.sleep(0.5)

            # Open Artists screen via menu (Search=0, Artists=1)
            await pilot.press("f10")
            await asyncio.sleep(0.3)
            await pilot.press("down")  # Navigate past Search to Artists
            await pilot.press("enter")
            await asyncio.sleep(0.5)

            # Verify we're on Artists screen
            assert isinstance(pilot.app.screen, ArtistsScreen), (
                f"Expected ArtistsScreen, got {type(pilot.app.screen).__name__}"
            )

            # Press 'r' for random artist
            await pilot.press("r")
            await asyncio.sleep(2.0)  # Wait for cards to load

            # Verify we're back on main screen
            assert not isinstance(pilot.app.screen, ArtistsScreen), (
                "Should have dismissed ArtistsScreen after random selection"
            )

            # Verify results list has cards
            results = pilot.app.query_one("#results-list", ResultsList)
            assert len(results.children) > 0, (
                f"Results should contain cards, but found {len(results.children)} items"
            )

    @pytest.mark.asyncio
    async def test_set_selection_shows_cards(self) -> None:
        """Verify selecting a set shows its cards within the Sets screen."""
        import asyncio

        from mtg_spellbook.screens import SetsScreen

        app = MTGSpellbook()
        async with app.run_test(size=(140, 45)) as pilot:
            await asyncio.sleep(0.5)

            # Open Sets screen via menu (Search=0, Artists=1, Sets=2)
            await pilot.press("f10")
            await asyncio.sleep(0.3)
            await pilot.press("down")  # Navigate past Search
            await pilot.press("down")  # Navigate past Artists to Sets
            await pilot.press("enter")
            await asyncio.sleep(0.5)

            # Verify we're on Sets screen
            assert isinstance(pilot.app.screen, SetsScreen), (
                f"Expected SetsScreen, got {type(pilot.app.screen).__name__}"
            )

            # Navigate down to a set
            for _ in range(3):
                await pilot.press("down")
                await asyncio.sleep(0.1)

            # Select the set - this shows details within the Sets screen
            await pilot.press("enter")
            await asyncio.sleep(1.0)

            # Still on Sets screen but now showing set details
            assert isinstance(pilot.app.screen, SetsScreen), (
                "Should still be on SetsScreen showing set details"
            )

    @pytest.mark.asyncio
    async def test_search_returns_results(self) -> None:
        """Verify searching for a card returns results."""
        import asyncio

        from mtg_spellbook.widgets import ResultsList

        app = MTGSpellbook()
        async with app.run_test(size=(140, 45)) as pilot:
            await asyncio.sleep(0.5)

            # Focus search and type query
            await pilot.press("escape")
            await asyncio.sleep(0.1)
            for char in "sol ring":
                await pilot.press(char)
            await pilot.press("enter")
            await asyncio.sleep(1.5)

            # Verify results
            results = pilot.app.query_one("#results-list", ResultsList)
            assert len(results.children) > 0, "Search should return results"

            # Verify a card is selected
            assert pilot.app._current_card is not None, "Should have a current card selected"
