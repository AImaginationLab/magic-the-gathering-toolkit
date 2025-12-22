"""Tests for Dashboard V4 widget (interactive dashboard)."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock

import pytest
from textual.app import App, ComposeResult
from textual.containers import Vertical

from mtg_core.data.database import UnifiedDatabase
from mtg_core.data.models.responses import ArtistSummary
from mtg_spellbook.widgets.dashboard import (
    Dashboard,
    DashboardAction,
    QuickLinksBar,
    SearchBar,
)
from mtg_spellbook.widgets.dashboard.widget import ArtistSpotlight


def create_sample_artist() -> ArtistSummary:
    """Create a sample artist for testing."""
    return ArtistSummary(
        name="Rebecca Guay",
        card_count=47,
        sets_count=18,
        first_card_year=1997,
        most_recent_year=2019,
    )


def create_mock_database() -> AsyncMock:
    """Create a mock database for testing dashboard queries."""
    mock_db = AsyncMock()
    mock_db.get_random_artist_for_spotlight = AsyncMock(return_value=create_sample_artist())
    return mock_db


class DashboardTestApp(App[None]):
    """Test app with Dashboard widget."""

    def compose(self) -> ComposeResult:
        with Vertical(id="main-container"):
            yield Dashboard(id="dashboard")


class TestDashboardV4Widget:
    """Tests for Dashboard V4 widget functionality."""

    @pytest.mark.asyncio
    async def test_dashboard_renders_components(self) -> None:
        """Test that dashboard renders all required components."""
        async with DashboardTestApp().run_test() as pilot:
            dashboard = pilot.app.query_one("#dashboard", Dashboard)

            # V4 uses: QuickLinksBar, SearchBar, ArtistSpotlight
            assert dashboard.query_one("#quick-links-bar", QuickLinksBar)
            assert dashboard.query_one("#dashboard-search-bar", SearchBar)
            assert dashboard.query_one("#artist-spotlight-content", ArtistSpotlight)

    @pytest.mark.asyncio
    async def test_dashboard_is_not_focusable(self) -> None:
        """Test that dashboard container is not focusable."""
        async with DashboardTestApp().run_test() as pilot:
            dashboard = pilot.app.query_one("#dashboard", Dashboard)

            # Dashboard container can_focus=False (children are focusable)
            assert dashboard.can_focus is False

    @pytest.mark.asyncio
    async def test_dashboard_set_database(self) -> None:
        """Test that set_database() stores database reference."""
        async with DashboardTestApp().run_test() as pilot:
            dashboard = pilot.app.query_one("#dashboard", Dashboard)
            mock_db = create_mock_database()

            dashboard.set_database(cast(UnifiedDatabase, mock_db))

            # Verify database is stored
            assert dashboard._db == mock_db

    @pytest.mark.asyncio
    async def test_dashboard_loads_data_from_database(self) -> None:
        """Test that dashboard loads data from database correctly."""
        async with DashboardTestApp().run_test() as pilot:
            dashboard = pilot.app.query_one("#dashboard", Dashboard)
            mock_db = create_mock_database()

            dashboard.set_database(cast(UnifiedDatabase, mock_db))
            dashboard.load_dashboard()

            # Wait for the worker to complete
            await pilot.pause()
            await pilot.pause()  # Double pause to ensure async work completes

            # Verify database methods were called
            mock_db.get_random_artist_for_spotlight.assert_called_once()

    @pytest.mark.asyncio
    async def test_dashboard_clear_resets_state(self) -> None:
        """Test that clear resets dashboard state."""
        async with DashboardTestApp().run_test() as pilot:
            dashboard = pilot.app.query_one("#dashboard", Dashboard)

            # Set some state
            dashboard._artist = create_sample_artist()
            dashboard.is_loading = False

            # Clear
            dashboard.clear()

            # Verify cleared
            assert dashboard._artist is None
            assert dashboard.is_loading is True

    @pytest.mark.asyncio
    async def test_dashboard_loading_state(self) -> None:
        """Test that dashboard tracks loading state."""
        async with DashboardTestApp().run_test() as pilot:
            dashboard = pilot.app.query_one("#dashboard", Dashboard)

            # Initial state is loading
            assert dashboard.is_loading is True


class TestDashboardActionMessage:
    """Tests for DashboardAction message."""

    @pytest.mark.asyncio
    async def test_dashboard_action_message_creation(self) -> None:
        """Test DashboardAction message can be created with action types."""
        # Test each action type
        msg_artists = DashboardAction("artists")
        assert msg_artists.action == "artists"

        msg_sets = DashboardAction("sets")
        assert msg_sets.action == "sets"

        msg_decks = DashboardAction("decks")
        assert msg_decks.action == "decks"

        msg_random = DashboardAction("random")
        assert msg_random.action == "random"


class TestDashboardArtistSpotlight:
    """Tests for artist spotlight rendering."""

    @pytest.mark.asyncio
    async def test_artist_spotlight_internal_render(self) -> None:
        """Test that _update_artist_spotlight updates the Static widget."""
        async with DashboardTestApp().run_test() as pilot:
            dashboard = pilot.app.query_one("#dashboard", Dashboard)
            artist = create_sample_artist()

            # Set artist state and call internal update method
            dashboard._artist = artist
            dashboard._update_artist_spotlight(artist)

            # Verify state was set
            assert dashboard._artist.name == "Rebecca Guay"

            # Verify spotlight widget exists and can be queried
            spotlight = dashboard.query_one("#artist-spotlight-content", ArtistSpotlight)
            assert spotlight is not None


class TestDashboardMessagePassing:
    """Tests for dashboard message passing (critical bug fix verification)."""

    @pytest.mark.asyncio
    async def test_quick_link_button_posts_correct_message_type(self) -> None:
        """Test that QuickLinkButton posts the message from messages.py, not a local copy."""
        from mtg_spellbook.widgets.dashboard import QuickLinkActivated
        from mtg_spellbook.widgets.dashboard.messages import (
            QuickLinkActivated as MessagesQuickLinkActivated,
        )

        # The import from dashboard should be the SAME class as from messages
        assert QuickLinkActivated is MessagesQuickLinkActivated

    @pytest.mark.asyncio
    async def test_search_bar_posts_correct_message_types(self) -> None:
        """Test that SearchBar posts messages from messages.py, not local copies."""
        from mtg_spellbook.widgets.dashboard import (
            SearchResultSelected,
            SearchSubmitted,
        )
        from mtg_spellbook.widgets.dashboard.messages import (
            SearchResultSelected as MessagesSearchResultSelected,
        )
        from mtg_spellbook.widgets.dashboard.messages import (
            SearchSubmitted as MessagesSearchSubmitted,
        )

        # The imports from dashboard should be the SAME classes as from messages
        assert SearchResultSelected is MessagesSearchResultSelected
        assert SearchSubmitted is MessagesSearchSubmitted

    @pytest.mark.asyncio
    async def test_quick_link_button_click_posts_message(self) -> None:
        """Test that clicking a QuickLinkButton posts QuickLinkActivated message."""
        from textual.app import App

        from mtg_spellbook.widgets.dashboard import QuickLinkActivated, QuickLinkButton

        received_messages: list[QuickLinkActivated] = []

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield QuickLinkButton("Artists", "artists", "a", id="test-btn")

            def on_quick_link_activated(self, event: QuickLinkActivated) -> None:
                received_messages.append(event)

        async with TestApp().run_test() as pilot:
            btn = pilot.app.query_one("#test-btn", QuickLinkButton)
            await pilot.click(btn)

            assert len(received_messages) == 1
            assert received_messages[0].action == "artists"

    @pytest.mark.asyncio
    async def test_quick_link_button_enter_posts_message(self) -> None:
        """Test that pressing Enter on a focused QuickLinkButton posts message."""
        from textual.app import App

        from mtg_spellbook.widgets.dashboard import QuickLinkActivated, QuickLinkButton

        received_messages: list[QuickLinkActivated] = []

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield QuickLinkButton("Sets", "sets", "s", id="test-btn")

            def on_quick_link_activated(self, event: QuickLinkActivated) -> None:
                received_messages.append(event)

        async with TestApp().run_test() as pilot:
            btn = pilot.app.query_one("#test-btn", QuickLinkButton)
            btn.focus()
            await pilot.press("enter")

            assert len(received_messages) == 1
            assert received_messages[0].action == "sets"
