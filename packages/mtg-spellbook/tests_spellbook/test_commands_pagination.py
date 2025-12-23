"""Tests for pagination commands mixin."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from mtg_core.data.models.responses import CardDetail, CardSummary, Prices
from mtg_spellbook.pagination import PaginationState


@pytest.fixture
def sample_paginated_cards() -> list[CardSummary]:
    """Sample cards for pagination testing."""
    cards = []
    for i in range(100):
        cards.append(
            CardSummary(
                uuid=f"uuid-{i}",
                name=f"Card {i}",
                mana_cost="{1}",
                type="Creature",
                colors=["U"],
                rarity="common",
                set_code="TST",
            )
        )
    return cards


@pytest.fixture
def sample_card_details() -> list[CardDetail]:
    """Sample card details for testing."""
    cards = []
    for i in range(10):
        cards.append(
            CardDetail(
                uuid=f"uuid-{i}",
                name=f"Card {i}",
                mana_cost="{1}",
                type="Creature — Human",
                text="Test card",
                power="2",
                toughness="2",
                colors=["U"],
                color_identity=["U"],
                keywords=[],
                cmc=1.0,
                rarity="common",
                set_code="TST",
                number=str(i),
                artist="Test Artist",
                legalities={"standard": "legal"},
                prices=Prices(usd=0.25),
            )
        )
    return cards


class TestPaginationCommands:
    """Tests for PaginationCommandsMixin functionality."""

    @pytest.mark.asyncio
    async def test_next_page(
        self, mock_app_with_database, sample_paginated_cards: list[CardSummary]
    ) -> None:
        """Test navigating to next page."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._pagination = PaginationState.from_summaries(
                sample_paginated_cards, source_type="search", page_size=25
            )
            app._current_results = []

            initial_page = app._pagination.current_page
            app.action_next_page()
            await pilot.pause(0.2)

            assert app._pagination.current_page == initial_page + 1

    @pytest.mark.asyncio
    async def test_prev_page(
        self, mock_app_with_database, sample_paginated_cards: list[CardSummary]
    ) -> None:
        """Test navigating to previous page."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._pagination = PaginationState.from_summaries(
                sample_paginated_cards, source_type="search", page_size=25
            )
            app._pagination.go_to_page(2)
            app._current_results = []

            app.action_prev_page()
            await pilot.pause(0.2)

            assert app._pagination.current_page == 1

    @pytest.mark.asyncio
    async def test_first_page(
        self, mock_app_with_database, sample_paginated_cards: list[CardSummary]
    ) -> None:
        """Test navigating to first page."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._pagination = PaginationState.from_summaries(
                sample_paginated_cards, source_type="search", page_size=25
            )
            app._pagination.go_to_page(3)
            app._current_results = []

            app.action_first_page()
            await pilot.pause(0.2)

            assert app._pagination.current_page == 1

    @pytest.mark.asyncio
    async def test_last_page(
        self, mock_app_with_database, sample_paginated_cards: list[CardSummary]
    ) -> None:
        """Test navigating to last page."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._pagination = PaginationState.from_summaries(
                sample_paginated_cards, source_type="search", page_size=25
            )
            app._current_results = []

            app.action_last_page()
            await pilot.pause(0.2)

            assert app._pagination.current_page == app._pagination.total_pages

    @pytest.mark.asyncio
    async def test_goto_page_modal(
        self, mock_app_with_database, sample_paginated_cards: list[CardSummary]
    ) -> None:
        """Test showing goto page modal."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._pagination = PaginationState.from_summaries(
                sample_paginated_cards, source_type="search", page_size=25
            )

            app.action_goto_page()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_goto_page_single_page(self, mock_app_with_database) -> None:
        """Test goto page does nothing with single page."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._pagination = PaginationState.from_summaries(
                [
                    CardSummary(
                        name="Card", type="Creature", colors=[], rarity="common", set_code="TST"
                    )
                ],
                source_type="search",
                page_size=25,
            )

            app.action_goto_page()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_load_current_page_with_cache(
        self,
        mock_app_with_database,
        sample_paginated_cards: list[CardSummary],
        sample_card_details: list[CardDetail],
    ) -> None:
        """Test loading page from cache."""
        app = mock_app_with_database()

        async with app.run_test() as _pilot:
            app._pagination = PaginationState.from_summaries(
                sample_paginated_cards, source_type="search", page_size=10
            )
            app._pagination.cache_details(1, sample_card_details)

            # _load_current_page is decorated with @work, so it returns a Worker
            worker = app._load_current_page()
            await worker.wait()

            assert len(app._current_results) == len(sample_card_details)

    @pytest.mark.asyncio
    async def test_load_current_page_without_cache(
        self,
        mock_app_with_database,
        sample_paginated_cards: list[CardSummary],
        sample_card_details: list[CardDetail],
    ) -> None:
        """Test loading page without cache."""
        app = mock_app_with_database()

        async with app.run_test() as _pilot:
            app._pagination = PaginationState.from_summaries(
                sample_paginated_cards, source_type="search", page_size=10
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.cards.get_card", AsyncMock(return_value=sample_card_details[0])
                )
                # _load_current_page is decorated with @work, so it returns a Worker
                worker = app._load_current_page()
                await worker.wait()

    @pytest.mark.asyncio
    async def test_display_search_results(
        self, mock_app_with_database, sample_card_details: list[CardDetail]
    ) -> None:
        """Test displaying search results."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._current_results = sample_card_details
            app._pagination = PaginationState.from_summaries(
                [
                    CardSummary(
                        name=c.name,
                        type=c.type,
                        colors=c.colors,
                        rarity=c.rarity,
                        set_code=c.set_code,
                    )
                    for c in sample_card_details
                ],
                source_type="search",
            )

            app._display_search_results()
            await pilot.pause()

            results_list = app.query_one("#results-list")
            assert len(results_list.children) == len(sample_card_details)

    @pytest.mark.asyncio
    async def test_display_synergy_results(
        self, mock_app_with_database, sample_card_details: list[CardDetail]
    ) -> None:
        """Test displaying synergy results with scores."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._current_results = sample_card_details[:3]
            app._synergy_mode = True
            app._synergy_info = {
                "Card 0": {"score": 0.9, "type": "keyword", "reason": "Flying synergy"},
                "Card 1": {"score": 0.7, "type": "tribal", "reason": "Elf tribal"},
                "Card 2": {"score": 0.5, "type": "theme", "reason": "Sacrifice theme"},
            }
            app._pagination = PaginationState.from_summaries(
                [
                    CardSummary(
                        name=c.name,
                        type=c.type,
                        colors=c.colors,
                        rarity=c.rarity,
                        set_code=c.set_code,
                    )
                    for c in sample_card_details[:3]
                ],
                source_type="synergy",
            )

            app._display_synergy_results()
            await pilot.pause()

            results_list = app.query_one("#results-list")
            assert len(results_list.children) == 3

    @pytest.mark.asyncio
    async def test_update_pagination_header_single_page(self, mock_app_with_database) -> None:
        """Test pagination header with single page."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._pagination = PaginationState.from_summaries(
                [
                    CardSummary(
                        name="Card", type="Creature", colors=[], rarity="common", set_code="TST"
                    )
                ],
                source_type="search",
            )
            app._synergy_mode = False
            app._artist_mode = False

            app._update_pagination_header()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_update_pagination_header_multiple_pages(
        self, mock_app_with_database, sample_paginated_cards: list[CardSummary]
    ) -> None:
        """Test pagination header with multiple pages."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._pagination = PaginationState.from_summaries(
                sample_paginated_cards, source_type="search", page_size=25
            )
            app._synergy_mode = False
            app._artist_mode = False

            app._update_pagination_header()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_update_pagination_header_artist_mode(
        self, mock_app_with_database, sample_paginated_cards: list[CardSummary]
    ) -> None:
        """Test pagination header in artist mode."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._pagination = PaginationState.from_summaries(
                sample_paginated_cards, source_type="artist", page_size=25
            )
            app._artist_mode = True
            app._artist_name = "Test Artist"
            app._synergy_mode = False

            app._update_pagination_header()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_update_pagination_header_synergy_mode(
        self, mock_app_with_database, sample_paginated_cards: list[CardSummary]
    ) -> None:
        """Test pagination header in synergy mode."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._pagination = PaginationState.from_summaries(
                sample_paginated_cards, source_type="synergy", page_size=25
            )
            app._synergy_mode = True
            app._artist_mode = False

            app._update_pagination_header()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_load_card_details_search_mode(
        self,
        mock_app_with_database,
        sample_paginated_cards: list[CardSummary],
        sample_card_details: list[CardDetail],
    ) -> None:
        """Test loading card details in search mode."""
        app = mock_app_with_database()

        async with app.run_test():
            app._artist_mode = False

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.cards.get_card", AsyncMock(return_value=sample_card_details[0])
                )
                details = await app._load_card_details(sample_paginated_cards[:5], 0)
                assert len(details) > 0

    @pytest.mark.asyncio
    async def test_load_card_details_artist_mode(
        self,
        mock_app_with_database,
        sample_paginated_cards: list[CardSummary],
        sample_card_details: list[CardDetail],
    ) -> None:
        """Test loading card details in artist mode with UUIDs."""
        app = mock_app_with_database()

        async with app.run_test():
            app._artist_mode = True
            app._artist_card_uuids = {0: "uuid-0", 1: "uuid-1"}

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.cards.get_card", AsyncMock(return_value=sample_card_details[0])
                )
                details = await app._load_card_details(sample_paginated_cards[:2], 0)
                assert len(details) > 0

    @pytest.mark.asyncio
    async def test_prefetch_next_page(
        self,
        mock_app_with_database,
        sample_paginated_cards: list[CardSummary],
        sample_card_details: list[CardDetail],
    ) -> None:
        """Test prefetching next page in background."""
        app = mock_app_with_database()

        async with app.run_test() as _pilot:
            app._pagination = PaginationState.from_summaries(
                sample_paginated_cards, source_type="search", page_size=10
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.cards.get_card", AsyncMock(return_value=sample_card_details[0])
                )
                # _prefetch_next_page is decorated with @work, so it returns a Worker
                worker = app._prefetch_next_page()
                await worker.wait()

    @pytest.mark.asyncio
    async def test_format_result_line(
        self, mock_app_with_database, sample_card_details: list[CardDetail]
    ) -> None:
        """Test formatting result line with all fields."""
        app = mock_app_with_database()

        async with app.run_test():
            card = sample_card_details[0]
            line = app._format_result_line(card)

            assert card.name in line
            assert isinstance(line, str)

    @pytest.mark.asyncio
    async def test_get_card_stats_creature(
        self, mock_app_with_database, sample_card_details: list[CardDetail]
    ) -> None:
        """Test getting stats for creature card."""
        app = mock_app_with_database()

        async with app.run_test():
            card = sample_card_details[0]
            stats = app._get_card_stats(card)

            assert "/" in stats or stats == "2/2"

    @pytest.mark.asyncio
    async def test_get_card_stats_planeswalker(self, mock_app_with_database) -> None:
        """Test getting stats for planeswalker card."""
        app = mock_app_with_database()

        async with app.run_test():
            card = CardDetail(
                uuid="pw1",
                name="Test Walker",
                mana_cost="{2}{U}{U}",
                type="Planeswalker — Test",
                text="Test",
                colors=["U"],
                color_identity=["U"],
                keywords=[],
                cmc=4.0,
                rarity="mythic",
                set_code="TST",
                number="1",
                artist="Test",
                loyalty="4",
                legalities={},
            )

            stats = app._get_card_stats(card)
            assert "4" in stats or "\u2726" in stats

    @pytest.mark.asyncio
    async def test_get_card_price(
        self, mock_app_with_database, sample_card_details: list[CardDetail]
    ) -> None:
        """Test getting card price."""
        app = mock_app_with_database()

        async with app.run_test():
            card = sample_card_details[0]
            price = app._get_card_price(card)

            assert "$" in price or price == ""
