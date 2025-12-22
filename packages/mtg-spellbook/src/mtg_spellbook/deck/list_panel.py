"""Deck list panel widget."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Button, ListItem, ListView, Static

from ..ui.theme import ui_colors
from .messages import DeckSelected
from .modals import ConfirmDeleteModal, NewDeckModal

if TYPE_CHECKING:
    from mtg_core.data.database import DeckSummary

    from ..deck_manager import DeckManager


class DeckListItem(ListItem):
    """A single deck in the list."""

    def __init__(self, deck: DeckSummary, is_active: bool = False) -> None:
        super().__init__()
        self.deck = deck
        self.is_active = is_active

    def compose(self) -> ComposeResult:
        format_str = f" · {self.deck.format}" if self.deck.format else ""
        active_marker = f"[{ui_colors.GOLD}]>[/] " if self.is_active else "  "
        yield Static(
            f"{active_marker}[bold]{self.deck.name}[/]\n"
            f"   [dim]{self.deck.card_count} cards{format_str}[/]"
        )


class DeckListPanel(Vertical):
    """Panel showing list of user's decks."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("n", "new_deck", "New Deck"),
        Binding("d", "delete_deck", "Delete"),
        Binding("enter", "open_deck", "Open"),
    ]

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._decks: list[DeckSummary] = []
        self._active_deck_id: int | None = None

    def compose(self) -> ComposeResult:
        yield Static(f"[bold {ui_colors.GOLD_DIM}]My Decks[/]", id="deck-list-header")
        yield Button("+ New Deck", id="new-deck-btn", variant="primary")
        yield ListView(id="deck-list")
        yield Static(
            "[dim][N] New [Enter] Open [D] Delete[/]",
            id="deck-list-footer",
        )

    def set_active_deck(self, deck_id: int | None) -> None:
        """Set which deck is currently active/open in editor."""
        self._active_deck_id = deck_id

    async def refresh_decks(
        self, deck_manager: DeckManager, active_deck_id: int | None = None
    ) -> None:
        """Refresh the deck list from database."""
        if active_deck_id is not None:
            self._active_deck_id = active_deck_id

        self._decks = await deck_manager.list_decks()
        deck_list = self.query_one("#deck-list", ListView)
        deck_list.clear()

        if not self._decks:
            deck_list.append(ListItem(Static("[dim]No decks yet. Press N to create one.[/]")))
        else:
            for deck in self._decks:
                is_active = deck.id == self._active_deck_id
                deck_list.append(DeckListItem(deck, is_active=is_active))

    def action_new_deck(self) -> None:
        """Create a new deck."""
        self.app.push_screen(NewDeckModal())

    def action_delete_deck(self) -> None:
        """Delete the selected deck."""
        deck_list = self.query_one("#deck-list", ListView)
        if deck_list.highlighted_child and isinstance(deck_list.highlighted_child, DeckListItem):
            deck = deck_list.highlighted_child.deck
            self.app.push_screen(
                ConfirmDeleteModal(deck.id, deck.name),
                callback=self._on_delete_confirmed,
            )

    def _on_delete_confirmed(self, deleted: bool | None) -> None:
        """Called after delete confirmation."""
        if deleted:
            self.post_message(DeckSelected(-1))

    def action_open_deck(self) -> None:
        """Open the selected deck."""
        deck_list = self.query_one("#deck-list", ListView)
        if deck_list.highlighted_child and isinstance(deck_list.highlighted_child, DeckListItem):
            deck = deck_list.highlighted_child.deck
            self.post_message(DeckSelected(deck.id))

    @on(Button.Pressed, "#new-deck-btn")
    def on_new_deck_button(self) -> None:
        """Handle new deck button click."""
        self.action_new_deck()

    @on(ListView.Selected, "#deck-list")
    def on_deck_selected(self, event: ListView.Selected) -> None:
        """Handle deck selection."""
        if event.item and isinstance(event.item, DeckListItem):
            self.post_message(DeckSelected(event.item.deck.id))
