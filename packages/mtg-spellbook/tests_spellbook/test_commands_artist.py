"""Tests for artist commands mixin."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from mtg_core.data.models.responses import (
    ArtistCardsResult,
    ArtistSummary,
    CardDetail,
    CardSummary,
    Prices,
)


@pytest.fixture
def sample_artist_cards() -> list[CardSummary]:
    """Sample cards by an artist."""
    cards = []
    for i in range(75):
        cards.append(
            CardSummary(
                uuid=f"artist-uuid-{i}",
                name=f"Artist Card {i}",
                mana_cost="{1}{U}",
                type="Creature",
                colors=["U"],
                rarity="common" if i % 2 == 0 else "rare",
                set_code="TST",
                collector_number=str(i),
            )
        )
    return cards


@pytest.fixture
def sample_artist_detail() -> CardDetail:
    """Sample card detail for artist card."""
    return CardDetail(
        uuid="artist-card-uuid",
        name="Test Artist Card",
        mana_cost="{2}{U}",
        type="Creature — Human",
        text="Test",
        power="2",
        toughness="2",
        colors=["U"],
        color_identity=["U"],
        keywords=[],
        cmc=3.0,
        rarity="rare",
        set_code="TST",
        number="1",
        artist="Test Artist",
        legalities={"standard": "legal"},
        prices=Prices(usd=1.50),
    )


@pytest.fixture
def sample_artists() -> list[ArtistSummary]:
    """Sample artists for testing."""
    return [
        ArtistSummary(
            name="Rebecca Guay",
            card_count=47,
            sets_count=18,
            first_card_year=1997,
            most_recent_year=2019,
        ),
        ArtistSummary(
            name="Terese Nielsen",
            card_count=89,
            sets_count=25,
            first_card_year=1996,
            most_recent_year=2020,
        ),
        ArtistSummary(
            name="Mark Poole",
            card_count=125,
            sets_count=35,
            first_card_year=1993,
            most_recent_year=2018,
        ),
    ]


class TestArtistCommands:
    """Tests for ArtistCommandsMixin functionality."""

    @pytest.mark.asyncio
    async def test_show_artist(
        self,
        mock_app_with_database,
        sample_artist_cards: list[CardSummary],
        sample_artist_detail: CardDetail,
    ) -> None:
        """Test showing artist's cards."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            artist_result = ArtistCardsResult(
                artist_name="Test Artist",
                cards=sample_artist_cards,
                total_count=len(sample_artist_cards),
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.artists.get_artist_cards", AsyncMock(return_value=artist_result)
                )
                m.setattr(
                    "mtg_core.tools.cards.get_card", AsyncMock(return_value=sample_artist_detail)
                )

                app.show_artist("Test Artist")
                await pilot.pause(0.3)

                assert app._artist_mode is True
                assert app._artist_name == "Test Artist"
                assert len(app._current_results) > 0

    @pytest.mark.asyncio
    async def test_show_artist_with_selection(
        self,
        mock_app_with_database,
        sample_artist_cards: list[CardSummary],
        sample_artist_detail: CardDetail,
    ) -> None:
        """Test showing artist with specific card selection."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            # Create cards with specific name
            cards = sample_artist_cards.copy()
            cards[10] = CardSummary(
                uuid="specific-uuid",
                name="Specific Card",
                mana_cost="{1}",
                type="Creature",
                colors=["U"],
                rarity="rare",
                set_code="TST",
                collector_number="10",
            )

            artist_result = ArtistCardsResult(
                artist_name="Test Artist",
                cards=cards,
                total_count=len(cards),
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.artists.get_artist_cards", AsyncMock(return_value=artist_result)
                )
                m.setattr(
                    "mtg_core.tools.cards.get_card", AsyncMock(return_value=sample_artist_detail)
                )

                app.show_artist("Test Artist", select_card="Specific Card")
                await pilot.pause(0.3)

    @pytest.mark.asyncio
    async def test_show_artist_no_cards(self, mock_app_with_database) -> None:
        """Test showing artist with no cards."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            artist_result = ArtistCardsResult(
                artist_name="Test Artist",
                cards=[],
                total_count=0,
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.artists.get_artist_cards", AsyncMock(return_value=artist_result)
                )

                app.show_artist("Test Artist")
                await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_show_artist_no_database(self, mock_app_with_database) -> None:
        """Test show artist with no database."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db = None

            app.show_artist("Test Artist")
            await pilot.pause(0.1)

    @pytest.mark.asyncio
    async def test_browse_artists(
        self, mock_app_with_database, sample_artists: list[ArtistSummary]
    ) -> None:
        """Test opening artist browser."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_all_artists = AsyncMock(return_value=sample_artists)

            app.browse_artists()
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_browse_artists_with_search(
        self, mock_app_with_database, sample_artists: list[ArtistSummary]
    ) -> None:
        """Test browsing artists with search query."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            filtered = [sample_artists[0]]
            app._db.search_artists = AsyncMock(return_value=filtered)

            app.browse_artists(search_query="Rebecca")
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_browse_artists_empty(self, mock_app_with_database) -> None:
        """Test browsing artists when none exist."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_all_artists = AsyncMock(return_value=[])

            app.browse_artists()
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_browse_artists_reuses_existing(
        self, mock_app_with_database, sample_artists: list[ArtistSummary]
    ) -> None:
        """Test that artist browser is reused if already exists."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_all_artists = AsyncMock(return_value=sample_artists)

            # First call creates browser
            app.browse_artists()
            await pilot.pause(0.2)

            # Second call should reuse existing
            app.browse_artists()
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_browse_artists_no_database(self, mock_app_with_database) -> None:
        """Test browse artists with no database."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db = None

            app.browse_artists()
            await pilot.pause(0.1)

    @pytest.mark.asyncio
    async def test_random_artist(
        self, mock_app_with_database, sample_artists: list[ArtistSummary]
    ) -> None:
        """Test selecting random artist."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_all_artists = AsyncMock(return_value=sample_artists)

            # Mock the actual show_artist call
            app.show_artist = AsyncMock()

            app.random_artist()
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_random_artist_no_artists(self, mock_app_with_database) -> None:
        """Test random artist when none exist."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_all_artists = AsyncMock(return_value=[])

            app.random_artist()
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_random_artist_no_database(self, mock_app_with_database) -> None:
        """Test random artist with no database."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db = None

            app.random_artist()
            await pilot.pause(0.1)

    @pytest.mark.asyncio
    async def test_display_artist_results(
        self,
        mock_app_with_database,
        sample_artist_detail: CardDetail,
    ) -> None:
        """Test displaying artist results."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._current_results = [sample_artist_detail] * 5
            app._pagination = AsyncMock(current_page=1, total_pages=1, total_items=5)

            app._display_artist_results()
            await pilot.pause()

            results_list = app.query_one("#results-list")
            assert len(results_list.children) == 5

    @pytest.mark.asyncio
    async def test_show_artist_pagination(
        self,
        mock_app_with_database,
        sample_artist_cards: list[CardSummary],
        sample_artist_detail: CardDetail,
    ) -> None:
        """Test artist results with pagination."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            # Create enough cards for multiple pages
            artist_result = ArtistCardsResult(
                artist_name="Test Artist",
                cards=sample_artist_cards,
                total_count=len(sample_artist_cards),
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.artists.get_artist_cards", AsyncMock(return_value=artist_result)
                )
                m.setattr(
                    "mtg_core.tools.cards.get_card", AsyncMock(return_value=sample_artist_detail)
                )

                app.show_artist("Test Artist")
                await pilot.pause(0.3)

                assert app._pagination is not None
                assert app._pagination.total_pages > 1

    @pytest.mark.asyncio
    async def test_show_results_view_artist_mode(self, mock_app_with_database) -> None:
        """Test showing results view in artist mode."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._show_results_view()
            await pilot.pause()

            dashboard = app.query_one("#dashboard")
            assert "hidden" in dashboard.classes

            results_container = app.query_one("#results-container")
            assert "hidden" not in results_container.classes


class TestArtistCommandsIntegration:
    """Integration tests for artist commands."""

    @pytest.mark.asyncio
    async def test_artist_workflow(
        self,
        mock_app_with_database,
        sample_artist_cards: list[CardSummary],
        sample_artist_detail: CardDetail,
    ) -> None:
        """Test complete artist browsing workflow."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            artist_result = ArtistCardsResult(
                artist_name="Test Artist",
                cards=sample_artist_cards[:10],
                total_count=10,
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.artists.get_artist_cards", AsyncMock(return_value=artist_result)
                )
                m.setattr(
                    "mtg_core.tools.cards.get_card", AsyncMock(return_value=sample_artist_detail)
                )

                # Show artist
                app.show_artist("Test Artist")
                await pilot.pause(0.3)

                # Verify artist mode active
                assert app._artist_mode is True
                assert app._artist_name == "Test Artist"

                # Verify cards loaded
                assert len(app._current_results) > 0

                # Verify UUID mapping created
                assert hasattr(app, "_artist_card_uuids")
                assert len(app._artist_card_uuids) > 0
