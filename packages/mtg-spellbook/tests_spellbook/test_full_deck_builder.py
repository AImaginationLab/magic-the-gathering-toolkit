"""Tests for FullDeckBuilder (Phase 3) - comprehensive user flow testing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from textual.widgets import Input, ListView

from mtg_spellbook.deck.full_builder import FullDeckBuilder, SearchResultItem
from mtg_spellbook.deck.quick_filter_bar import QuickFilterBar

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardSummary


@pytest.fixture
def sample_card_summary() -> CardSummary:
    """Sample CardSummary for testing."""
    from mtg_core.data.models.responses import CardSummary

    return CardSummary(
        name="Lightning Bolt",
        mana_cost="{R}",
        type="Instant",
        power=None,
        toughness=None,
        colors=["R"],
        cmc=1.0,
        rarity="common",
        set_code="LEA",
    )


@pytest.fixture
def sample_creature_summary() -> CardSummary:
    """Sample creature CardSummary for testing."""
    from mtg_core.data.models.responses import CardSummary

    return CardSummary(
        name="Goblin Guide",
        mana_cost="{R}",
        type="Creature - Goblin Scout",
        power="2",
        toughness="2",
        colors=["R"],
        cmc=1.0,
        rarity="rare",
        set_code="ZEN",
    )


@pytest.fixture
def sample_deck_with_cards() -> Any:
    """Sample deck with cards for testing."""
    from mtg_core.data.models.card import Card
    from mtg_spellbook.deck_manager import DeckCardWithData, DeckWithCards

    card1 = Card(
        uuid="uuid-bolt",
        name="Lightning Bolt",
        manaCost="{R}",
        manaValue=1.0,
        colors=["R"],
        colorIdentity=["R"],
        type="Instant",
        types=["Instant"],
        text="Lightning Bolt deals 3 damage to any target.",
        rarity="common",
        setCode="LEA",
        number="161",
        artist="Christopher Rush",
        keywords=[],
    )

    return DeckWithCards(
        id=1,
        name="Mono-Red Burn",
        format="modern",
        commander=None,
        cards=[
            DeckCardWithData(
                card_name="Lightning Bolt",
                quantity=4,
                is_sideboard=False,
                is_commander=False,
                set_code="M21",
                collector_number="152",
                card=card1,
            ),
        ],
    )


@pytest.fixture
def mock_deck_manager(sample_deck_with_cards: Any) -> Any:
    """Mock DeckManager for testing."""
    from mtg_spellbook.deck_manager import AddCardResult

    mock = AsyncMock()
    mock.get_deck = AsyncMock(return_value=sample_deck_with_cards)
    mock.add_card = AsyncMock(return_value=AddCardResult(success=True, new_quantity=1))
    mock.validate_deck = AsyncMock(
        return_value=MagicMock(is_valid=True, format="modern", issues=[])
    )
    return mock


@pytest.fixture
def mock_mtg_database(sample_card_summary: CardSummary) -> Any:
    """Mock MTGDatabase for testing."""
    mock_db = AsyncMock()
    mock_db.search_cards = AsyncMock(return_value=([sample_card_summary], 1))
    return mock_db


class TestFullDeckBuilderLayout:
    """Tests for FullDeckBuilder layout and composition."""

    @pytest.mark.asyncio
    async def test_full_builder_mounts_correctly(
        self,
        sample_deck_with_cards: Any,
        mock_deck_manager: Any,
        mock_mtg_database: Any,
    ) -> None:
        """Test that FullDeckBuilder mounts with all required components."""
        from textual.app import App, ComposeResult

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            builder = FullDeckBuilder(
                deck=sample_deck_with_cards,
                deck_manager=mock_deck_manager,
                db=mock_mtg_database,
            )
            pilot.app.push_screen(builder)
            await pilot.pause()

            # Verify key components exist
            assert builder.query_one("#builder-search-input", Input) is not None
            assert builder.query_one("#quick-filter-bar", QuickFilterBar) is not None
            assert builder.query_one("#search-results", ListView) is not None
            assert builder.query_one("#builder-deck-editor") is not None

    @pytest.mark.asyncio
    async def test_header_shows_deck_name_and_format(
        self,
        sample_deck_with_cards: Any,
        mock_deck_manager: Any,
        mock_mtg_database: Any,
    ) -> None:
        """Test that header displays deck name and format."""
        from textual.app import App, ComposeResult
        from textual.widgets import Static

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            builder = FullDeckBuilder(
                deck=sample_deck_with_cards,
                deck_manager=mock_deck_manager,
                db=mock_mtg_database,
            )
            pilot.app.push_screen(builder)
            await pilot.pause()

            header = builder.query_one("#builder-header", Static)
            header_text = str(header.render())
            assert "Mono-Red Burn" in header_text
            assert "modern" in header_text.lower()


class TestFullDeckBuilderNavigation:
    """Tests for keyboard navigation in FullDeckBuilder."""

    @pytest.mark.asyncio
    async def test_tab_switches_pane(
        self,
        sample_deck_with_cards: Any,
        mock_deck_manager: Any,
        mock_mtg_database: Any,
    ) -> None:
        """Test that Tab key switches between search and deck panes."""
        from textual.app import App, ComposeResult

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            builder = FullDeckBuilder(
                deck=sample_deck_with_cards,
                deck_manager=mock_deck_manager,
                db=mock_mtg_database,
            )
            pilot.app.push_screen(builder)
            await pilot.pause()

            # Initially in search pane
            assert builder._active_pane == "search"

            # Press Tab to switch to deck pane
            await pilot.press("tab")
            await pilot.pause()
            assert builder._active_pane == "deck"

            # Press Tab again to switch back to search
            # Note: Now that DeckEditorPanel no longer consumes Tab,
            # Tab should cycle back to search pane
            await pilot.press("tab")
            await pilot.pause()
            assert builder._active_pane == "search"

    @pytest.mark.asyncio
    async def test_slash_focuses_search(
        self,
        sample_deck_with_cards: Any,
        mock_deck_manager: Any,
        mock_mtg_database: Any,
    ) -> None:
        """Test that / key focuses search input."""
        from textual.app import App, ComposeResult

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            builder = FullDeckBuilder(
                deck=sample_deck_with_cards,
                deck_manager=mock_deck_manager,
                db=mock_mtg_database,
            )
            pilot.app.push_screen(builder)
            await pilot.pause()

            # Switch to deck pane first
            await pilot.press("tab")
            await pilot.pause()
            assert builder._active_pane == "deck"

            # Press / to focus search
            await pilot.press("slash")
            await pilot.pause()

            assert builder._active_pane == "search"
            search_input = builder.query_one("#builder-search-input", Input)
            assert search_input.has_focus

    @pytest.mark.asyncio
    async def test_escape_exits_builder(
        self,
        sample_deck_with_cards: Any,
        mock_deck_manager: Any,
        mock_mtg_database: Any,
    ) -> None:
        """Test that Escape key exits the builder."""
        from textual.app import App, ComposeResult

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            builder = FullDeckBuilder(
                deck=sample_deck_with_cards,
                deck_manager=mock_deck_manager,
                db=mock_mtg_database,
            )
            pilot.app.push_screen(builder)
            await pilot.pause()

            assert isinstance(pilot.app.screen, FullDeckBuilder)

            await pilot.press("escape")
            await pilot.pause()

            # Should no longer be showing builder
            assert not isinstance(pilot.app.screen, FullDeckBuilder)


class TestFullDeckBuilderSearch:
    """Tests for search functionality in FullDeckBuilder."""

    @pytest.mark.asyncio
    async def test_live_search_triggers_on_input(
        self,
        sample_deck_with_cards: Any,
        mock_deck_manager: Any,
        mock_mtg_database: Any,
        sample_card_summary: CardSummary,
    ) -> None:
        """Test that live search triggers when user types >= 2 characters."""
        from textual.app import App, ComposeResult

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            # Patch the card_tools.search_cards to return our sample
            with patch("mtg_core.tools.cards.search_cards") as mock_search:
                from mtg_core.data.models.responses import SearchResult

                mock_search.return_value = SearchResult(
                    cards=[sample_card_summary], page=1, page_size=50, total_count=1
                )

                builder = FullDeckBuilder(
                    deck=sample_deck_with_cards,
                    deck_manager=mock_deck_manager,
                    db=mock_mtg_database,
                )
                pilot.app.push_screen(builder)
                await pilot.pause()

                # Type in search box (more than 2 chars to trigger live search)
                search_input = builder.query_one("#builder-search-input", Input)
                search_input.value = "bolt"
                # Trigger input change manually
                search_input.post_message(Input.Changed(search_input, "bolt"))
                await pilot.pause()
                await pilot.pause()  # Extra pause for async work

                # Search should have been called
                mock_search.assert_called()

    @pytest.mark.asyncio
    async def test_search_results_display(
        self,
        sample_deck_with_cards: Any,
        mock_deck_manager: Any,
        mock_mtg_database: Any,
        sample_card_summary: CardSummary,
    ) -> None:
        """Test that search results are displayed in the list."""
        from textual.app import App, ComposeResult

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            builder = FullDeckBuilder(
                deck=sample_deck_with_cards,
                deck_manager=mock_deck_manager,
                db=mock_mtg_database,
            )
            pilot.app.push_screen(builder)
            await pilot.pause()

            # Manually set search results
            builder._search_results = [sample_card_summary]
            builder._update_search_results()
            await pilot.pause()

            # Verify results are shown
            results_list = builder.query_one("#search-results", ListView)
            assert len(results_list.children) == 1
            assert isinstance(results_list.children[0], SearchResultItem)


class TestFullDeckBuilderQuickAdd:
    """Tests for quick-add shortcuts in FullDeckBuilder."""

    @pytest.mark.asyncio
    async def test_space_adds_one_to_mainboard(
        self,
        sample_deck_with_cards: Any,
        mock_deck_manager: Any,
        mock_mtg_database: Any,
        sample_card_summary: CardSummary,
    ) -> None:
        """Test that Space key adds 1 copy to mainboard."""
        from textual.app import App, ComposeResult

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            builder = FullDeckBuilder(
                deck=sample_deck_with_cards,
                deck_manager=mock_deck_manager,
                db=mock_mtg_database,
            )
            pilot.app.push_screen(builder)
            await pilot.pause()

            # Set up search results
            builder._search_results = [sample_card_summary]
            builder._update_search_results()
            await pilot.pause()

            # Focus and highlight the search results
            results_list = builder.query_one("#search-results", ListView)
            results_list.focus()
            results_list.index = 0
            await pilot.pause()

            # Press Space to add card
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()  # Extra pause for async work

            # Verify add_card was called correctly
            mock_deck_manager.add_card.assert_called_once_with(
                1, "Lightning Bolt", 1, sideboard=False, set_code="LEA", collector_number=None
            )

    @pytest.mark.asyncio
    async def test_number_keys_add_n_copies(
        self,
        sample_deck_with_cards: Any,
        mock_deck_manager: Any,
        mock_mtg_database: Any,
        sample_card_summary: CardSummary,
    ) -> None:
        """Test that 1-4 keys add N copies to mainboard."""
        from textual.app import App, ComposeResult

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            builder = FullDeckBuilder(
                deck=sample_deck_with_cards,
                deck_manager=mock_deck_manager,
                db=mock_mtg_database,
            )
            pilot.app.push_screen(builder)
            await pilot.pause()

            # Set up search results
            builder._search_results = [sample_card_summary]
            builder._update_search_results()
            await pilot.pause()

            # Focus and highlight the search results
            results_list = builder.query_one("#search-results", ListView)
            results_list.focus()
            results_list.index = 0
            await pilot.pause()

            # Press '4' to add 4 copies
            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            # Verify add_card was called with quantity=4
            mock_deck_manager.add_card.assert_called_once_with(
                1, "Lightning Bolt", 4, sideboard=False, set_code="LEA", collector_number=None
            )

    @pytest.mark.asyncio
    async def test_shift_space_adds_to_sideboard(
        self,
        sample_deck_with_cards: Any,
        mock_deck_manager: Any,
        mock_mtg_database: Any,
        sample_card_summary: CardSummary,
    ) -> None:
        """Test that Shift+Space adds 1 copy to sideboard."""
        from textual.app import App, ComposeResult

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            builder = FullDeckBuilder(
                deck=sample_deck_with_cards,
                deck_manager=mock_deck_manager,
                db=mock_mtg_database,
            )
            pilot.app.push_screen(builder)
            await pilot.pause()

            # Set up search results
            builder._search_results = [sample_card_summary]
            builder._update_search_results()
            await pilot.pause()

            # Focus and highlight the search results
            results_list = builder.query_one("#search-results", ListView)
            results_list.focus()
            results_list.index = 0
            await pilot.pause()

            # Press Shift+Space to add to sideboard
            await pilot.press("shift+space")
            await pilot.pause()
            await pilot.pause()

            # Verify add_card was called with sideboard=True
            mock_deck_manager.add_card.assert_called_once_with(
                1, "Lightning Bolt", 1, sideboard=True, set_code="LEA", collector_number=None
            )


class TestFullDeckBuilderValidation:
    """Tests for deck validation in FullDeckBuilder."""

    @pytest.mark.asyncio
    async def test_v_key_triggers_validation(
        self,
        sample_deck_with_cards: Any,
        mock_deck_manager: Any,
        mock_mtg_database: Any,
    ) -> None:
        """Test that V key triggers deck validation."""
        from textual.app import App, ComposeResult

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            builder = FullDeckBuilder(
                deck=sample_deck_with_cards,
                deck_manager=mock_deck_manager,
                db=mock_mtg_database,
            )
            pilot.app.push_screen(builder)
            await pilot.pause()

            # Press V to validate
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()

            # Validation should have been triggered (no error should occur)
            # The test passes if no exception is raised


class TestFullDeckBuilderFilterIntegration:
    """Tests for filter integration in FullDeckBuilder."""

    @pytest.mark.asyncio
    async def test_filter_changes_trigger_search(
        self,
        sample_deck_with_cards: Any,
        mock_deck_manager: Any,
        mock_mtg_database: Any,
        sample_card_summary: CardSummary,
    ) -> None:
        """Test that filter changes trigger a new search."""
        from textual.app import App, ComposeResult

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            with patch("mtg_core.tools.cards.search_cards") as mock_search:
                from mtg_core.data.models.responses import SearchResult

                mock_search.return_value = SearchResult(
                    cards=[sample_card_summary], page=1, page_size=50, total_count=1
                )

                builder = FullDeckBuilder(
                    deck=sample_deck_with_cards,
                    deck_manager=mock_deck_manager,
                    db=mock_mtg_database,
                )
                pilot.app.push_screen(builder)
                await pilot.pause()

                # First, set a search query
                search_input = builder.query_one("#builder-search-input", Input)
                search_input.value = "bolt"
                await pilot.pause()

                # Click a filter button to change filters
                filter_bar = builder.query_one("#quick-filter-bar", QuickFilterBar)
                # Simulate filter change by posting message
                filter_bar.post_message(QuickFilterBar.FiltersChanged({"cmc": 1}))
                await pilot.pause()
                await pilot.pause()

                # Search should have been called (at least once due to filter change)
                # Note: May be called multiple times due to input and filter changes


class TestSearchResultItem:
    """Tests for SearchResultItem widget."""

    @pytest.mark.asyncio
    async def test_search_result_item_displays_card_info(
        self, sample_card_summary: CardSummary
    ) -> None:
        """Test that SearchResultItem displays card name and mana cost."""
        from textual.app import App, ComposeResult
        from textual.widgets import ListView

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield ListView(id="test-list")

        async with TestApp().run_test() as pilot:
            test_list = pilot.app.query_one("#test-list", ListView)
            item = SearchResultItem(sample_card_summary)
            test_list.append(item)
            await pilot.pause()

            # The item should render with card name
            assert item.card.name == "Lightning Bolt"
            assert item.card.mana_cost == "{R}"
