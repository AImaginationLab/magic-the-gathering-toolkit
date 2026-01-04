"""Modal dialogs for collection management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, ListItem, ListView, Select, Static

from mtg_core.tools.recommendations import DeckSuggestion

from ..ui.theme import ui_colors


class AddToCollectionResult:
    """Result from AddToCollectionModal."""

    def __init__(
        self,
        card_name: str | None,
        quantity: int,
        foil: bool,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> None:
        self.card_name = card_name
        self.quantity = quantity
        self.foil = foil
        self.set_code = set_code
        self.collector_number = collector_number


class AddToCollectionModal(ModalScreen[AddToCollectionResult | None]):
    """Modal for adding a card to the collection."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,q", "cancel", "Cancel"),
    ]

    CSS = """
    AddToCollectionModal {
        align: center middle;
    }

    #add-collection-dialog {
        width: 60;
        height: auto;
        max-height: 25;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    #add-collection-dialog Label {
        margin-bottom: 1;
    }

    #add-collection-dialog Input {
        margin-bottom: 1;
    }

    #card-name-input {
        width: 100%;
    }

    #qty-row {
        height: auto;
        width: 100%;
        align: left middle;
        margin-bottom: 1;
    }

    #qty-input {
        width: 10;
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

    #foil-checkbox {
        margin: 1 0;
    }

    #add-collection-buttons {
        margin-top: 1;
        height: auto;
    }

    #add-collection-buttons Button {
        margin-right: 1;
    }
    """

    def __init__(self, card_name: str | None = None) -> None:
        """Initialize the modal.

        Args:
            card_name: Optional pre-filled card name
        """
        super().__init__()
        self._initial_card_name = card_name or ""

    def compose(self) -> ComposeResult:
        with Vertical(id="add-collection-dialog"):
            yield Label(f"[bold {ui_colors.GOLD_DIM}]Add to Collection[/]")
            yield Label("Card Name:")
            yield Input(
                value=self._initial_card_name,
                placeholder="Lightning Bolt",
                id="card-name-input",
            )
            yield Label("Quantity:")
            with Horizontal(id="qty-row"):
                yield Input(value="1", id="qty-input", type="integer")
                with Horizontal(id="qty-buttons"):
                    yield Button("1", id="qty-1", classes="qty-btn -selected")
                    yield Button("2", id="qty-2", classes="qty-btn")
                    yield Button("3", id="qty-3", classes="qty-btn")
                    yield Button("4", id="qty-4", classes="qty-btn")
            yield Checkbox("Foil", id="foil-checkbox")
            with Horizontal(id="add-collection-buttons"):
                yield Button("Add", variant="primary", id="add-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        """Focus the card name input on mount."""
        if not self._initial_card_name:
            self.query_one("#card-name-input", Input).focus()
        else:
            self.query_one("#qty-input", Input).focus()

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
        # Only handle if not focused on card name input
        focused = self.focused
        if focused and focused.id == "card-name-input":
            return

        if event.key in ("1", "2", "3", "4"):
            qty = int(event.key)
            try:
                qty_input = self.query_one("#qty-input", Input)
                qty_input.value = str(qty)
                self._update_qty_button_selection(qty)
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
                # Clear selection for quantities outside 1-4
                for i in range(1, 5):
                    try:
                        btn = self.query_one(f"#qty-{i}", Button)
                        btn.remove_class("-selected")
                    except Exception:
                        pass
        except Exception:
            pass

    def action_cancel(self) -> None:
        """Cancel adding."""
        self.dismiss(None)

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        """Handle cancel button."""
        self.dismiss(None)

    @on(Button.Pressed, "#add-btn")
    def on_add(self) -> None:
        """Handle add button."""
        self._do_add()

    @on(Input.Submitted, "#card-name-input")
    def on_name_submitted(self) -> None:
        """Handle enter in card name input."""
        self._do_add()

    @on(Input.Submitted, "#qty-input")
    def on_qty_submitted(self) -> None:
        """Handle enter in quantity input."""
        self._do_add()

    def _do_add(self) -> None:
        """Actually add the card.

        Supports multiple input formats:
        - "Lightning Bolt" - card name
        - "fca 27" - set code + collector number
        - "2 fca 27" - optional quantity prefix + set code + collector number
        - "Lightning Bolt *F*" or "Lightning Bolt foil" - foil markers
        """
        from .parser import parse_card_input

        card_name_input = self.query_one("#card-name-input", Input)
        qty_input = self.query_one("#qty-input", Input)
        foil_cb = self.query_one("#foil-checkbox", Checkbox)

        raw_input = card_name_input.value.strip()
        if not raw_input:
            self.app.notify("Please enter a card name", severity="error")
            card_name_input.focus()
            return

        # Get default quantity from qty_input field
        try:
            default_qty = int(qty_input.value)
            if default_qty < 1:
                default_qty = 1
        except ValueError:
            default_qty = 1

        # Parse the input
        parsed = parse_card_input(raw_input, default_quantity=default_qty)

        # Combine foil from checkbox and parsed input
        is_foil = foil_cb.value or parsed.foil

        # Return parsed result - CollectionManager handles lookup
        self.dismiss(
            AddToCollectionResult(
                card_name=parsed.card_name,
                quantity=parsed.quantity,
                foil=is_foil,
                set_code=parsed.set_code,
                collector_number=parsed.collector_number,
            )
        )


class ImportCollectionModal(ModalScreen[str | None]):
    """Modal for importing cards from text format."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,q", "cancel", "Cancel"),
    ]

    CSS = """
    ImportCollectionModal {
        align: center middle;
    }

    #import-dialog {
        width: 70;
        height: auto;
        max-height: 35;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    #import-dialog Label {
        margin-bottom: 1;
    }

    #import-text-area {
        height: 15;
        margin-bottom: 1;
    }

    #import-buttons {
        margin-top: 1;
        height: auto;
    }

    #import-buttons Button {
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        from textual.widgets import TextArea

        with Vertical(id="import-dialog"):
            yield Label(f"[bold {ui_colors.GOLD_DIM}]Import Cards[/]")
            yield Label(
                "[dim]Formats: '4 Lightning Bolt', 'fin 345', or group by set:[/]\n"
                "[dim]  fin:    (set context)[/]\n"
                "[dim]  345     (collector #)[/]\n"
                "[dim]  2x 421  (with quantity)[/]"
            )
            yield TextArea(id="import-text-area")
            with Horizontal(id="import-buttons"):
                yield Button("Import", variant="primary", id="import-btn")
                yield Button("Cancel", id="cancel-btn")

    def action_cancel(self) -> None:
        """Cancel import."""
        self.dismiss(None)

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        """Handle cancel button."""
        self.dismiss(None)

    @on(Button.Pressed, "#import-btn")
    def on_import(self) -> None:
        """Handle import button."""
        from textual.widgets import TextArea

        text_area = self.query_one("#import-text-area", TextArea)
        text = text_area.text.strip()

        if not text:
            self.app.notify("Please enter cards to import", severity="error")
            return

        self.dismiss(text)


class ExportCollectionModal(ModalScreen[None]):
    """Modal for exporting collection to text format."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,q", "close", "Close"),
    ]

    CSS = """
    ExportCollectionModal {
        align: center middle;
    }

    #export-dialog {
        width: 70;
        height: auto;
        max-height: 35;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    #export-dialog Label {
        margin-bottom: 1;
    }

    #export-text-area {
        height: 20;
        margin-bottom: 1;
    }

    #export-buttons {
        margin-top: 1;
        height: auto;
    }

    #export-buttons Button {
        margin-right: 1;
    }
    """

    def __init__(self, export_text: str) -> None:
        super().__init__()
        self._export_text = export_text

    def compose(self) -> ComposeResult:
        from textual.widgets import TextArea

        with Vertical(id="export-dialog"):
            yield Label(f"[bold {ui_colors.GOLD_DIM}]Export Collection[/]")
            yield Label("[dim]Copy the text below to share or backup your collection[/]")
            yield TextArea(self._export_text, id="export-text-area", read_only=True)
            with Horizontal(id="export-buttons"):
                yield Button("Copy to Clipboard", variant="primary", id="copy-btn")
                yield Button("Close", id="close-btn")

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)

    @on(Button.Pressed, "#close-btn")
    def on_close(self) -> None:
        """Handle close button."""
        self.dismiss(None)

    @on(Button.Pressed, "#copy-btn")
    def on_copy(self) -> None:
        """Handle copy button - copy to clipboard."""
        import subprocess

        try:
            # Try to copy to clipboard using pbcopy (macOS) or xclip (Linux)
            process = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            process.communicate(self._export_text.encode())
            self.app.notify("Copied to clipboard!", timeout=2)
        except FileNotFoundError:
            try:
                process = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                process.communicate(self._export_text.encode())
                self.app.notify("Copied to clipboard!", timeout=2)
            except FileNotFoundError:
                self.app.notify(
                    "Clipboard not available - select and copy manually",
                    severity="warning",
                    timeout=3,
                )


