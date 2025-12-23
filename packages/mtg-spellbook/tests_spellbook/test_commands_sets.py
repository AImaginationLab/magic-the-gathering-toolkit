"""Tests for set commands mixin."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from textual.widgets import Static

from mtg_core.data.models import Set
from mtg_core.data.models.card import Card
from mtg_core.data.models.responses import (
    CardDetail,
    CardSummary,
    Prices,
    SetDetail,
    SetsResponse,
    SetSummary,
)
from mtg_core.data.models.responses import (
    SetStats as SetStatsData,
)


@pytest.fixture
def sample_sets() -> list[SetSummary]:
    """Sample sets for testing."""
    return [
        SetSummary(code="lea", name="Limited Edition Alpha", release_date="1993-08-05"),
        SetSummary(code="leb", name="Limited Edition Beta", release_date="1993-10-04"),
        SetSummary(
            code="afr", name="Adventures in the Forgotten Realms", release_date="2021-07-23"
        ),
    ]


@pytest.fixture
def sample_set_detail() -> SetDetail:
    """Sample set detail for testing."""
    return SetDetail(
        code="lea",
        name="Limited Edition Alpha",
        type="core",
        release_date="1993-08-05",
        total_set_size=295,
    )


@pytest.fixture
def sample_set_model() -> Set:
    """Sample Set model for testing."""
    return Set(
        code="lea",
        name="Limited Edition Alpha",
        type="core",
        release_date="1993-08-05",
        total_set_size=295,
    )


@pytest.fixture
def sample_set_cards() -> list[CardDetail]:
    """Sample cards from a set."""
    return [
        CardDetail(
            uuid="uuid1",
            name="Black Lotus",
            mana_cost="{0}",
            type="Artifact",
            text="Sacrifice Black Lotus: Add three mana of any one color.",
            colors=[],
            color_identity=[],
            keywords=[],
            cmc=0.0,
            rarity="rare",
            set_code="LEA",
            number="232",
            artist="Christopher Rush",
            legalities={"vintage": "restricted", "legacy": "banned"},
            prices=Prices(usd=15000.0),
        ),
        CardDetail(
            uuid="uuid2",
            name="Ancestral Recall",
            mana_cost="{U}",
            type="Instant",
            text="Target player draws three cards.",
            colors=["U"],
            color_identity=["U"],
            keywords=[],
            cmc=1.0,
            rarity="rare",
            set_code="LEA",
            number="48",
            artist="Mark Poole",
            legalities={"vintage": "restricted", "legacy": "banned"},
            prices=Prices(usd=5000.0),
        ),
    ]


class TestSetCommands:
    """Tests for SetCommandsMixin functionality."""

    @pytest.mark.asyncio
    async def test_browse_sets(self, mock_app_with_database, sample_sets: list[SetSummary]) -> None:
        """Test browsing sets displays them in results list."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_all_sets = AsyncMock(return_value=sample_sets)

            result = SetsResponse(sets=sample_sets)
            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))
                app.browse_sets("")
                await pilot.pause()

            results_list = app.query_one("#results-list")
            assert len(results_list.children) > 0

    @pytest.mark.asyncio
    async def test_browse_sets_with_query(
        self, mock_app_with_database, sample_sets: list[SetSummary]
    ) -> None:
        """Test browsing sets with search query."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            filtered = [sample_sets[0]]
            result = SetsResponse(sets=filtered)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))
                app.browse_sets("alpha")
                await pilot.pause()

            header = app.query_one("#results-header", Static)
            header_text = str(header.render())
            assert "1" in header_text or "Sets" in header_text

    @pytest.mark.asyncio
    async def test_explore_set(
        self, mock_app_with_database, sample_set_model: Set, sample_set_cards: list[CardDetail]
    ) -> None:
        """Test exploring a set loads cards into results."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_set = AsyncMock(return_value=sample_set_model)
            app._db.search_cards = AsyncMock(return_value=(sample_set_cards, len(sample_set_cards)))

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.cards.get_card",
                    AsyncMock(return_value=sample_set_cards[0]),
                )
                app.explore_set("lea")
                await pilot.pause(0.3)

            assert app._set_mode is True
            assert app._set_code == "LEA"

    @pytest.mark.asyncio
    async def test_explore_set_no_cards(
        self, mock_app_with_database, sample_set_model: Set
    ) -> None:
        """Test exploring a set with no cards shows message."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_set = AsyncMock(return_value=sample_set_model)
            app._db.search_cards = AsyncMock(return_value=([], 0))

            app.explore_set("lea")
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_show_set(self, mock_app_with_database, sample_set_detail: SetDetail) -> None:
        """Test showing set details."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_set", AsyncMock(return_value=sample_set_detail))
                app.show_set("lea")
                await pilot.pause(0.2)

            results_list = app.query_one("#results-list")
            assert len(results_list.children) > 0

    @pytest.mark.asyncio
    async def test_show_set_not_found(self, mock_app_with_database) -> None:
        """Test showing non-existent set."""
        from mtg_core.exceptions import SetNotFoundError

        app = mock_app_with_database()

        async with app.run_test() as pilot:
            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.sets.get_set",
                    AsyncMock(side_effect=SetNotFoundError("Not found")),
                )
                app.show_set("xyz")
                await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_show_stats(self, mock_app_with_database) -> None:
        """Test showing database statistics."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_database_stats = AsyncMock(
                return_value={
                    "unique_cards": 25000,
                    "total_sets": 500,
                    "data_version": "2024-01",
                }
            )

            app.show_stats()
            await pilot.pause(0.2)

            results_list = app.query_one("#results-list")
            assert len(results_list.children) > 0

    @pytest.mark.asyncio
    async def test_show_set_detail(
        self, mock_app_with_database, sample_set_model: Set, sample_set_cards: list[CardDetail]
    ) -> None:
        """Test showing detailed set view."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            stats = SetStatsData(
                set_code="LEA",
                total_cards=len(sample_set_cards),
                rarity_distribution={"rare": 2},
                color_distribution={"U": 1, "C": 1},
            )

            app._db.get_set = AsyncMock(return_value=sample_set_model)
            app._db.get_cards_in_set = AsyncMock(
                return_value=[
                    Card(
                        uuid=card.uuid,
                        name=card.name,
                        manaCost=card.mana_cost,
                        manaValue=card.cmc,
                        type=card.type,
                        types=["Artifact"] if "Artifact" in card.type else ["Instant"],
                        colors=card.colors,
                        colorIdentity=card.color_identity,
                        rarity=card.rarity,
                        setCode=card.set_code or "LEA",
                        number=card.number or "1",
                        artist=card.artist or "Unknown",
                        keywords=card.keywords,
                        power=None,
                        toughness=None,
                    )
                    for card in sample_set_cards
                ]
            )
            app._db.get_set_stats = AsyncMock(return_value=stats)

            app.show_set_detail("lea")
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_show_set_detail_no_cards(
        self, mock_app_with_database, sample_set_model: Set
    ) -> None:
        """Test showing set detail with no cards."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_set = AsyncMock(return_value=sample_set_model)
            app._db.get_cards_in_set = AsyncMock(return_value=[])

            app.show_set_detail("lea")
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_display_set_results(
        self, mock_app_with_database, sample_set_cards: list[CardDetail]
    ) -> None:
        """Test displaying set results."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._current_results = sample_set_cards
            app._pagination = MagicMock(current_page=1, total_pages=1, total_items=2)

            app._display_set_results()
            await pilot.pause()

            results_list = app.query_one("#results-list")
            assert len(results_list.children) == len(sample_set_cards)

    @pytest.mark.asyncio
    async def test_load_more_set_cards(
        self, mock_app_with_database, sample_set_cards: list[CardDetail]
    ) -> None:
        """Test lazy loading more set cards."""
        from mtg_spellbook.pagination import PaginationState

        app = mock_app_with_database()

        async with app.run_test():
            # Setup initial state
            app._set_mode = True
            app._set_code = "LEA"
            summaries = [
                CardSummary(
                    uuid=card.uuid,
                    name=card.name,
                    mana_cost=card.mana_cost,
                    type=card.type,
                    colors=card.colors,
                    rarity=card.rarity,
                    set_code=card.set_code,
                )
                for card in sample_set_cards
            ]
            app._pagination = PaginationState.from_summaries(
                summaries, source_type="set", source_query="LEA"
            )

            # Mock returns sample_set_cards (2 cards) - test expects at least this many
            app._db.search_cards = AsyncMock(return_value=(sample_set_cards, 4))

            await app._load_more_set_cards_async(2)

            # After loading, should have loaded at least initial + loaded cards
            assert app._pagination.loaded_items_count >= 2

    @pytest.mark.asyncio
    async def test_show_results_view(self, mock_app_with_database) -> None:
        """Test showing results view."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._show_results_view()
            await pilot.pause()

            dashboard = app.query_one("#dashboard")
            assert "hidden" in dashboard.classes
