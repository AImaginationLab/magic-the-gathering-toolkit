"""Tests for the Help Screen / Knowledge Base.

These tests verify:
1. Tab navigation works correctly to reach the search input
2. Keyword search filters results
3. Topic selection switches content panels
"""

from __future__ import annotations

import pytest

from mtg_spellbook.app import MTGSpellbook


class TestHelpScreenNavigation:
    """Test Tab navigation and focus management in the Help Screen."""

    @pytest.mark.asyncio
    async def test_tab_reaches_search_input(self) -> None:
        """Tab from topics list should reach the search input.

        User flow:
        1. Start on dashboard
        2. Press Ctrl+H to open help screen
        3. Tab should cycle through focusable widgets including search
        """
        from textual.widgets import Input

        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            # Open help screen via Ctrl+H
            await pilot.press("ctrl+h")
            await pilot.pause()

            # Verify we're on the help screen
            from mtg_spellbook.screens.help import HelpScreen

            assert isinstance(pilot.app.screen, HelpScreen), (
                f"Expected HelpScreen, got {type(pilot.app.screen).__name__}"
            )

            # Get the search input
            search_input = pilot.app.screen.query_one("#keyword-search", Input)

            # Tab multiple times to find the search input
            max_tabs = 10
            found_search = False
            for _ in range(max_tabs):
                await pilot.press("tab")
                await pilot.pause()

                # Check if search input has focus
                if search_input.has_focus:
                    found_search = True
                    break

            assert found_search, (
                f"Tab did not reach search input after {max_tabs} presses. "
                f"Current focus: {pilot.app.focused}"
            )

    @pytest.mark.asyncio
    async def test_slash_focuses_search(self) -> None:
        """Pressing / should focus the search input directly."""
        from textual.widgets import Input

        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            # Open help screen
            await pilot.press("ctrl+h")
            await pilot.pause()

            # Press / to focus search
            await pilot.press("/")
            await pilot.pause()

            # Verify search input has focus
            search_input = pilot.app.screen.query_one("#keyword-search", Input)
            assert search_input.has_focus, (
                f"Expected search input to have focus after /, but focus is on: {pilot.app.focused}"
            )


class TestKeywordSearchFiltering:
    """Test that keyword search correctly filters the list."""

    @pytest.mark.asyncio
    async def test_search_directly_filters_list(self) -> None:
        """Test that calling the filter directly works.

        This tests the filtering logic without going through the debounced path,
        which is hard to test with Textual's pilot due to async task timing.
        """
        from textual.widgets import ListView

        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            # Open help screen
            await pilot.press("ctrl+h")
            await pilot.pause()
            await pilot.pause()  # Wait for data load

            from mtg_spellbook.screens.help import HelpScreen, KeywordGlossary

            screen = pilot.app.screen
            assert isinstance(screen, HelpScreen)

            # Get widgets
            glossary = screen.query_one("#keyword-glossary", KeywordGlossary)
            keyword_list = screen.query_one("#keyword-list", ListView)

            # Verify keywords are loaded
            assert len(glossary.keywords) > 0, "Keywords should be loaded"

            # Get initial count
            initial_count = len(list(keyword_list.children))
            assert initial_count > 0, "Keyword list should have items initially"

            # Directly set search_query and call filter (bypasses debounce)
            glossary.search_query = "flying"
            glossary._filter_and_display()
            await pilot.pause()

            # Verify filtering occurred
            filtered_count = len(list(keyword_list.children))
            assert filtered_count < initial_count, (
                f"Filtered count ({filtered_count}) should be less than initial ({initial_count})"
            )

            # Verify Flying is in the filtered results
            found_flying = False
            for item in keyword_list.children:
                if item.id and "flying" in item.id.lower():
                    found_flying = True
                    break

            assert found_flying, (
                f"Flying keyword should be in filtered results. "
                f"Found items: {[i.id for i in list(keyword_list.children)[:5]]}"
            )


class TestTopicSwitching:
    """Test that selecting topics switches the middle panel."""

    @pytest.mark.asyncio
    async def test_topic_keywords_shows_keyword_glossary(self) -> None:
        """Test that Keywords topic shows the KeywordGlossary panel."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            # Open help screen
            await pilot.press("ctrl+h")
            await pilot.pause()

            from mtg_spellbook.screens.help import HelpScreen

            screen = pilot.app.screen
            assert isinstance(screen, HelpScreen)

            # Default topic should be keywords
            assert screen.current_topic == "keywords"

            # Keyword glossary should be visible
            keyword_glossary = screen.query_one("#keyword-glossary")
            assert not keyword_glossary.has_class("hidden")

    @pytest.mark.asyncio
    async def test_topic_switch_hides_keyword_glossary(self) -> None:
        """Test that switching topics hides the keyword glossary."""
        app = MTGSpellbook()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            # Open help screen
            await pilot.press("ctrl+h")
            await pilot.pause()

            from mtg_spellbook.screens.help import HelpScreen

            screen = pilot.app.screen
            assert isinstance(screen, HelpScreen)

            # Switch to concepts topic
            screen.current_topic = "concepts"
            await pilot.pause()

            # Keyword glossary should be hidden
            keyword_glossary = screen.query_one("#keyword-glossary")
            assert keyword_glossary.has_class("hidden")

            # Concepts glossary should be visible
            concepts_glossary = screen.query_one("#concepts-glossary")
            assert concepts_glossary.has_class("visible")
