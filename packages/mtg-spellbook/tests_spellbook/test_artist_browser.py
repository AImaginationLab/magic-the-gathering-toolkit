"""Tests for ArtistBrowser widget."""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import patch

import pytest
from textual.app import App, ComposeResult
from textual.containers import Vertical

from mtg_core.data.models.responses import ArtistSummary
from mtg_spellbook.widgets.artist_browser import (
    ArtistBrowser,
    ArtistBrowserClosed,
    ArtistSelected,
)


def create_sample_artists() -> list[ArtistSummary]:
    """Create sample artists for testing."""
    return [
        ArtistSummary(
            name="Aaron Miller",
            card_count=23,
            sets_count=5,
            first_card_year=2010,
            most_recent_year=2023,
        ),
        ArtistSummary(
            name="Adam Paquette",
            card_count=187,
            sets_count=45,
            first_card_year=2012,
            most_recent_year=2024,
        ),
        ArtistSummary(
            name="Rebecca Guay",
            card_count=47,
            sets_count=18,
            first_card_year=1997,
            most_recent_year=2019,
        ),
        ArtistSummary(
            name="Rob Alexander",
            card_count=129,
            sets_count=30,
            first_card_year=1995,
            most_recent_year=2020,
        ),
        ArtistSummary(
            name="Zoltan Boros",
            card_count=85,
            sets_count=22,
            first_card_year=2008,
            most_recent_year=2024,
        ),
    ]


class ArtistBrowserTestApp(App[None]):
    """Test app with ArtistBrowser widget."""

    def compose(self) -> ComposeResult:
        with Vertical(id="main-container"):
            yield ArtistBrowser(id="artist-browser")


class TestArtistBrowserWidget:
    """Tests for ArtistBrowser widget functionality."""

    @pytest.mark.asyncio
    async def test_browser_loads_artists(self) -> None:
        """Test that browser correctly loads and displays artists."""
        async with ArtistBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)
            artists = create_sample_artists()

            await browser.load_artists(artists)

            assert browser.total_count == 5
            assert browser.filtered_count == 5
            assert len(browser._artists) == 5

    @pytest.mark.asyncio
    async def test_search_filters_artists(self) -> None:
        """Test that search correctly filters the artist list."""
        async with ArtistBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)
            artists = create_sample_artists()

            await browser.load_artists(artists)

            # Filter by "rebecca"
            filtered = browser._filter_artists("rebecca")
            assert len(filtered) == 1
            assert filtered[0].name == "Rebecca Guay"

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self) -> None:
        """Test that search is case-insensitive."""
        async with ArtistBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)
            artists = create_sample_artists()

            await browser.load_artists(artists)

            # Test various cases
            assert len(browser._filter_artists("REBECCA")) == 1
            assert len(browser._filter_artists("Rebecca")) == 1
            assert len(browser._filter_artists("rEbEcCa")) == 1

    @pytest.mark.asyncio
    async def test_empty_search_returns_all(self) -> None:
        """Test that empty search returns all artists."""
        async with ArtistBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)
            artists = create_sample_artists()

            await browser.load_artists(artists)

            filtered = browser._filter_artists("")
            assert len(filtered) == 5

    @pytest.mark.asyncio
    async def test_close_action_posts_message(self) -> None:
        """Test that close action posts ArtistBrowserClosed message."""

        class TestApp(App[None]):
            messages: ClassVar[list[ArtistBrowserClosed]] = []

            def compose(self) -> ComposeResult:
                with Vertical(id="main-container"):
                    yield ArtistBrowser(id="artist-browser")

            def on_artist_browser_closed(self, msg: ArtistBrowserClosed) -> None:
                TestApp.messages.append(msg)

        TestApp.messages = []  # Reset for this test
        async with TestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)

            browser.action_close()
            await pilot.pause()

            assert len(TestApp.messages) == 1

    @pytest.mark.asyncio
    async def test_get_current_artist(self) -> None:
        """Test getting the currently selected artist."""
        async with ArtistBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)
            artists = create_sample_artists()

            await browser.load_artists(artists)

            # First artist should be selected (Aaron Miller after sorting)
            current = browser.get_current_artist()
            assert current is not None
            assert current.name == "Aaron Miller"

    @pytest.mark.asyncio
    async def test_random_artist_selection(self) -> None:
        """Test random artist selection."""

        class TestApp(App[None]):
            messages: ClassVar[list[ArtistSelected]] = []

            def compose(self) -> ComposeResult:
                with Vertical(id="main-container"):
                    yield ArtistBrowser(id="artist-browser")

            def on_artist_selected(self, msg: ArtistSelected) -> None:
                TestApp.messages.append(msg)

        TestApp.messages = []  # Reset for this test
        async with TestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)
            artists = create_sample_artists()

            await browser.load_artists(artists)

            with patch("random.choice", return_value=artists[2]):
                browser.action_random_artist()
                await pilot.pause()

            assert len(TestApp.messages) == 1
            assert TestApp.messages[0].artist.name == "Rebecca Guay"

    @pytest.mark.asyncio
    async def test_focus_search_action(self) -> None:
        """Test that focus search action focuses the input."""
        async with ArtistBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)
            artists = create_sample_artists()

            await browser.load_artists(artists)

            browser.action_focus_search()
            await pilot.pause()

            from textual.widgets import Input

            search = browser.query_one("#artist-search", Input)
            assert search.has_focus

    @pytest.mark.asyncio
    async def test_header_updates_with_search(self) -> None:
        """Test that header updates to show filter count when searching."""
        async with ArtistBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)
            artists = create_sample_artists()

            await browser.load_artists(artists)

            # Simulate search
            browser.search_query = "rebecca"
            browser._filtered_artists = browser._filter_artists("rebecca")
            browser.filtered_count = len(browser._filtered_artists)

            header = browser._render_header()
            assert "showing 1 of 5" in header

    @pytest.mark.asyncio
    async def test_navigation_skips_headers(self) -> None:
        """Test that navigation up/down skips letter headers."""
        async with ArtistBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)
            artists = create_sample_artists()

            await browser.load_artists(artists)

            # Navigate down multiple times and ensure we stay on artist items
            from textual.widgets import ListView

            from mtg_spellbook.widgets.artist_browser.widget import ArtistListItem

            artist_list = browser.query_one("#artist-list", ListView)

            browser.action_nav_down()
            await pilot.pause()

            # Should be on an ArtistListItem, not a header
            if artist_list.index is not None:
                item = artist_list.children[artist_list.index]
                assert isinstance(item, ArtistListItem)


