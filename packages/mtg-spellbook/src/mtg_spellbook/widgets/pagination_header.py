"""Pagination header widget for displaying page info and controls."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.widgets import Static

if TYPE_CHECKING:
    from ..pagination import PaginationState


class PaginationHeader(Static):
    """Header widget showing pagination info and keyboard hints."""

    DEFAULT_CSS = """
    PaginationHeader {
        height: 2;
        padding: 0 1;
        background: #1a1a2e;
        border-bottom: solid #3d3d3d;
    }

    PaginationHeader .page-info {
        color: #e6c84a;
        text-style: bold;
    }

    PaginationHeader .page-position {
        color: #888;
        margin-left: 2;
    }

    PaginationHeader .page-controls {
        color: #666;
        text-style: italic;
        dock: right;
    }

    PaginationHeader .no-pagination {
        color: #e6c84a;
        text-style: bold;
    }
    """

    def __init__(
        self,
        pagination: PaginationState | None = None,
        title: str = "Results",
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._pagination = pagination
        self._title = title

    def compose(self) -> ComposeResult:
        """Compose the header content."""
        yield Static("", id="pagination-content")

    def update_pagination(
        self, pagination: PaginationState | None, title: str | None = None
    ) -> None:
        """Update the pagination display."""
        self._pagination = pagination
        if title is not None:
            self._title = title
        self._refresh_content()

    def _refresh_content(self) -> None:
        """Refresh the header content."""
        content = self.query_one("#pagination-content", Static)

        if self._pagination is None or self._pagination.total_items == 0:
            content.update(f"[bold #e6c84a]{self._title} (0)[/]")
            return

        p = self._pagination

        if p.total_pages <= 1:
            # Single page - simple display
            content.update(f"[bold #e6c84a]{self._title} ({p.total_items})[/]")
        else:
            # Multiple pages - show full pagination
            info = (
                f"[bold #e6c84a]{self._title}: {p.start_index}-{p.end_index} of {p.total_items}[/]"
            )
            position = f"[#888]Page {p.current_page}/{p.total_pages}[/]"
            controls = "[dim]n:Next p:Prev g:GoTo[/]"

            if p.is_loading:
                position = "[yellow]Loading...[/]"

            content.update(f"{info}  {position}  {controls}")

    def show_loading(self) -> None:
        """Show loading state."""
        content = self.query_one("#pagination-content", Static)
        content.update(f"[bold #e6c84a]{self._title}[/]  [yellow]Loading...[/]")
