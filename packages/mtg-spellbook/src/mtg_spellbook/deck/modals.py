"""Modal dialogs for deck management."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

if TYPE_CHECKING:
    from mtg_core.data.database import DeckSummary


class NewDeckModal(ModalScreen[int | None]):
    """Modal for creating a new deck."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape", "cancel", "Cancel"),
    ]

    CSS = """
    NewDeckModal {
        align: center middle;
    }

    #new-deck-dialog {
        width: 50;
        height: auto;
        max-height: 20;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    #new-deck-dialog Label {
        margin-bottom: 1;
    }

    #new-deck-dialog Input {
        margin-bottom: 1;
    }

    #new-deck-dialog Select {
        margin-bottom: 1;
    }

    #new-deck-buttons {
        margin-top: 1;
        height: auto;
    }

    #new-deck-buttons Button {
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="new-deck-dialog"):
            yield Label("[bold #c9a227]Create New Deck[/]")
            yield Label("Name:")
            yield Input(placeholder="My Awesome Deck", id="deck-name-input")
            yield Label("Format:")
            yield Select(
                [
                    ("Any", None),
                    ("Standard", "standard"),
                    ("Modern", "modern"),
                    ("Legacy", "legacy"),
                    ("Vintage", "vintage"),
                    ("Commander", "commander"),
                    ("Pioneer", "pioneer"),
                    ("Pauper", "pauper"),
                ],
                id="format-select",
                value=None,
            )
            with Horizontal(id="new-deck-buttons"):
                yield Button("Create", variant="primary", id="create-btn")
                yield Button("Cancel", id="cancel-btn")

    def action_cancel(self) -> None:
        """Cancel deck creation."""
        self.dismiss(None)

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        """Handle cancel button."""
        self.dismiss(None)

    @on(Button.Pressed, "#create-btn")
    async def on_create(self) -> None:
        """Handle create button."""
        name_input = self.query_one("#deck-name-input", Input)
        format_select = self.query_one("#format-select", Select)

        name = name_input.value.strip()
        if not name:
            self.app.notify("Please enter a deck name", severity="error")
            return

        format_val = format_select.value if format_select.value != Select.BLANK else None

        deck_manager = await self.app._ctx.get_deck_manager()  # type: ignore
        if deck_manager:
            deck_id = await deck_manager.create_deck(name, format_val)
            self.app.notify(f"Created deck: {name}")
            self.dismiss(deck_id)
        else:
            self.app.notify("Could not create deck", severity="error")
            self.dismiss(None)

    @on(Input.Submitted, "#deck-name-input")
    async def on_name_submitted(self) -> None:
        """Handle enter in name input."""
        await self.on_create()


class ConfirmDeleteModal(ModalScreen[bool]):
    """Modal for confirming deck deletion."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape", "cancel", "Cancel"),
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
    ]

    CSS = """
    ConfirmDeleteModal {
        align: center middle;
    }

    #confirm-dialog {
        width: 50;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $error;
    }

    #confirm-buttons {
        margin-top: 1;
        height: auto;
    }

    #confirm-buttons Button {
        margin-right: 1;
    }
    """

    def __init__(self, deck_id: int, deck_name: str) -> None:
        super().__init__()
        self.deck_id = deck_id
        self.deck_name = deck_name

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label("[bold red]Delete deck?[/]")
            yield Label(f"[bold]{self.deck_name}[/]")
            yield Label("[dim]This cannot be undone.[/]")
            with Horizontal(id="confirm-buttons"):
                yield Button("Delete", variant="error", id="delete-btn")
                yield Button("Cancel", id="cancel-btn")

    def action_cancel(self) -> None:
        """Cancel deletion."""
        self.dismiss(False)

    def action_confirm(self) -> None:
        """Confirm deletion."""
        self._do_delete()

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        """Handle cancel button."""
        self.dismiss(False)

    @on(Button.Pressed, "#delete-btn")
    def on_delete(self) -> None:
        """Handle delete button."""
        self._do_delete()

    def _do_delete(self) -> None:
        """Actually delete the deck."""

        async def delete() -> None:
            try:
                deck_manager = await self.app._ctx.get_deck_manager()  # type: ignore
                if deck_manager:
                    await deck_manager.delete_deck(self.deck_id)
                    self.app.notify(f"Deleted deck: {self.deck_name}")
                    self.dismiss(True)
                else:
                    self.app.notify("Deck manager not available", severity="error")
                    self.dismiss(False)
            except Exception as e:
                self.app.notify(f"Failed to delete deck: {e}", severity="error")
                self.dismiss(False)

        self.app.call_later(delete)


class AddToDeckModal(ModalScreen[tuple[int, int] | None]):
    """Modal for adding a card to a deck."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape", "cancel", "Cancel"),
    ]

    CSS = """
    AddToDeckModal {
        align: center middle;
    }

    #add-to-deck-dialog {
        width: 50;
        height: auto;
        max-height: 25;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    #add-to-deck-dialog Label {
        margin-bottom: 1;
    }

    #add-to-deck-dialog Input {
        margin-bottom: 1;
        width: 10;
    }

    #add-to-deck-dialog Select {
        margin-bottom: 1;
    }

    #add-buttons {
        margin-top: 1;
        height: auto;
    }

    #add-buttons Button {
        margin-right: 1;
    }
    """

    def __init__(self, card_name: str, decks: list[DeckSummary]) -> None:
        super().__init__()
        self.card_name = card_name
        self.decks = decks

    def compose(self) -> ComposeResult:
        with Vertical(id="add-to-deck-dialog"):
            yield Label("[bold #c9a227]Add to Deck[/]")
            yield Label(f"[bold]{self.card_name}[/]")
            yield Label("Deck:")
            if self.decks:
                yield Select(
                    [(d.name, d.id) for d in self.decks],
                    id="deck-select",
                    value=self.decks[0].id if self.decks else Select.BLANK,
                )
            else:
                yield Static("[dim]No decks. Create one first.[/]")
            yield Label("Quantity:")
            yield Input(value="4", id="qty-input", type="integer")
            with Horizontal(id="add-buttons"):
                yield Button("Add", variant="primary", id="add-btn")
                yield Button("Cancel", id="cancel-btn")

    def action_cancel(self) -> None:
        """Cancel adding."""
        self.dismiss(None)

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        """Handle cancel button."""
        self.dismiss(None)

    @on(Button.Pressed, "#add-btn")
    async def on_add(self) -> None:
        """Handle add button."""
        if not self.decks:
            self.dismiss(None)
            return

        deck_select = self.query_one("#deck-select", Select)
        qty_input = self.query_one("#qty-input", Input)

        deck_id = deck_select.value
        if deck_id == Select.BLANK:
            self.app.notify("Please select a deck", severity="error")
            return
        assert isinstance(deck_id, int)

        try:
            quantity = int(qty_input.value)
            if quantity < 1:
                quantity = 1
        except ValueError:
            quantity = 4

        deck_manager = await self.app._ctx.get_deck_manager()  # type: ignore
        if deck_manager:
            result = await deck_manager.add_card(deck_id, self.card_name, quantity)
            if result.success:
                deck_name = next((d.name for d in self.decks if d.id == deck_id), "deck")
                self.app.notify(f"Added {quantity}x {self.card_name} to {deck_name}")
                self.dismiss((deck_id, quantity))
            else:
                self.app.notify(result.error or "Failed to add card", severity="error")
                self.dismiss(None)
        else:
            self.app.notify("Could not add card", severity="error")
            self.dismiss(None)