class PrintingSelectionModal(ModalScreen[dict[str, tuple[str, str]] | None]):
    """Modal for selecting specific printings for imported cards.

    Returns a dict mapping card_name -> (set_code, collector_number).
    """

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
    ]

    CSS = """
    PrintingSelectionModal {
        align: center middle;
    }

    #printing-dialog {
        width: 80;
        height: auto;
        max-height: 40;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    #printing-dialog Label {
        margin-bottom: 1;
    }

    #printing-list {
        height: auto;
        max-height: 25;
        overflow-y: auto;
        margin-bottom: 1;
    }

    .printing-row {
        height: auto;
        padding: 1 0;
        border-bottom: solid #2a2a2a;
    }

    .printing-row Label {
        margin-bottom: 0;
    }

    .printing-select {
        width: 100%;
        margin-top: 1;
    }

    #printing-buttons {
        margin-top: 1;
        height: auto;
    }

    #printing-buttons Button {
        margin-right: 1;
    }
    """

    def __init__(
        self,
        cards: list[tuple[str, int]],  # (card_name, printings_count)
        db: object,  # MTGDatabase - using object to avoid import issues
    ) -> None:
        super().__init__()
        self._cards = cards
        self._db = db
        self._select_id_to_card: dict[str, str] = {}  # select_id -> card_name
        self._printings: dict[
            str, list[tuple[str, str, str]]
        ] = {}  # card -> [(set_code, number, label)]
        self._selections: dict[str, tuple[str, str]] = {}  # card -> (set_code, number)

    def compose(self) -> ComposeResult:
        with Vertical(id="printing-dialog"):
            yield Label(
                f"[bold {ui_colors.GOLD_DIM}]Select Printings[/]  "
                f"[dim]({len(self._cards)} cards with multiple printings)[/]"
            )
            yield Label(
                "[dim]Choose which printing you want for each card, or skip to use default.[/]"
            )

            with Vertical(id="printing-list"):
                for idx, (card_name, count) in enumerate(self._cards):
                    select_id = f"select-{idx}"
                    self._select_id_to_card[select_id] = card_name
                    with Vertical(classes="printing-row"):
                        yield Label(f"[bold]{card_name}[/] [dim]({count} printings)[/]")
                        yield Select(
                            [],  # Options loaded async
                            id=select_id,
                            classes="printing-select",
                            prompt="Loading printings...",
                        )

            with Horizontal(id="printing-buttons"):
                yield Button("Apply Selections", variant="primary", id="confirm-btn")
                yield Button("Skip", id="skip-btn")

    async def on_mount(self) -> None:
        """Load printings for each card."""
        for idx, (card_name, _) in enumerate(self._cards):
            try:
                printings = await self._db.get_all_printings(card_name)  # type: ignore[attr-defined]
                options: list[tuple[str, str]] = []
                for p in printings:
                    set_code = p.set_code or "???"
                    number = p.collector_number or "?"
                    set_name = p.set_name or set_code.upper()
                    label = f"{set_name} ({set_code.upper()}) #{number}"
                    value = f"{set_code}|{number}"
                    options.append((label, value))

                # Sort by set code
                options.sort(key=lambda x: x[0])

                # Update the select widget
                select_id = f"select-{idx}"
                try:
                    select = self.query_one(f"#{select_id}", Select)
                    select.set_options(options)
                    select.prompt = "Select printing..."
                except Exception:
                    pass

            except Exception:
                pass

    @on(Select.Changed)
    def on_select_changed(self, event: Select.Changed) -> None:
        """Track selections."""
        if event.value and event.value != Select.BLANK:
            # Get card name from mapping (avoids lossy decoding)
            select_id = event.select.id or ""
            card_name = self._select_id_to_card.get(select_id)
            if not card_name:
                return

            # Parse set_code|number from value
            value = str(event.value)
            if "|" in value:
                set_code, number = value.split("|", 1)
                self._selections[card_name] = (set_code, number)

    def action_cancel(self) -> None:
        """Cancel without applying selections."""
        self.dismiss(None)

    def action_confirm(self) -> None:
        """Apply selections."""
        self._do_confirm()

    @on(Button.Pressed, "#skip-btn")
    def on_skip(self) -> None:
        """Skip printing selection."""
        self.dismiss(None)

    @on(Button.Pressed, "#confirm-btn")
    def on_confirm(self) -> None:
        """Apply selections."""
        self._do_confirm()

    def _do_confirm(self) -> None:
        """Return the selections."""
        if self._selections:
            self.dismiss(self._selections)
        else:
            self.dismiss(None)


