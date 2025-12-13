"""Deck list panel widget."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Button, ListItem, ListView, Static

from .messages import DeckSelected
from .modals import ConfirmDeleteModal, NewDeckModal

if TYPE_CHECKING:
    from mtg_core.data.database import DeckSummary

    from ..deck_manager import DeckManager


class DeckListItem(ListItem):
    """A single deck in the list."""

    def __init__(self, deck: DeckSummary) -> None:
        super().__init__()
        self.deck = deck

    def compose(self) -> ComposeResult:
        format_str = f" · {self.deck.format}" if self.deck.format else ""
        yield Static(f"[bold]{self.deck.name}[/]\n[dim]{self.deck.card_count} cards{format_str}[/]")


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

    def compose(self) -> ComposeResult:
        yield Static("[bold #c9a227]My Decks[/]", id="deck-list-header")
        yield Button("+ New Deck", id="new-deck-btn", variant="primary")
        yield ListView(id="deck-list")
        yield Static(
            "[dim][N] New · [Enter] Open · [D] Delete[/]",
            id="deck-list-footer",
        )

    async def refresh_decks(self, deck_manager: DeckManager) -> None:
        """Refresh the deck list from database."""
        self._decks = await deck_manager.list_decks()
        deck_list = self.query_one("#deck-list", ListView)
        deck_list.clear()

        if not self._decks:
            deck_list.append(ListItem(Static("[dim]No decks yet. Press N to create one.[/]")))
        else:
            for deck in self._decks:
                deck_list.append(DeckListItem(deck))

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
