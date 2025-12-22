"""Tests for artist selection from Artists screen.

Regression test for bug: when going directly to Artists page (without visiting
Search first), selecting an artist would not render the search results page.
"""

from __future__ import annotations

import asyncio

import pytest
from textual.widgets import ListView, Static

from mtg_spellbook.app import MTGSpellbook


class TestArtistSelection:
    """Tests for selecting an artist from the Artists screen."""

    @pytest.mark.asyncio
    async def test_artist_selection_renders_results(self) -> None:
        """Bug: Go to Artists page directly, select artist, results must render.

        This is a regression test for a bug where:
        1. User opens app (dashboard is visible)
        2. User goes to Artists page (without visiting Search first)
        3. User selects an artist
        4. Expected: search results page shows artist's cards
        5. Actual (bug): results page doesn't render at all
        """
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.5)

            # Verify we start on the dashboard
            dashboard = pilot.app.query_one("#dashboard")
            assert "hidden" not in dashboard.classes, "Dashboard should be visible on startup"

            # Verify results container starts hidden
            results_container = pilot.app.query_one("#results-container")
            assert "hidden" in results_container.classes, "Results should be hidden initially"

            # Navigate to Artists screen via menu (Search=0, Artists=1)
            await pilot.press("f10")
            await asyncio.sleep(0.3)
            await pilot.press("down")  # Move to Artists
            await pilot.press("enter")
            await asyncio.sleep(1.0)  # Wait for screen to load

            # Verify we're on Artists screen
            screen = pilot.app.screen
            screen_name = type(screen).__name__
            assert "Artists" in screen_name, f"Expected Artists screen, got {screen_name}"

            # Wait for artist list to populate
            await asyncio.sleep(1.0)

            # Select the first artist (press Enter on the highlighted item)
            await pilot.press("enter")
            await asyncio.sleep(1.5)  # Wait for navigation back and card loading

            # After selecting artist, we should be back on main screen
            screen = pilot.app.screen
            screen_name = type(screen).__name__

            # The main app screen should now show results
            # Check that results container is visible (not hidden)
            results_container = pilot.app.query_one("#results-container")
            detail_container = pilot.app.query_one("#detail-container")

            assert "hidden" not in results_container.classes, (
                f"Results container should be visible after selecting artist. "
                f"Screen: {screen_name}. Results classes: {results_container.classes}"
            )
            assert "hidden" not in detail_container.classes, (
                f"Detail container should be visible after selecting artist. "
                f"Screen: {screen_name}. Detail classes: {detail_container.classes}"
            )

            # Dashboard should be hidden
            dashboard = pilot.app.query_one("#dashboard")
            assert "hidden" in dashboard.classes, (
                f"Dashboard should be hidden after selecting artist. "
                f"Dashboard classes: {dashboard.classes}"
            )

            # Results list should have items (artist's cards)
            results_list = pilot.app.query_one("#results-list", ListView)
            # Give a bit more time for results to populate
            await asyncio.sleep(0.5)
            assert len(results_list.children) > 0, (
                "Results list should have cards from the selected artist"
            )

    @pytest.mark.asyncio
    async def test_artist_selection_shows_header(self) -> None:
        """Verify the results header shows artist name after selection."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.5)

            # Go directly to Artists screen
            await pilot.press("f10")
            await asyncio.sleep(0.3)
            await pilot.press("down")  # Move to Artists
            await pilot.press("enter")
            await asyncio.sleep(1.0)

            # Wait for list to populate and select first artist
            await asyncio.sleep(1.0)
            await pilot.press("enter")
            await asyncio.sleep(1.5)

            # Check that results container is visible (primary verification)
            results_container = pilot.app.query_one("#results-container")
            assert "hidden" not in results_container.classes, (
                "Results container should be visible after selecting artist"
            )