class ConfirmDeleteModal(ModalScreen[bool]):
    """Confirmation modal for deleting a card from the collection."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,n", "cancel", "Cancel"),
        Binding("y,enter", "confirm", "Confirm"),
    ]

    CSS = """
    ConfirmDeleteModal {
        align: center middle;
    }

    #confirm-delete-dialog {
        width: 50;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $error;
    }

    #confirm-delete-dialog Label {
        margin-bottom: 1;
        text-align: center;
        width: 100%;
    }

    #confirm-delete-info {
        margin: 1 0;
        padding: 1;
        background: #1a1a2e;
    }

    #confirm-delete-buttons {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #confirm-delete-buttons Button {
        margin: 0 1;
    }

    #delete-btn {
        background: $error;
    }
    """

    def __init__(
        self,
        card_name: str,
        quantity: int = 0,
        foil_quantity: int = 0,
    ) -> None:
        """Initialize the modal.

        Args:
            card_name: Name of the card to delete
            quantity: Current regular quantity
            foil_quantity: Current foil quantity
        """
        super().__init__()
        self._card_name = card_name
        self._quantity = quantity
        self._foil_quantity = foil_quantity

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-delete-dialog"):
            yield Label(f"[bold {ui_colors.TEXT_ERROR}]Remove from Collection?[/]")
            with Vertical(id="confirm-delete-info"):
                yield Label(f"[bold]{self._card_name}[/]")
                qty_parts = []
                if self._quantity > 0:
                    qty_parts.append(f"{self._quantity} regular")
                if self._foil_quantity > 0:
                    qty_parts.append(f"{self._foil_quantity} foil")
                if qty_parts:
                    yield Label(f"[dim]{' + '.join(qty_parts)}[/]")
            yield Label("[dim]This will remove the card entirely from your collection.[/]")
            with Horizontal(id="confirm-delete-buttons"):
                yield Button("Delete", variant="error", id="delete-btn")
                yield Button("Cancel", id="cancel-btn")

    def action_cancel(self) -> None:
        """Cancel deletion."""
        self.dismiss(False)

    def action_confirm(self) -> None:
        """Confirm deletion."""
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        """Handle cancel button."""
        self.dismiss(False)

    @on(Button.Pressed, "#delete-btn")
    def on_delete(self) -> None:
        """Handle delete button."""
        self.dismiss(True)


@dataclass
class CollectionCardInfo:
    """Card info passed to DeckSuggestionsModal."""

    name: str
    type_line: str | None = None
    colors: list[str] | None = None
    mana_cost: str | None = None
    text: str | None = None


@dataclass
class CreateDeckResult:
    """Result from DeckSuggestionsModal when creating a deck."""

    deck_name: str
    card_names: list[str]
    commander: str | None = None
    format_type: str = "commander"


class SuggestionItem(ListItem):
    """A selectable deck suggestion item with inline details."""

    def __init__(self, suggestion: object, id: str | None = None) -> None:
        super().__init__(id=id)
        self.suggestion = suggestion

    def compose(self) -> ComposeResult:
        yield Static(self._format_suggestion())

    def _format_suggestion(self) -> str:
        """Format the suggestion display with rich inline details."""
        name = getattr(self.suggestion, "name", "Unknown")
        archetype = getattr(self.suggestion, "archetype", "")
        completion = getattr(self.suggestion, "completion_pct", 0.0)
        colors = getattr(self.suggestion, "colors", [])
        key_owned = getattr(self.suggestion, "key_cards_owned", [])
        reasons = getattr(self.suggestion, "reasons", [])
        commander = getattr(self.suggestion, "commander", None)

        # Color indicators using mana symbols
        color_map = {"W": "W", "U": "U", "B": "B", "R": "R", "G": "G"}
        color_str = " ".join(f"[bold]{color_map.get(c, c)}[/]" for c in colors)

        # Completion bar (compact, capped at 100%)
        bar_width = 12
        filled = min(bar_width, int(completion * bar_width))
        bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
        pct = min(100, int(completion * 100))

        # Score color
        if completion >= 0.7:
            score_color = ui_colors.SYNERGY_STRONG
        elif completion >= 0.5:
            score_color = ui_colors.SYNERGY_MODERATE
        elif completion >= 0.3:
            score_color = ui_colors.SYNERGY_WEAK
        else:
            score_color = ui_colors.TEXT_DIM

        lines = []

        # Line 1: Name + Colors + Score
        line1 = f"[bold {ui_colors.GOLD}]{name}[/]"
        if color_str:
            line1 += f"  {color_str}"
        line1 += f"  [{score_color}]{bar} {pct}%[/]"
        lines.append(line1)

        # Line 2: Archetype / Commander
        if commander and commander != name:
            lines.append(f"  [green]\u2605 Commander:[/] {commander}")
        elif archetype:
            lines.append(f"  [{ui_colors.TEXT_DIM}]{archetype}[/]")

        # Line 3: Reason (why this deck)
        if reasons:
            lines.append(f"  [{ui_colors.TEXT_DIM}]\u2192 {reasons[0]}[/]")

        # Line 4: Card preview (first 3 cards)
        if key_owned:
            preview = ", ".join(key_owned[:3])
            if len(key_owned) > 3:
                preview += f" +{len(key_owned) - 3} more"
            lines.append(f"  [{ui_colors.TEXT_DIM}]\u2726 {preview}[/]")

        return "\n".join(lines)


class DeckSuggestionsModal(ModalScreen[CreateDeckResult | None]):
    """Modal showing buildable deck archetypes from collection.

    Simple single-column design with inline details for each suggestion.
    """

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,q", "close", "Close"),
        Binding("c", "show_commander", "Commander"),
        Binding("s", "show_standard", "Standard"),
        Binding("enter", "create_deck", "Create"),
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
    ]

    CSS = """
    DeckSuggestionsModal {
        align: center middle;
    }

    #deck-suggestions-dialog {
        width: 85;
        height: 80%;
        padding: 1 2;
        background: #0a0a14;
        border: thick #c9a227;
    }

    #deck-suggestions-header {
        height: 3;
        text-align: center;
        border-bottom: solid #2a2a4e;
    }

    #format-row {
        height: 3;
        align: center middle;
    }

    .format-btn {
        width: 14;
        height: 3;
        margin: 0 1;
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
        height: 100%;
        min-height: 20;
        scrollbar-color: #c9a227;
    }

    #suggestions-list > ListItem {
        height: auto;
        padding: 1;
        background: #1a1a2e;
        border-bottom: solid #2a2a4e;
    }

    #suggestions-list > ListItem:hover {
        background: #2a2a4e;
    }

    #suggestions-list > ListItem.-highlight {
        background: #2a2a4e;
        border-left: heavy #c9a227;
    }

    #deck-suggestions-footer {
        height: 3;
        align: center middle;
        dock: bottom;
    }

    #deck-suggestions-footer Button {
        margin: 0 1;
    }

    #create-btn {
        background: #2e7d32;
        min-width: 20;
    }

    #create-btn:hover {
        background: #388e3c;
    }

    #close-btn {
        background: #1a1a2e;
    }
    """

    def __init__(self, card_info_list: list[CollectionCardInfo]) -> None:
        super().__init__()
        self._card_info_list = card_info_list
        self._collection_cards = {c.name for c in card_info_list}
        self._current_format = "commander"
        self._suggestions: list[DeckSuggestion] = []
        self._selected_suggestion: object | None = None

    def compose(self) -> ComposeResult:
        from textual.widgets import ListView

        with Vertical(id="deck-suggestions-dialog"):
            yield Static(
                f"[bold {ui_colors.GOLD}]What Can I Build?[/]  "
                f"[dim]({len(self._card_info_list)} cards)[/]",
                id="deck-suggestions-header",
            )
            with Horizontal(id="format-row"):
                yield Button("Commander", id="btn-commander", classes="format-btn -active")
                yield Button("Standard", id="btn-standard", classes="format-btn")

            yield ListView(id="suggestions-list")

            with Horizontal(id="deck-suggestions-footer"):
                yield Button("Create Deck", id="create-btn", variant="success")
                yield Button("Close", id="close-btn")

    async def on_mount(self) -> None:
        """Load suggestions on mount."""
        await self._load_suggestions()
        # Focus the list
        try:
            from textual.widgets import ListView

            list_view = self.query_one("#suggestions-list", ListView)
            list_view.focus()
        except Exception:
            pass

    async def _load_suggestions(self) -> None:
        """Load deck suggestions for current format."""
        from textual.widgets import ListView

        from mtg_core.tools.recommendations import CardData, get_deck_finder

        finder = get_deck_finder()

        # Convert our card info to CardData for the finder
        card_data = [
            CardData(
                name=c.name,
                type_line=c.type_line,
                colors=c.colors,
                mana_cost=c.mana_cost,
                text=c.text,
            )
            for c in self._card_info_list
        ]

        self._suggestions = await finder.find_buildable_decks(
            self._collection_cards,
            format=self._current_format,
            card_data=card_data,
            min_completion=0.1,
            limit=10,
        )

        # Update list
        try:
            list_view = self.query_one("#suggestions-list", ListView)
            list_view.clear()

            if not self._suggestions:
                list_view.append(
                    ListItem(
                        Static(
                            f"[{ui_colors.TEXT_DIM}]No suggestions found for {self._current_format}.\n"
                            "Try adding more legendary creatures or tribal cards![/]"
                        )
                    )
                )
                self._selected_suggestion = None
                return

            for suggestion in self._suggestions:
                list_view.append(SuggestionItem(suggestion))

            # Select first item
            if list_view.children:
                list_view.index = 0
                self._selected_suggestion = self._suggestions[0]

        except Exception:
            pass

    @on(ListView.Highlighted, "#suggestions-list")
    def on_suggestion_highlighted(self, event: ListView.Highlighted) -> None:
        """Track selected suggestion."""
        if event.item and isinstance(event.item, SuggestionItem):
            self._selected_suggestion = event.item.suggestion

    @on(Button.Pressed, "#btn-commander")
    async def on_commander_tab(self) -> None:
        """Switch to Commander format."""
        await self._switch_format("commander")

    @on(Button.Pressed, "#btn-standard")
    async def on_standard_tab(self) -> None:
        """Switch to Standard format."""
        await self._switch_format("standard")

    async def _switch_format(self, fmt: str) -> None:
        """Switch format and reload suggestions."""
        if self._current_format == fmt:
            return

        self._current_format = fmt

        # Update button styles
        try:
            cmd_btn = self.query_one("#btn-commander", Button)
            std_btn = self.query_one("#btn-standard", Button)

            if fmt == "commander":
                cmd_btn.add_class("-active")
                std_btn.remove_class("-active")
            else:
                std_btn.add_class("-active")
                cmd_btn.remove_class("-active")
        except Exception:
            pass

        await self._load_suggestions()

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)

    async def action_show_commander(self) -> None:
        """Show Commander suggestions."""
        await self._switch_format("commander")

    async def action_show_standard(self) -> None:
        """Show Standard suggestions."""
        await self._switch_format("standard")

    def action_nav_up(self) -> None:
        """Navigate up in list."""
        from textual.widgets import ListView

        try:
            list_view = self.query_one("#suggestions-list", ListView)
            list_view.action_cursor_up()
        except Exception:
            pass

    def action_nav_down(self) -> None:
        """Navigate down in list."""
        from textual.widgets import ListView

        try:
            list_view = self.query_one("#suggestions-list", ListView)
            list_view.action_cursor_down()
        except Exception:
            pass

    def action_create_deck(self) -> None:
        """Create a deck from the selected suggestion."""
        self._do_create_deck()

    @on(Button.Pressed, "#create-btn")
    def on_create_deck(self) -> None:
        """Handle create deck button."""
        self._do_create_deck()

    def _do_create_deck(self) -> None:
        """Create deck from selected suggestion."""
        if not self._selected_suggestion:
            self.app.notify("Select a deck first", severity="warning")
            return

        name = getattr(self._selected_suggestion, "name", "New Deck")
        commander = getattr(self._selected_suggestion, "commander", None)
        key_cards = getattr(self._selected_suggestion, "key_cards_owned", [])

        if not key_cards:
            self.app.notify("No cards in this suggestion", severity="warning")
            return

        result = CreateDeckResult(
            deck_name=name,
            card_names=key_cards,
            commander=commander,
            format_type=self._current_format,
        )
        self.dismiss(result)

    @on(Button.Pressed, "#close-btn")
    def on_close(self) -> None:
        """Handle close button."""
        self.dismiss(None)
