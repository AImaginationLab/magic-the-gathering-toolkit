"""Layout tests for DeckSuggestionsScreen.

Tests verify that UI elements render with proper dimensions.
Uses the real MTGSpellbook app to ensure proper CSS and styles.
"""

from __future__ import annotations

import asyncio

import pytest
from textual.widgets import Button, ListView, Static

from mtg_spellbook.app import MTGSpellbook
from mtg_spellbook.collection.deck_suggestions_screen import (
    CollectionCardInfo,
    DeckSuggestionsScreen,
)


def _create_mock_cards(count: int = 50) -> list[CollectionCardInfo]:
    """Create mock card data for testing."""
    return [
        CollectionCardInfo(
            name=f"Test Card {i}",
            type_line="Legendary Creature - Test" if i < 5 else "Creature - Test",
            colors=["W"] if i % 2 == 0 else ["U"],
            mana_cost="{2}{W}" if i % 2 == 0 else "{1}{U}",
            color_identity=["W"] if i % 2 == 0 else ["U"],
        )
        for i in range(count)
    ]


class TestDeckSuggestionsLayout:
    """Tests for DeckSuggestionsScreen layout - elements must have proper dimensions."""

    @pytest.mark.asyncio
    async def test_format_buttons_have_height(self) -> None:
        """Format buttons (Commander/Standard) must be visible with non-zero height."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.3)

            # Push the DeckSuggestionsScreen
            mock_cards = _create_mock_cards(50)
            app.push_screen(DeckSuggestionsScreen(mock_cards))
            await asyncio.sleep(0.5)

            # Find the format buttons on the current screen
            screen = pilot.app.screen
            cmd_btn = screen.query_one("#btn-commander", Button)
            std_btn = screen.query_one("#btn-standard", Button)

            # Both buttons must have non-zero height (visible)
            assert cmd_btn.region.height > 0, f"Commander button has zero height: {cmd_btn.region}"
            assert std_btn.region.height > 0, f"Standard button has zero height: {std_btn.region}"

    @pytest.mark.asyncio
    async def test_suggestions_list_has_height(self) -> None:
        """ListView must have substantial height to show suggestions."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.3)

            mock_cards = _create_mock_cards(50)
            app.push_screen(DeckSuggestionsScreen(mock_cards))
            await asyncio.sleep(0.5)

            screen = pilot.app.screen
            list_view = screen.query_one("#suggestions-list", ListView)

            # ListView must have substantial height (at least 10 rows for content)
            assert list_view.region.height >= 10, (
                f"ListView height too small: {list_view.region.height}. "
                f"Expected >= 10. Full region: {list_view.region}"
            )

    @pytest.mark.asyncio
    async def test_statusbar_visible_at_bottom(self) -> None:
        """Statusbar must be visible at the bottom of the screen."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.3)

            mock_cards = _create_mock_cards(50)
            app.push_screen(DeckSuggestionsScreen(mock_cards))
            await asyncio.sleep(0.5)

            screen = pilot.app.screen
            statusbar = screen.query_one("#suggestions-statusbar", Static)

            # Statusbar must have non-zero height
            assert statusbar.region.height > 0, f"Statusbar has zero height: {statusbar.region}"

            # Statusbar should be near the bottom of the screen (within 5 rows of bottom)
            screen_height = 40
            statusbar_bottom = statusbar.region.y + statusbar.region.height
            assert statusbar_bottom >= screen_height - 5, (
                f"Statusbar not at bottom. Statusbar bottom: {statusbar_bottom}, "
                f"Screen height: {screen_height}"
            )

    @pytest.mark.asyncio
    async def test_all_elements_in_proper_vertical_order(self) -> None:
        """Elements should be stacked: header -> format-bar -> list -> statusbar."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await asyncio.sleep(0.3)

            mock_cards = _create_mock_cards(50)
            app.push_screen(DeckSuggestionsScreen(mock_cards))
            await asyncio.sleep(0.5)

            screen = pilot.app.screen
            header = screen.query_one("#suggestions-header", Static)
            cmd_btn = screen.query_one("#btn-commander", Button)
            list_view = screen.query_one("#suggestions-list", ListView)
            statusbar = screen.query_one("#suggestions-statusbar", Static)

            # Verify vertical ordering
            assert header.region.y < cmd_btn.region.y, (
                f"Header (y={header.region.y}) should be above format button (y={cmd_btn.region.y})"
            )
            assert cmd_btn.region.y < list_view.region.y, (
                f"Format button (y={cmd_btn.region.y}) should be above list (y={list_view.region.y})"
            )
            assert list_view.region.y < statusbar.region.y, (
                f"List (y={list_view.region.y}) should be above statusbar (y={statusbar.region.y})"
            )