class TestArtistBrowserMessages:
    """Tests for ArtistBrowser message handling."""

    @pytest.mark.asyncio
    async def test_select_artist_posts_message(self) -> None:
        """Test that selecting an artist posts ArtistSelected message."""

        class TestApp(App[None]):
            messages: ClassVar[list[ArtistSelected]] = []

            def compose(self) -> ComposeResult:
                with Vertical(id="main-container"):
                    yield ArtistBrowser(id="artist-browser")

            def on_artist_selected(self, msg: ArtistSelected) -> None:
                TestApp.messages.append(msg)

        TestApp.messages = []  # Reset for this test
        async with TestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)
            artists = create_sample_artists()

            await browser.load_artists(artists)

            browser.action_select_artist()
            await pilot.pause()

            assert len(TestApp.messages) == 1
            # First artist alphabetically
            assert TestApp.messages[0].artist.name == "Aaron Miller"


class TestArtistBrowserEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_artist_list(self) -> None:
        """Test browser with empty artist list."""
        async with ArtistBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)

            await browser.load_artists([])

            assert browser.total_count == 0
            assert browser.filtered_count == 0
            assert browser.get_current_artist() is None

    @pytest.mark.asyncio
    async def test_random_on_empty_list(self) -> None:
        """Test random action with empty list does not crash."""
        async with ArtistBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)

            await browser.load_artists([])

            # Should not raise
            browser.action_random_artist()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_search_no_results(self) -> None:
        """Test search with no matching results."""
        async with ArtistBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)
            artists = create_sample_artists()

            await browser.load_artists(artists)

            filtered = browser._filter_artists("nonexistent artist xyz")
            assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_artist_with_special_characters(self) -> None:
        """Test handling of artist names with special characters."""
        async with ArtistBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#artist-browser", ArtistBrowser)

            artists = [
                ArtistSummary(
                    name="D. Alexander Gregory",
                    card_count=10,
                    sets_count=3,
                    first_card_year=1995,
                    most_recent_year=1998,
                ),
            ]

            await browser.load_artists(artists)

            assert browser.total_count == 1
            # Verify artist was loaded (no letter positions feature anymore)
            assert len(browser._artists) == 1
            assert browser._artists[0].name == "D. Alexander Gregory"
