"""Go to Page modal dialog."""

from __future__ import annotations

from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class GoToPageModal(ModalScreen[int | None]):
    """Modal dialog for jumping to a specific page."""

    DEFAULT_CSS = """
    GoToPageModal {
        align: center middle;
    }

    GoToPageModal > Vertical {
        width: 40;
        height: auto;
        max-height: 12;
        background: #1e1e2e;
        border: thick #c9a227;
        padding: 1 2;
    }

    GoToPageModal .modal-title {
        text-align: center;
        text-style: bold;
        color: #e6c84a;
        margin-bottom: 1;
    }

    GoToPageModal .modal-info {
        text-align: center;
        color: #888;
        margin-bottom: 1;
    }

    GoToPageModal Input {
        margin-bottom: 1;
    }

    GoToPageModal .button-row {
        height: 3;
        align: center middle;
    }

    GoToPageModal Button {
        margin: 0 1;
    }

    GoToPageModal .error-text {
        color: #ff6b6b;
        text-align: center;
        height: 1;
    }
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape,q", "cancel", "Cancel"),
        ("enter", "submit", "Go"),
    ]

    class PageSelected(Message):
        """Message sent when a page is selected."""

        def __init__(self, page: int) -> None:
            super().__init__()
            self.page = page

    def __init__(
        self,
        current_page: int = 1,
        total_pages: int = 1,
    ) -> None:
        super().__init__()
        self._current_page = current_page
        self._total_pages = total_pages

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Go to Page", classes="modal-title")
            yield Label(
                f"Enter page number (1-{self._total_pages}):",
                classes="modal-info",
            )
            yield Input(
                value=str(self._current_page),
                placeholder=f"1-{self._total_pages}",
                id="page-input",
            )
            yield Static("", id="error-text", classes="error-text")
            with Vertical(classes="button-row"):
                yield Button("Go", variant="primary", id="go-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        """Focus and select the input on mount."""
        input_widget = self.query_one("#page-input", Input)
        input_widget.focus()
        input_widget.action_select_all()

    @on(Button.Pressed, "#go-btn")
    def on_go_pressed(self) -> None:
        """Handle Go button press."""
        self._try_submit()

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel_pressed(self) -> None:
        """Handle Cancel button press."""
        self.dismiss(None)

    @on(Input.Submitted)
    def on_input_submitted(self) -> None:
        """Handle Enter in input."""
        self._try_submit()

    def action_cancel(self) -> None:
        """Cancel the dialog."""
        self.dismiss(None)

    def action_submit(self) -> None:
        """Submit the dialog."""
        self._try_submit()

    def _try_submit(self) -> None:
        """Validate and submit the page number."""
        input_widget = self.query_one("#page-input", Input)
        error_text = self.query_one("#error-text", Static)

        try:
            page = int(input_widget.value.strip())
        except ValueError:
            error_text.update("[red]Please enter a valid number[/]")
            return

        if page < 1 or page > self._total_pages:
            error_text.update(f"[red]Page must be between 1 and {self._total_pages}[/]")
            return

        self.dismiss(page)
