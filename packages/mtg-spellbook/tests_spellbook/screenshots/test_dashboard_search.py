"""Tests for dashboard search functionality.

Regression test for bug: when searching from the dashboard and selecting a card
from the dropdown, the search results page should open with that card selected.
"""

from __future__ import annotations

import asyncio

import pytest
from textual.widgets import ListView

from mtg_spellbook.app import MTGSpellbook
from mtg_spellbook.widgets import CardPanel


class TestDashboardSearch:
    """Tests for searching from the dashboard."""

    @pytest.mark.asyncio
    async def test_dashboard_search_selection_shows_specific_card(self) -> None:
        """Search for Lightning Bolt, select it, verify it's displayed.

        This test:
        1. Starts on dashboard (results container hidden)
        2. Types "Lightning Bolt" in dashboard search
        3. Selects from dropdown
        4. Verifies results container is visible
        5. Verifies the selected card name matches what was searched
        6. Verifies the card panel is showing content
        """
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.5)

            # Verify initial state - dashboard visible, results hidden
            dashboard = pilot.app.query_one("#dashboard")
            results_container = pilot.app.query_one("#results-container")
            detail_container = pilot.app.query_one("#detail-container")

            assert "hidden" not in dashboard.classes, "Dashboard should be visible on startup"
            assert "hidden" in results_container.classes, "Results should be hidden initially"
            assert "hidden" in detail_container.classes, "Detail should be hidden initially"

            # Type "Lightning Bolt" in the dashboard search bar
            for char in "Lightning Bolt":
                await pilot.press(char)
            await asyncio.sleep(1.0)  # Wait for typeahead dropdown to appear

            # Select the first result from the dropdown
            await pilot.press("down")
            await asyncio.sleep(0.2)
            await pilot.press("enter")
            await asyncio.sleep(2.0)  # Wait for card to load

            # Verify state changed - dashboard hidden, results visible
            dashboard = pilot.app.query_one("#dashboard")
            results_container = pilot.app.query_one("#results-container")
            detail_container = pilot.app.query_one("#detail-container")

            assert "hidden" in dashboard.classes, (
                f"Dashboard should be hidden after selecting card. "
                f"Dashboard classes: {dashboard.classes}"
            )
            assert "hidden" not in results_container.classes, (
                f"Results container should be visible after selecting card. "
                f"Results classes: {results_container.classes}"
            )
            assert "hidden" not in detail_container.classes, (
                f"Detail container should be visible after selecting card. "
                f"Detail classes: {detail_container.classes}"
            )

            # Verify the correct card is loaded
            current_card = pilot.app._current_card
            assert current_card is not None, "A card should be loaded after selection"
            assert "Lightning" in current_card.name or "Bolt" in current_card.name, (
                f"Expected Lightning Bolt or similar, got: {current_card.name}"
            )

            # Verify results list has the card
            results_list = pilot.app.query_one("#results-list", ListView)
            assert len(results_list.children) > 0, "Results list should have the selected card"

            # Verify card panel has content - check region has height
            card_panel = pilot.app.query_one("#card-panel", CardPanel)
            assert card_panel.region.height > 0, (
                f"Card panel should have height. Region: {card_panel.region}"
            )

    @pytest.mark.asyncio
    async def test_dashboard_search_submit_renders_results(self) -> None:
        """Submit search from dashboard, results page must render with results.

        This test verifies that pressing Enter to submit a search query
        from the dashboard shows the results page with search results.
        """
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.5)

            # Verify initial state
            dashboard = pilot.app.query_one("#dashboard")
            assert "hidden" not in dashboard.classes, "Dashboard should be visible on startup"

            # Type a search query and press Enter to submit
            for char in "goblin":
                await pilot.press(char)
            await asyncio.sleep(0.3)
            await pilot.press("enter")
            await asyncio.sleep(2.0)  # Wait for search results

            # Verify results container is visible
            results_container = pilot.app.query_one("#results-container")
            detail_container = pilot.app.query_one("#detail-container")

            assert "hidden" not in results_container.classes, (
                f"Results container should be visible after search submit. "
                f"Results classes: {results_container.classes}"
            )
            assert "hidden" not in detail_container.classes, (
                f"Detail container should be visible after search submit. "
                f"Detail classes: {detail_container.classes}"
            )

            # Results list should have items
            results_list = pilot.app.query_one("#results-list", ListView)
            assert len(results_list.children) > 0, (
                "Results list should have search results for 'goblin'"
            )

            # First card should be selected
            assert pilot.app._current_card is not None, "First search result should be selected"
