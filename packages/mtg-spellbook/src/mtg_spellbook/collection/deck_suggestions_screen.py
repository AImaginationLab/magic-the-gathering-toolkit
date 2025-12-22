"""Full-screen deck suggestions view."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.widgets import Button, ListItem, ListView, Static

from mtg_core.tools.recommendations.deck_finder import DeckSuggestion

from ..screens import BaseScreen
from ..ui.theme import ui_colors


@dataclass
class CollectionCardInfo:
    """Card info passed to deck suggestions."""

    name: str
    type_line: str | None = None
    colors: list[str] | None = None
    mana_cost: str | None = None
    text: str | None = None
    color_identity: list[str] | None = None


@dataclass
class CreateDeckResult:
    """Result when creating a deck from suggestion."""

    deck_name: str
    card_names: list[str]  # Cards user owns
    cards_missing: list[str] | None = None  # Cards to acquire (e.g., basic lands)
    commander: str | None = None
    format_type: str = "commander"


class SuggestionListItem(ListItem):
    """ListItem that stores a deck suggestion."""

    def __init__(self, suggestion: DeckSuggestion, content: str) -> None:
        super().__init__()
        self.suggestion = suggestion
        self._content = content

    def compose(self) -> ComposeResult:
        yield Static(self._content)


class DeckSuggestionsScreen(BaseScreen[CreateDeckResult | None]):
    """Full-screen deck suggestions based on collection.

    Shows what decks can be built from the user's collection.
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape,q", "close", "Back", show=True),
        Binding("c", "show_commander", "Commander", show=True),
        Binding("s", "show_standard", "Standard", show=True),
        Binding("enter", "create_deck", "Create", show=True),
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
        Binding("pageup", "page_up", show=False),
        Binding("pagedown", "page_down", show=False),
    ]

    # Don't show footer - this screen has its own status bar
    show_footer: ClassVar[bool] = False

    CSS = """
    DeckSuggestionsScreen {
        background: #0d0d0d;
    }

    /* Override screen-content to use grid for proper height distribution */
    DeckSuggestionsScreen #screen-content {
        layout: grid;
        grid-size: 1;
        grid-rows: 3 3 1fr 2;  /* header, format-bar, list, statusbar */
    }

    #suggestions-header {
        background: #0a0a14;
        border-bottom: heavy #c9a227;
        padding: 0 2;
        content-align: center middle;
    }

    #format-bar {
        background: #121218;
        padding: 0 2;
        border-bottom: solid #2a2a4e;
    }

    .format-btn {
        width: 14;
        height: 3;
        margin: 0 1 0 0;
        background: #1a1a2e;
        border: solid #3d3d3d;
    }

    .format-btn:hover {
        background: #2a2a4e;
    }

    .format-btn.-active {
        background: #c9a227;
        color: #0a0a14;
        text-style: bold;
    }

    #suggestions-list {
        width: 100%;
        height: 1fr;
        scrollbar-color: #c9a227;
    }

    #suggestions-list > ListItem {
        height: auto;
        min-height: 4;
        padding: 1 2;
        background: #121212;
        border-bottom: solid #2a2a4e;
    }

    #suggestions-list > ListItem:hover {
        background: #1a1a2e;
    }

    #suggestions-list > ListItem.-highlight {
        background: #2a2a4e;
        border-left: heavy #c9a227;
    }

    #suggestions-statusbar {
        padding: 0 2;
        background: #1a1a1a;
        border-top: solid #3d3d3d;
        content-align: left middle;
    }

    #empty-state {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-align: center;
    }
    """

    def __init__(self, card_info_list: list[CollectionCardInfo]) -> None:
        super().__init__()
        self._card_info_list = card_info_list
        self._collection_cards = {c.name for c in card_info_list}
        self._current_format = "commander"
        self._suggestions: list[DeckSuggestion] = []
        self._selected_suggestion: DeckSuggestion | None = None

    def compose_content(self) -> ComposeResult:
        yield Static(
            f"[bold {ui_colors.GOLD}]SUGGEST DECKS[/]  "
            f"[{ui_colors.TEXT_DIM}]({len(self._card_info_list)} cards in collection)[/]",
            id="suggestions-header",
        )

        with Horizontal(id="format-bar"):
            yield Button("Commander", id="btn-commander", classes="format-btn -active")
            yield Button("Standard", id="btn-standard", classes="format-btn")

        yield ListView(id="suggestions-list")

        yield Static(self._render_statusbar(), id="suggestions-statusbar")

    async def on_mount(self) -> None:
        """Load suggestions on mount."""
        # Delay loading until after the screen is fully mounted
        self.call_after_refresh(self._load_suggestions)
        try:
            list_view = self.query_one("#suggestions-list", ListView)
            list_view.focus()
        except NoMatches:
            pass

    def _load_suggestions(self) -> None:
        """Load deck suggestions for current format."""
        from mtg_core.tools.recommendations.deck_finder import CardData, get_deck_finder

        finder = get_deck_finder()

        # Convert card info to CardData
        card_data = [
            CardData(
                name=c.name,
                type_line=c.type_line,
                colors=c.colors,
                mana_cost=c.mana_cost,
                text=c.text,
                color_identity=c.color_identity,
            )
            for c in self._card_info_list
        ]

        self._suggestions = finder.find_buildable_decks(
            self._collection_cards,
            format=self._current_format,
            card_data=card_data,
            min_completion=0.1,
            limit=20,
        )

        self._populate_list()

    def _populate_list(self) -> None:
        """Populate the suggestions list."""
        try:
            list_view = self.query_one("#suggestions-list", ListView)
            # Clear existing items
            list_view.clear()

            if not self._suggestions:
                list_view.append(
                    ListItem(
                        Static(
                            f"[{ui_colors.TEXT_DIM}]No {self._current_format} decks found.\n\n"
                            "Add more legendary creatures or tribal cards![/]",
                            id="empty-state",
                        )
                    )
                )
                self._selected_suggestion = None
                return

            for suggestion in self._suggestions:
                content = self._format_suggestion(suggestion)
                item = SuggestionListItem(suggestion, content)
                list_view.append(item)

            # Force refresh
            list_view.refresh(layout=True)

            if self._suggestions:
                list_view.index = 0
                self._selected_suggestion = self._suggestions[0]

        except Exception as e:
            self.notify(f"ERROR populating list: {e}", severity="error", timeout=10)

    def _format_suggestion(self, s: DeckSuggestion) -> str:
        """Format a suggestion for display."""
        # Color indicators
        color_str = " ".join(s.colors) if s.colors else ""

        # Completion bar
        bar_width = 12
        filled = int(s.completion_pct * bar_width)
        bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
        pct = int(s.completion_pct * 100)

        # Score color
        if s.completion_pct >= 0.7:
            score_color = ui_colors.SYNERGY_STRONG
        elif s.completion_pct >= 0.5:
            score_color = ui_colors.SYNERGY_MODERATE
        elif s.completion_pct >= 0.3:
            score_color = ui_colors.SYNERGY_WEAK
        else:
            score_color = ui_colors.TEXT_DIM

        lines = []

        # Line 1: Name + Colors + Score
        line1 = f"[bold {ui_colors.GOLD}]{s.name}[/]"
        if color_str:
            line1 += f"  {color_str}"
        line1 += f"  [{score_color}]{bar} {pct}%[/]"
        lines.append(line1)

        # Line 2: Commander or archetype
        if s.commander and s.commander != s.name:
            lines.append(f"  [green]★ Commander:[/] {s.commander}")
        elif s.archetype:
            lines.append(f"  [{ui_colors.TEXT_DIM}]{s.archetype}[/]")

        # Card counts section with clearer split
        owned_count = len(s.key_cards_owned) if s.key_cards_owned else 0
        missing_count = len(s.key_cards_missing) if s.key_cards_missing else 0

        lines.append("")
        lines.append(f"  [bold green]✓ OWNED ({owned_count})[/]")
        # Show first few owned card names
        if s.key_cards_owned:
            shown = s.key_cards_owned[:5]
            for card in shown:
                lines.append(f"    [{ui_colors.TEXT_DIM}]{card}[/]")
            if len(s.key_cards_owned) > 5:
                lines.append(f"    [{ui_colors.TEXT_DIM}]... +{len(s.key_cards_owned) - 5} more[/]")

        if missing_count > 0:
            lines.append("")
            lines.append(f"  [bold yellow]⚠ NEEDED ({missing_count})[/]")
            # Count duplicates in missing cards
            from collections import Counter

            missing_counts = Counter(s.key_cards_missing)
            for card, qty in list(missing_counts.items())[:5]:
                qty_str = f" x{qty}" if qty > 1 else ""
                lines.append(f"    [{ui_colors.TEXT_DIM}]{card}{qty_str}[/]")
            if len(missing_counts) > 5:
                lines.append(f"    [{ui_colors.TEXT_DIM}]... +{len(missing_counts) - 5} more[/]")

        return "\n".join(lines)

    def _render_statusbar(self) -> str:
        """Render status bar."""
        parts = [
            f"[{ui_colors.GOLD}]c[/]:Commander",
            f"[{ui_colors.GOLD}]s[/]:Standard",
            f"[{ui_colors.GOLD}]Enter[/]:Create Deck",
            f"[{ui_colors.GOLD}]Esc[/]:Back",
        ]
        return "  ".join(parts)

    @on(ListView.Highlighted, "#suggestions-list")
    def on_suggestion_highlighted(self, event: ListView.Highlighted) -> None:
        """Track selected suggestion."""
        if isinstance(event.item, SuggestionListItem):
            self._selected_suggestion = event.item.suggestion

    @on(ListView.Selected, "#suggestions-list")
    def on_suggestion_selected(self, event: ListView.Selected) -> None:
        """Create deck when Enter pressed on suggestion."""
        if isinstance(event.item, SuggestionListItem):
            self._selected_suggestion = event.item.suggestion
            self.action_create_deck()

    @on(Button.Pressed, "#btn-commander")
    def on_commander_btn(self) -> None:
        self._switch_format("commander")

    @on(Button.Pressed, "#btn-standard")
    def on_standard_btn(self) -> None:
        self._switch_format("standard")

    def _switch_format(self, fmt: str) -> None:
        """Switch format and reload."""
        if self._current_format == fmt:
            return

        self._current_format = fmt

        try:
            cmd_btn = self.query_one("#btn-commander", Button)
            std_btn = self.query_one("#btn-standard", Button)

            if fmt == "commander":
                cmd_btn.add_class("-active")
                std_btn.remove_class("-active")
            else:
                std_btn.add_class("-active")
                cmd_btn.remove_class("-active")
        except NoMatches:
            pass

        self._load_suggestions()

    def action_close(self) -> None:
        """Close screen."""
        self.dismiss(None)

    def action_show_commander(self) -> None:
        self._switch_format("commander")

    def action_show_standard(self) -> None:
        self._switch_format("standard")

    def action_nav_up(self) -> None:
        with contextlib.suppress(NoMatches):
            self.query_one("#suggestions-list", ListView).action_cursor_up()

    def action_nav_down(self) -> None:
        with contextlib.suppress(NoMatches):
            self.query_one("#suggestions-list", ListView).action_cursor_down()

    def action_page_up(self) -> None:
        with contextlib.suppress(NoMatches):
            self.query_one("#suggestions-list", ListView).action_page_up()

    def action_page_down(self) -> None:
        with contextlib.suppress(NoMatches):
            self.query_one("#suggestions-list", ListView).action_page_down()

    def action_create_deck(self) -> None:
        """Create deck from selected suggestion."""
        if not self._selected_suggestion:
            self.notify("Select a deck first", severity="warning")
            return

        s = self._selected_suggestion

        if not s.key_cards_owned and not s.key_cards_missing:
            self.notify("No cards in this suggestion", severity="warning")
            return

        result = CreateDeckResult(
            deck_name=s.name,
            card_names=s.key_cards_owned,
            cards_missing=s.key_cards_missing if s.key_cards_missing else None,
            commander=s.commander,
            format_type=self._current_format,
        )
        self.dismiss(result)
