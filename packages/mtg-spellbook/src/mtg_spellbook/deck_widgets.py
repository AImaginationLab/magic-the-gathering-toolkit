"""Deck management widgets for the MTG Spellbook TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Select, Static

from .formatting import prettify_mana

if TYPE_CHECKING:
    from mtg_core.data.database import DeckSummary

    from .deck_manager import DeckManager, DeckWithCards


# ─────────────────────────────────────────────────────────────────────────────
# Messages
# ─────────────────────────────────────────────────────────────────────────────


class DeckSelected(Message):
    """Message sent when a deck is selected."""

    def __init__(self, deck_id: int) -> None:
        super().__init__()
        self.deck_id = deck_id


class DeckCreated(Message):
    """Message sent when a new deck is created."""

    def __init__(self, deck_id: int, name: str) -> None:
        super().__init__()
        self.deck_id = deck_id
        self.name = name


class AddToDeckRequested(Message):
    """Message sent when user wants to add a card to a deck."""

    def __init__(self, card_name: str) -> None:
        super().__init__()
        self.card_name = card_name


class CardAddedToDeck(Message):
    """Message sent when a card is added to a deck."""

    def __init__(self, card_name: str, deck_name: str, quantity: int) -> None:
        super().__init__()
        self.card_name = card_name
        self.deck_name = deck_name
        self.quantity = quantity


# ─────────────────────────────────────────────────────────────────────────────
# Deck List Widget
# ─────────────────────────────────────────────────────────────────────────────


class DeckListItem(ListItem):
    """A single deck in the list."""

    def __init__(self, deck: DeckSummary) -> None:
        super().__init__()
        self.deck = deck

    def compose(self) -> ComposeResult:
        format_str = f" · {self.deck.format}" if self.deck.format else ""
        yield Static(
            f"[bold]{self.deck.name}[/]\n"
            f"[dim]{self.deck.card_count} cards{format_str}[/]"
        )


class DeckListPanel(Vertical):
    """Panel showing list of user's decks."""

    BINDINGS: ClassVar[list[Binding]] = [
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
            deck_list.append(
                ListItem(Static("[dim]No decks yet. Press N to create one.[/]"))
            )
        else:
            for deck in self._decks:
                deck_list.append(DeckListItem(deck))

    def action_new_deck(self) -> None:
        """Create a new deck."""
        self.app.push_screen(NewDeckModal())

    def action_delete_deck(self) -> None:
        """Delete the selected deck."""
        deck_list = self.query_one("#deck-list", ListView)
        if deck_list.highlighted_child and isinstance(
            deck_list.highlighted_child, DeckListItem
        ):
            deck = deck_list.highlighted_child.deck
            self.app.push_screen(
                ConfirmDeleteModal(deck.id, deck.name),
                callback=self._on_delete_confirmed,
            )

    def _on_delete_confirmed(self, deleted: bool) -> None:
        """Called after delete confirmation."""
        if deleted:
            self.post_message(DeckSelected(-1))  # Signal to refresh

    def action_open_deck(self) -> None:
        """Open the selected deck."""
        deck_list = self.query_one("#deck-list", ListView)
        if deck_list.highlighted_child and isinstance(
            deck_list.highlighted_child, DeckListItem
        ):
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


# ─────────────────────────────────────────────────────────────────────────────
# Deck Editor Widget
# ─────────────────────────────────────────────────────────────────────────────


class DeckCardItem(ListItem):
    """A single card in the deck editor."""

    def __init__(self, card_name: str, quantity: int, mana_cost: str | None = None) -> None:
        super().__init__()
        self.card_name = card_name
        self.quantity = quantity
        self.mana_cost = mana_cost

    def compose(self) -> ComposeResult:
        mana = prettify_mana(self.mana_cost) if self.mana_cost else ""
        yield Static(f"{self.quantity}x {self.card_name}  {mana}")


class DeckEditorPanel(Vertical):
    """Panel for editing a deck."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("plus", "increase_qty", "+1"),
        Binding("equal", "increase_qty", "+1"),  # Same key without shift
        Binding("minus", "decrease_qty", "-1"),
        Binding("s", "toggle_sideboard", "Sideboard"),
        Binding("delete", "remove_card", "Remove"),
        Binding("backspace", "back_to_list", "Back"),
        Binding("v", "validate", "Validate"),
    ]

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._deck: DeckWithCards | None = None

    def compose(self) -> ComposeResult:
        yield Static("[bold]No deck loaded[/]", id="deck-editor-header")
        with Horizontal(id="deck-editor-content"):
            with Vertical(id="deck-cards-container"):
                yield Static("[#c9a227]Mainboard[/]", id="mainboard-header")
                yield ListView(id="mainboard-list")
                yield Static("[#c9a227]Sideboard[/]", id="sideboard-header")
                yield ListView(id="sideboard-list")
            with Vertical(id="deck-stats-container"):
                yield Static("[dim]Stats[/]", id="deck-stats")
        yield Static(
            "[dim][+/-] Qty · [S] Sideboard · [Del] Remove · [V] Validate · [Backspace] Back[/]",
            id="deck-editor-footer",
        )

    def update_deck(self, deck: DeckWithCards | None) -> None:
        """Update the displayed deck."""
        self._deck = deck

        header = self.query_one("#deck-editor-header", Static)
        mainboard = self.query_one("#mainboard-list", ListView)
        sideboard = self.query_one("#sideboard-list", ListView)
        stats = self.query_one("#deck-stats", Static)

        mainboard.clear()
        sideboard.clear()

        if deck is None:
            header.update("[bold]No deck loaded[/]")
            stats.update("[dim]No stats[/]")
            return

        # Update header
        format_str = f" ({deck.format})" if deck.format else ""
        header.update(f"[bold #c9a227]{deck.name}[/]{format_str}")

        # Populate mainboard
        for card in sorted(deck.mainboard, key=lambda c: c.card_name):
            mana_cost = card.card.mana_cost if card.card else None
            mainboard.append(DeckCardItem(card.card_name, card.quantity, mana_cost))

        # Populate sideboard
        for card in sorted(deck.sideboard, key=lambda c: c.card_name):
            mana_cost = card.card.mana_cost if card.card else None
            sideboard.append(DeckCardItem(card.card_name, card.quantity, mana_cost))

        # Update stats
        stats.update(self._render_stats(deck))

    def _render_stats(self, deck: DeckWithCards) -> str:
        """Render deck stats."""
        lines = [
            f"[bold]Cards:[/] {deck.mainboard_count}/60",
            f"[bold]Sideboard:[/] {deck.sideboard_count}/15",
            "",
        ]

        # Simple mana curve
        curve: dict[int, int] = {}
        for card in deck.mainboard:
            if card.card:
                cmc = int(card.card.mana_value or 0)
                curve[cmc] = curve.get(cmc, 0) + card.quantity

        if curve:
            lines.append("[bold]Mana Curve:[/]")
            max_count = max(curve.values()) if curve else 1
            for cmc in range(min(curve.keys() or [0]), max(curve.keys() or [0]) + 1):
                count = curve.get(cmc, 0)
                bar_len = int((count / max_count) * 8) if max_count > 0 else 0
                bar = "█" * bar_len
                lines.append(f"[dim]{cmc}:[/] {bar} {count}")

        return "\n".join(lines)

    def action_back_to_list(self) -> None:
        """Go back to deck list."""
        self.post_message(DeckSelected(-1))

    def action_validate(self) -> None:
        """Validate the deck."""
        if self._deck:
            self.app.notify(f"Validating {self._deck.name}...")
            # TODO: Actually run validation


# ─────────────────────────────────────────────────────────────────────────────
# Modals
# ─────────────────────────────────────────────────────────────────────────────


class NewDeckModal(ModalScreen[int | None]):
    """Modal for creating a new deck."""

    BINDINGS: ClassVar[list[Binding]] = [
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

        # Create deck via app's deck manager
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

    BINDINGS: ClassVar[list[Binding]] = [
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
        # Delete via app's deck manager
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

    BINDINGS: ClassVar[list[Binding]] = [
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

        try:
            quantity = int(qty_input.value)
            if quantity < 1:
                quantity = 1
        except ValueError:
            quantity = 4

        # Add via app's deck manager
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
