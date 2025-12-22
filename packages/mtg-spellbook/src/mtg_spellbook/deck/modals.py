"""Modal dialogs for deck management."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static

from ..ui.theme import ui_colors

if TYPE_CHECKING:
    from mtg_core.data.database import DeckSummary


class NewDeckModal(ModalScreen[int | None]):
    """Modal for creating a new deck."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,q", "cancel", "Cancel"),
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
            yield Label(f"[bold {ui_colors.GOLD_DIM}]Create New Deck[/]")
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
        Binding("escape,q", "cancel", "Cancel"),
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


class AddToDeckModal(ModalScreen[tuple[int, int, bool] | None]):
    """Modal for adding a card to a deck."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,q", "cancel", "Cancel"),
    ]

    CSS = """
    AddToDeckModal {
        align: center middle;
    }

    #add-to-deck-dialog {
        width: 60;
        height: auto;
        max-height: 40;
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

    #qty-row {
        height: auto;
        width: 100%;
        align: left middle;
        margin-bottom: 1;
    }

    #qty-buttons {
        height: auto;
        width: auto;
        margin-left: 2;
    }

    .qty-btn {
        width: 5;
        min-width: 5;
        height: 3;
        margin: 0 1 0 0;
        background: #2a2a4e;
        color: #e0e0e0;
        border: solid #3d3d3d;
        text-style: bold;
    }

    .qty-btn:hover {
        background: #3a3a5e;
        border: solid #5d5d7d;
    }

    .qty-btn:focus {
        border: solid #c9a227;
    }

    .qty-btn.-selected {
        background: #c9a227;
        color: #0d0d0d;
        border: solid #e6c84a;
    }

    #sideboard-checkbox {
        margin: 1 0;
    }

    #preview-section {
        height: auto;
        width: 100%;
        background: #1a1a2e;
        border: round #3d3d3d;
        padding: 1;
        margin: 1 0;
    }

    .preview-label {
        height: auto;
        width: 100%;
        color: #888;
    }

    .preview-value {
        height: auto;
        width: 100%;
        color: #e6c84a;
    }

    #add-buttons {
        margin-top: 1;
        height: auto;
    }

    #add-buttons Button {
        margin-right: 1;
    }
    """

    def __init__(
        self,
        card_name: str,
        decks: list[DeckSummary],
        current_qty: int = 0,
        current_sideboard_qty: int = 0,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> None:
        super().__init__()
        self.card_name = card_name
        self.decks = decks
        self.current_qty = current_qty
        self.current_sideboard_qty = current_sideboard_qty
        self.set_code = set_code
        self.collector_number = collector_number
        self._selected_deck_id: int | None = self.decks[0].id if self.decks else None

    def compose(self) -> ComposeResult:
        with Vertical(id="add-to-deck-dialog"):
            yield Label(f"[bold {ui_colors.GOLD_DIM}]Add to Deck[/]")
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
            with Horizontal(id="qty-row"):
                yield Input(value="4", id="qty-input", type="integer")
                with Horizontal(id="qty-buttons"):
                    yield Button("1", id="qty-1", classes="qty-btn")
                    yield Button("2", id="qty-2", classes="qty-btn")
                    yield Button("3", id="qty-3", classes="qty-btn")
                    yield Button("4", id="qty-4", classes="qty-btn -selected")
            yield Checkbox("Add to Sideboard", id="sideboard-checkbox")
            with Vertical(id="preview-section"):
                yield Static("", id="card-preview", classes="preview-value")
                yield Static("", id="deck-preview", classes="preview-value")
            with Horizontal(id="add-buttons"):
                yield Button("Add", variant="primary", id="add-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        """Initialize preview after mount."""
        self._update_preview()
        if self.decks:
            self._load_deck_info(self.decks[0].id)

    def _get_current_deck_info(self) -> tuple[int, int] | None:
        """Get current card counts for selected deck."""
        if not self._selected_deck_id:
            return None
        deck = next((d for d in self.decks if d.id == self._selected_deck_id), None)
        if deck:
            return (deck.card_count, deck.sideboard_count)
        return None

    def _load_deck_info(self, deck_id: int) -> None:
        """Load card info for selected deck (async via call_later)."""
        self._selected_deck_id = deck_id
        self._update_preview()

    def _update_preview(self) -> None:
        """Update the live preview labels."""
        try:
            qty_input = self.query_one("#qty-input", Input)
            qty = int(qty_input.value) if qty_input.value.isdigit() else 0
        except Exception:
            qty = 0

        try:
            sideboard_cb = self.query_one("#sideboard-checkbox", Checkbox)
            is_sideboard = sideboard_cb.value
        except Exception:
            is_sideboard = False

        current = self.current_sideboard_qty if is_sideboard else self.current_qty
        new_total = current + qty
        location = "sideboard" if is_sideboard else "mainboard"

        try:
            card_preview = self.query_one("#card-preview", Static)
            card_preview.update(
                f"Card: [dim]{current}x[/] -> [bold {ui_colors.GOLD_DIM}]{new_total}x[/] "
                f"[dim]({location})[/]"
            )
        except Exception:
            pass

        deck_info = self._get_current_deck_info()
        if deck_info:
            main_count, sb_count = deck_info
            if is_sideboard:
                new_sb = sb_count + qty
                deck_text = f"Deck: {main_count} main / [dim]{sb_count}[/] -> [bold {ui_colors.GOLD_DIM}]{new_sb}[/] side"
            else:
                new_main = main_count + qty
                deck_text = f"Deck: [dim]{main_count}[/] -> [bold {ui_colors.GOLD_DIM}]{new_main}[/] main / {sb_count} side"
            try:
                deck_preview = self.query_one("#deck-preview", Static)
                deck_preview.update(deck_text)
            except Exception:
                pass

    def _update_qty_button_selection(self, selected_qty: int) -> None:
        """Update visual selection state of quantity buttons."""
        for i in range(1, 5):
            try:
                btn = self.query_one(f"#qty-{i}", Button)
                if i == selected_qty:
                    btn.add_class("-selected")
                else:
                    btn.remove_class("-selected")
            except Exception:
                pass

    def on_key(self, event: Key) -> None:
        """Handle number key presses for quick quantity selection."""
        if event.key in ("1", "2", "3", "4"):
            qty = int(event.key)
            try:
                qty_input = self.query_one("#qty-input", Input)
                qty_input.value = str(qty)
                self._update_qty_button_selection(qty)
                self._update_preview()
            except Exception:
                pass
            event.stop()

    @on(Button.Pressed, ".qty-btn")
    def on_qty_button(self, event: Button.Pressed) -> None:
        """Handle quick quantity button press."""
        btn_id = event.button.id
        if btn_id and btn_id.startswith("qty-"):
            qty = int(btn_id.split("-")[1])
            try:
                qty_input = self.query_one("#qty-input", Input)
                qty_input.value = str(qty)
                self._update_qty_button_selection(qty)
                self._update_preview()
            except Exception:
                pass

    @on(Input.Changed, "#qty-input")
    def on_qty_changed(self, event: Input.Changed) -> None:
        """Handle quantity input changes."""
        try:
            qty = int(event.value) if event.value.isdigit() else 0
            if qty in (1, 2, 3, 4):
                self._update_qty_button_selection(qty)
            else:
                for i in range(1, 5):
                    try:
                        btn = self.query_one(f"#qty-{i}", Button)
                        btn.remove_class("-selected")
                    except Exception:
                        pass
        except Exception:
            pass
        self._update_preview()

    @on(Checkbox.Changed, "#sideboard-checkbox")
    def on_sideboard_changed(self, _event: Checkbox.Changed) -> None:
        """Handle sideboard checkbox change."""
        self._update_preview()

    @on(Select.Changed, "#deck-select")
    def on_deck_changed(self, event: Select.Changed) -> None:
        """Handle deck selection change."""
        if event.value != Select.BLANK and isinstance(event.value, int):
            self._load_deck_info(event.value)

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
        sideboard_cb = self.query_one("#sideboard-checkbox", Checkbox)

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

        is_sideboard = sideboard_cb.value

        deck_manager = await self.app._ctx.get_deck_manager()  # type: ignore
        if deck_manager:
            result = await deck_manager.add_card(
                deck_id,
                self.card_name,
                quantity,
                sideboard=is_sideboard,
                set_code=self.set_code,
                collector_number=self.collector_number,
            )
            if result.success:
                deck_name = next((d.name for d in self.decks if d.id == deck_id), "deck")
                location = " (sideboard)" if is_sideboard else ""
                self.app.notify(f"Added {quantity}x {self.card_name} to {deck_name}{location}")
                self.dismiss((deck_id, quantity, is_sideboard))
            else:
                self.app.notify(result.error or "Failed to add card", severity="error")
                self.dismiss(None)
        else:
            self.app.notify("Could not add card", severity="error")
            self.dismiss(None)
