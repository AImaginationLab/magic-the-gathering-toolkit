"""Visual regression tests for MTG Spellbook using pytest-textual-snapshot.

These tests capture SVG screenshots of the app's UI states and serve as both
documentation and regression tests for visual changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest
from textual.pilot import Pilot

from mtg_spellbook.app import MTGSpellbook

# Skip all tests if pytest-textual-snapshot is not installed
pytest.importorskip("pytest_textual_snapshot")

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardDetail


@pytest.fixture
def mock_card_detail() -> CardDetail:
    """Mock CardDetail for testing card display."""
    from mtg_core.data.models.responses import CardDetail

    return CardDetail(
        name="Lightning Bolt",
        mana_cost="{R}",
        type="Instant",
        text="Lightning Bolt deals 3 damage to any target.",
        colors=["R"],
        color_identity=["R"],
        rarity="common",
        set_code="LEA",
        artist="Christopher Rush",
        power=None,
        toughness=None,
        loyalty=None,
        uuid="test-uuid-123",
        legalities={
            "vintage": "legal",
            "legacy": "legal",
            "modern": "legal",
            "commander": "legal",
        },
    )


@pytest.fixture
def mock_card_synergy() -> CardDetail:
    """Mock CardDetail for synergy card."""
    from mtg_core.data.models.responses import CardDetail

    return CardDetail(
        name="Young Pyromancer",
        mana_cost="{1}{R}",
        type="Creature — Human Shaman",
        text="Whenever you cast an instant or sorcery spell, create a 1/1 red Elemental creature token.",
        colors=["R"],
        color_identity=["R"],
        rarity="uncommon",
        set_code="M14",
        artist="Cynthia Sheppard",
        power="2",
        toughness="1",
        loyalty=None,
        uuid="test-uuid-456",
        legalities={},
    )


@pytest.fixture
def mock_database_context() -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    """Mock DatabaseContext for testing without real database."""
    mock_db = AsyncMock()
    mock_db.get_database_stats = AsyncMock(return_value={"unique_cards": 33000, "total_sets": 500})
    mock_db.get_all_keywords = AsyncMock(
        return_value={"flying", "haste", "deathtouch", "first strike"}
    )

    mock_scryfall = AsyncMock()
    mock_deck_manager = AsyncMock()

    return mock_db, mock_scryfall, mock_deck_manager


class TestMTGSpellbookScreenshots:
    """Visual regression tests for MTG Spellbook app."""

    def test_empty_state(self, snap_compare: Any, mock_database_context: Any) -> None:
        """Screenshot of the initial empty state after app loads."""

        async def setup_app(pilot: Pilot[None]) -> None:
            """Setup app with mocked database."""
            app = pilot.app
            if not isinstance(app, MTGSpellbook):
                return

            # Mock the database connections
            mock_db, mock_scryfall, mock_deck_manager = mock_database_context
            app._db = mock_db
            app._scryfall = mock_scryfall
            app._deck_manager = mock_deck_manager

            # Simulate on_mount stats update
            stats = await mock_db.get_database_stats()
            app._card_count = stats.get("unique_cards", 0)
            app._set_count = stats.get("total_sets", 0)

            # Update header
            from textual.widgets import Static

            header = app.query_one("#header-content", Static)
            from mtg_spellbook.ui.theme import ui_colors

            header.update(
                f"[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n"
                f"     [bold {ui_colors.GOLD_DIM}]✦[/]  "
                f"[bold {ui_colors.GOLD}]M T G   S P E L L B O O K[/]  "
                f"[bold {ui_colors.GOLD_DIM}]✦[/]     "
                f"[{ui_colors.GOLD}]{app._card_count:,}[/] [dim]cards[/] "
                f"[#555]·[/] "
                f"[{ui_colors.GOLD}]{app._set_count}[/] [dim]sets[/]\n"
                f"[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
            )

        assert snap_compare(
            MTGSpellbook(),
            run_before=setup_app,
            terminal_size=(120, 40),
        )

    def test_help_screen(self, snap_compare: Any, mock_database_context: Any) -> None:
        """Screenshot of the help screen displayed in the card panel."""

        async def setup_app(pilot: Pilot[None]) -> None:
            """Setup and show help screen."""
            app = pilot.app
            if not isinstance(app, MTGSpellbook):
                return

            # Mock database
            mock_db, mock_scryfall, mock_deck_manager = mock_database_context
            app._db = mock_db
            app._scryfall = mock_scryfall
            app._deck_manager = mock_deck_manager

            # Simulate stats
            stats = await mock_db.get_database_stats()
            app._card_count = stats.get("unique_cards", 0)
            app._set_count = stats.get("total_sets", 0)

            # Show help
            app.show_help()

        assert snap_compare(
            MTGSpellbook(),
            run_before=setup_app,
            terminal_size=(120, 40),
        )

    def test_search_results(
        self, snap_compare: Any, mock_database_context: Any, mock_card_detail: Any
    ) -> None:
        """Screenshot with search results displayed."""

        async def setup_app(pilot: Pilot[None]) -> None:
            """Setup app with search results."""
            app = pilot.app
            if not isinstance(app, MTGSpellbook):
                return

            # Mock database
            mock_db, mock_scryfall, mock_deck_manager = mock_database_context
            app._db = mock_db
            app._scryfall = mock_scryfall
            app._deck_manager = mock_deck_manager

            # Simulate stats
            stats = await mock_db.get_database_stats()
            app._card_count = stats.get("unique_cards", 0)
            app._set_count = stats.get("total_sets", 0)

            # Populate search results with mock cards
            app._current_results = [mock_card_detail]
            app._current_card = mock_card_detail

            # Update results list
            from textual.widgets import Label, ListItem

            from mtg_spellbook.widgets import ResultsList

            results_list = app.query_one("#results-list", ResultsList)
            results_list.clear()

            line = f"[bold #FFFFFF]{mock_card_detail.name}[/] {{R}} [dim]⚡[/]"
            results_list.append(ListItem(Label(line)))
            results_list.index = 0

            # Update card panel
            app._update_card_panel(mock_card_detail)

            # Update results header
            from textual.widgets import Static

            from mtg_spellbook.ui.theme import ui_colors

            header = app.query_one("#results-header", Static)
            header.update(f"[bold {ui_colors.GOLD}]🔍 Results (1)[/]")

        assert snap_compare(
            MTGSpellbook(),
            run_before=setup_app,
            terminal_size=(120, 40),
        )

    def test_card_detail_info_tab(
        self, snap_compare: Any, mock_database_context: Any, mock_card_detail: Any
    ) -> None:
        """Screenshot of card detail with Info tab active."""

        async def setup_app(pilot: Pilot[None]) -> None:
            """Setup app with card details displayed."""
            app = pilot.app
            if not isinstance(app, MTGSpellbook):
                return

            # Mock database
            mock_db, mock_scryfall, mock_deck_manager = mock_database_context
            app._db = mock_db
            app._scryfall = mock_scryfall
            app._deck_manager = mock_deck_manager

            # Simulate stats
            stats = await mock_db.get_database_stats()
            app._card_count = stats.get("unique_cards", 0)
            app._set_count = stats.get("total_sets", 0)

            # Set current card
            app._current_card = mock_card_detail
            app._update_card_panel(mock_card_detail)

            # Ensure Info tab is active
            from mtg_spellbook.widgets import CardPanel

            panel = app.query_one("#card-panel", CardPanel)
            from textual.widgets import TabbedContent

            tabs = panel.query_one(panel.get_child_id("tabs"), TabbedContent)
            tabs.active = panel.get_child_name("tab-card")

        assert snap_compare(
            MTGSpellbook(),
            run_before=setup_app,
            terminal_size=(120, 40),
        )

    def test_synergy_mode_side_by_side(
        self,
        snap_compare: Any,
        mock_database_context: Any,
        mock_card_detail: Any,
        mock_card_synergy: Any,
    ) -> None:
        """Screenshot of synergy mode with two cards side-by-side."""

        async def setup_app(pilot: Pilot[None]) -> None:
            """Setup app in synergy mode."""
            app = pilot.app
            if not isinstance(app, MTGSpellbook):
                return

            # Mock database
            mock_db, mock_scryfall, mock_deck_manager = mock_database_context
            app._db = mock_db
            app._scryfall = mock_scryfall
            app._deck_manager = mock_deck_manager

            # Simulate stats
            stats = await mock_db.get_database_stats()
            app._card_count = stats.get("unique_cards", 0)
            app._set_count = stats.get("total_sets", 0)

            # Enable synergy mode
            app._synergy_mode = True
            app._show_synergy_panel()

            # Set both panels
            from mtg_spellbook.widgets import CardPanel

            main_panel = app.query_one("#card-panel", CardPanel)
            source_panel = app.query_one("#source-card-panel", CardPanel)

            main_panel.update_card(mock_card_synergy)
            source_panel.update_card(mock_card_detail)

            # Update results
            app._current_results = [mock_card_synergy]
            app._current_card = mock_card_synergy

            from textual.widgets import Label, ListItem

            from mtg_spellbook.widgets import ResultsList

            results_list = app.query_one("#results-list", ResultsList)
            results_list.clear()
            results_list.append(ListItem(Label(f"[bold #C5C5C5]{mock_card_synergy.name}[/]")))

            # Update header
            from textual.widgets import Static

            from mtg_spellbook.ui.theme import ui_colors

            header = app.query_one("#results-header", Static)
            header.update(
                f"[bold {ui_colors.GOLD}]🔗 Synergies with {mock_card_detail.name} (1)[/]"
            )

        assert snap_compare(
            MTGSpellbook(),
            run_before=setup_app,
            terminal_size=(140, 45),
        )

    def test_deck_panel_visible(self, snap_compare: Any, mock_database_context: Any) -> None:
        """Screenshot with deck panel toggled visible (empty state)."""

        async def setup_app(pilot: Pilot[None]) -> None:
            """Setup app with deck panel visible."""
            app = pilot.app
            if not isinstance(app, MTGSpellbook):
                return

            # Mock database
            mock_db, mock_scryfall, mock_deck_manager = mock_database_context
            app._db = mock_db
            app._scryfall = mock_scryfall
            app._deck_manager = mock_deck_manager

            # Simulate stats
            stats = await mock_db.get_database_stats()
            app._card_count = stats.get("unique_cards", 0)
            app._set_count = stats.get("total_sets", 0)

            # Toggle deck panel visible (but keep it empty for deterministic screenshots)
            from mtg_spellbook.deck import DeckListPanel

            deck_panel = app.query_one("#deck-panel", DeckListPanel)
            deck_panel.add_class("visible")
            app._deck_panel_visible = True

        assert snap_compare(
            MTGSpellbook(),
            run_before=setup_app,
            terminal_size=(140, 40),
        )
