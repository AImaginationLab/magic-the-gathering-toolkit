"""Tests for SetsScreen."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from textual.widgets import Input

from mtg_core.data.models import Set
from mtg_core.data.models.responses import CardDetail, Prices, SetsResponse, SetSummary
from mtg_spellbook.app import MTGSpellbook
from mtg_spellbook.screens.sets import SetsScreen


@pytest.fixture
def sample_sets_list() -> list[SetSummary]:
    """Sample sets for testing."""
    return [
        SetSummary(code="lea", name="Limited Edition Alpha", release_date="1993-08-05"),
        SetSummary(code="leb", name="Limited Edition Beta", release_date="1993-10-04"),
        SetSummary(
            code="afr", name="Adventures in the Forgotten Realms", release_date="2021-07-23"
        ),
        SetSummary(code="one", name="Phyrexia: All Will Be One", release_date="2023-02-10"),
        SetSummary(code="mom", name="March of the Machine", release_date="2023-04-21"),
    ]


@pytest.fixture
def sample_set_model() -> Set:
    """Sample Set model."""
    return Set(
        code="lea",
        name="Limited Edition Alpha",
        type="core",
        release_date="1993-08-05",
        total_set_size=295,
    )


@pytest.fixture
def sample_set_cards() -> list[CardDetail]:
    """Sample cards for a set."""
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
            legalities={},
            prices=Prices(usd=15000.0),
        ),
        CardDetail(
            uuid="uuid2",
            name="Lightning Bolt",
            mana_cost="{R}",
            type="Instant",
            text="Lightning Bolt deals 3 damage to any target.",
            colors=["R"],
            color_identity=["R"],
            keywords=[],
            cmc=1.0,
            rarity="common",
            set_code="LEA",
            number="161",
            artist="Christopher Rush",
            legalities={},
            prices=Prices(usd=2.50),
        ),
    ]


class TestSetsScreen:
    """Tests for SetsScreen functionality."""

    @pytest.mark.asyncio
    async def test_screen_initialization(self, mock_mtg_database) -> None:
        """Test screen initializes correctly."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            pilot.app.push_screen(screen)
            await pilot.pause()

            assert screen._db is not None

    @pytest.mark.asyncio
    async def test_load_sets(self, mock_mtg_database, sample_sets_list: list[SetSummary]) -> None:
        """Test loading sets into the screen."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                assert screen.total_count > 0

    @pytest.mark.asyncio
    async def test_search_sets(self, mock_mtg_database, sample_sets_list: list[SetSummary]) -> None:
        """Test searching for sets."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                search_input = screen.query_one("#sets-search-input", Input)
                search_input.value = "alpha"
                await pilot.pause(0.3)

    @pytest.mark.asyncio
    async def test_select_set(
        self,
        mock_mtg_database,
        sample_sets_list: list[SetSummary],
        sample_set_model: Set,
        sample_set_cards: list[CardDetail],
    ) -> None:
        """Test selecting a set to view details."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            mock_mtg_database.get_set = AsyncMock(return_value=sample_set_model)
            mock_mtg_database.search_cards = AsyncMock(
                return_value=(sample_set_cards, len(sample_set_cards))
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                screen.action_select()
                await pilot.pause(0.3)

    @pytest.mark.asyncio
    async def test_focus_search(
        self, mock_mtg_database, sample_sets_list: list[SetSummary]
    ) -> None:
        """Test focusing the search input."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                screen.action_focus_search()
                await pilot.pause()

                search_input = screen.query_one("#sets-search-input", Input)
                assert search_input.has_focus

    @pytest.mark.asyncio
    async def test_toggle_pane(
        self,
        mock_mtg_database,
        sample_sets_list: list[SetSummary],
        sample_set_model: Set,
        sample_set_cards: list[CardDetail],
    ) -> None:
        """Test toggling between set list and detail panes."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            mock_mtg_database.get_set = AsyncMock(return_value=sample_set_model)
            mock_mtg_database.search_cards = AsyncMock(
                return_value=(sample_set_cards, len(sample_set_cards))
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                # Load set detail first
                screen.action_select()
                await pilot.pause(0.3)

                # Toggle pane
                screen.action_toggle_pane()
                await pilot.pause()

    @pytest.mark.asyncio
    async def test_filter_artist_series(
        self, mock_mtg_database, sample_sets_list: list[SetSummary]
    ) -> None:
        """Test filtering to artist series sets."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            # Add some artist series sets
            sets_with_art = [
                *sample_sets_list,
                SetSummary(code="aafr", name="AFR Art Series", release_date="2021-07-23"),
                SetSummary(code="aone", name="ONE Art Series", release_date="2023-02-10"),
            ]
            result = SetsResponse(sets=sets_with_art)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                screen.action_filter_artist_series()
                await pilot.pause(0.3)

                # Should show only sets starting with 'A'
                assert screen.show_artist_series_only is True

    @pytest.mark.asyncio
    async def test_explore_set_action(
        self, mock_mtg_database, sample_sets_list: list[SetSummary]
    ) -> None:
        """Test explore set action."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                # Mock app methods
                pilot.app.explore_set = AsyncMock()
                pilot.app._show_search_view = AsyncMock()

                screen.action_explore_set()
                await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_back_or_exit_from_list(
        self, mock_mtg_database, sample_sets_list: list[SetSummary]
    ) -> None:
        """Test back/exit action from set list."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                screen.action_back_or_exit()
                await pilot.pause()

    @pytest.mark.asyncio
    async def test_navigation_actions(
        self, mock_mtg_database, sample_sets_list: list[SetSummary]
    ) -> None:
        """Test navigation actions (up, down, page up/down, first, last)."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                # Test navigation
                screen.action_nav_down()
                await pilot.pause()

                screen.action_nav_up()
                await pilot.pause()

                screen.action_page_down()
                await pilot.pause()

                screen.action_page_up()
                await pilot.pause()

                screen.action_first()
                await pilot.pause()

                screen.action_last_item()
                await pilot.pause()

    @pytest.mark.asyncio
    async def test_render_header_no_search(
        self, mock_mtg_database, sample_sets_list: list[SetSummary]
    ) -> None:
        """Test header rendering with no search."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                header = screen._render_header()
                assert "SETS" in header

    @pytest.mark.asyncio
    async def test_render_header_with_search(
        self, mock_mtg_database, sample_sets_list: list[SetSummary]
    ) -> None:
        """Test header rendering with search active."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                screen.search_query = "alpha"
                screen.filtered_count = 1
                header = screen._render_header()
                assert "showing" in header.lower()

    @pytest.mark.asyncio
    async def test_render_statusbar(
        self, mock_mtg_database, sample_sets_list: list[SetSummary]
    ) -> None:
        """Test statusbar rendering."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                statusbar = screen._render_statusbar()
                assert "navigate" in statusbar.lower()

    @pytest.mark.asyncio
    async def test_empty_sets_list(self, mock_mtg_database) -> None:
        """Test screen with no sets."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=[])

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                assert screen.total_count == 0


class TestSetsScreenEdgeCases:
    """Tests for edge cases in SetsScreen."""

    @pytest.mark.asyncio
    async def test_no_database(self) -> None:
        """Test screen with no database."""
        screen = SetsScreen(db=None)

        async with MTGSpellbook().run_test() as pilot:
            pilot.app.push_screen(screen)
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_search_debouncing(
        self, mock_mtg_database, sample_sets_list: list[SetSummary]
    ) -> None:
        """Test search input debouncing."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                search_input = screen.query_one("#sets-search-input", Input)

                # Rapid typing
                search_input.value = "a"
                await pilot.pause(0.05)
                search_input.value = "al"
                await pilot.pause(0.05)
                search_input.value = "alp"
                await pilot.pause(0.05)
                search_input.value = "alph"
                await pilot.pause(0.05)
                search_input.value = "alpha"

                # Wait for debounce
                await pilot.pause(0.3)

    @pytest.mark.asyncio
    async def test_select_with_no_items(self, mock_mtg_database) -> None:
        """Test select action with no items in list."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=[])

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                screen.action_select()
                await pilot.pause()

    @pytest.mark.asyncio
    async def test_toggle_filter_rarity(
        self,
        mock_mtg_database,
        sample_sets_list: list[SetSummary],
        sample_set_model: Set,
        sample_set_cards: list[CardDetail],
    ) -> None:
        """Test toggling rarity filter in detail view."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            mock_mtg_database.get_set = AsyncMock(return_value=sample_set_model)
            mock_mtg_database.search_cards = AsyncMock(
                return_value=(sample_set_cards, len(sample_set_cards))
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                # Load set detail
                screen.action_select()
                await pilot.pause(0.3)

                # Toggle filter
                screen.action_toggle_filter()
                await pilot.pause(0.3)

                assert screen.current_filter is not None

    @pytest.mark.asyncio
    async def test_random_card_action(
        self,
        mock_mtg_database,
        sample_sets_list: list[SetSummary],
        sample_set_model: Set,
        sample_set_cards: list[CardDetail],
    ) -> None:
        """Test random card selection."""
        screen = SetsScreen(db=mock_mtg_database)

        async with MTGSpellbook().run_test() as pilot:
            result = SetsResponse(sets=sample_sets_list)

            mock_mtg_database.get_set = AsyncMock(return_value=sample_set_model)
            mock_mtg_database.search_cards = AsyncMock(
                return_value=(sample_set_cards, len(sample_set_cards))
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr("mtg_core.tools.sets.get_sets", AsyncMock(return_value=result))

                pilot.app.push_screen(screen)
                await pilot.pause(0.3)

                # Load set detail
                screen.action_select()
                await pilot.pause(0.3)

                # Random card
                screen.action_random_card()
                await pilot.pause()
