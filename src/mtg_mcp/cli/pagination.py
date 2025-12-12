"""Reusable pagination utilities for CLI and REPL."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from rich.console import Console

console = Console()

T = TypeVar("T")


@dataclass
class PaginatedList(Generic[T]):
    """A paginated list with navigation support."""

    items: list[T]
    page_size: int = 10
    current_page: int = 0

    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        return max(1, (len(self.items) + self.page_size - 1) // self.page_size)

    @property
    def total_items(self) -> int:
        """Total number of items."""
        return len(self.items)

    @property
    def current_items(self) -> list[T]:
        """Items on the current page."""
        start = self.current_page * self.page_size
        end = start + self.page_size
        return self.items[start:end]

    @property
    def start_index(self) -> int:
        """1-based start index for display."""
        return self.current_page * self.page_size + 1

    @property
    def end_index(self) -> int:
        """1-based end index for display."""
        return min((self.current_page + 1) * self.page_size, len(self.items))

    @property
    def has_next(self) -> bool:
        """Whether there's a next page."""
        return self.current_page < self.total_pages - 1

    @property
    def has_prev(self) -> bool:
        """Whether there's a previous page."""
        return self.current_page > 0

    def next_page(self) -> bool:
        """Go to next page. Returns True if successful."""
        if self.has_next:
            self.current_page += 1
            return True
        return False

    def prev_page(self) -> bool:
        """Go to previous page. Returns True if successful."""
        if self.has_prev:
            self.current_page -= 1
            return True
        return False

    def reset(self) -> None:
        """Reset to first page."""
        self.current_page = 0


async def paginate_display(
    items: list[T],
    render_item: Callable[[T, int], None],
    *,
    title: str = "",
    page_size: int = 10,
    prompt: str = "more",
) -> None:
    """Display items with interactive pagination.

    Args:
        items: List of items to display
        render_item: Function to render a single item (item, 1-based index)
        title: Title to show above results
        page_size: Items per page
        prompt: Prompt name for input
        show_index: Whether to show item indices
    """
    if not items:
        console.print("[dim]No items to display[/]")
        return

    paginator = PaginatedList(items=items, page_size=page_size)

    while True:
        # Show title with count
        if title:
            console.print(f"\n[bold]{title}[/] ({paginator.total_items} total)\n")

        # Render current page items
        for i, item in enumerate(paginator.current_items):
            idx = paginator.start_index + i
            render_item(item, idx)

        # If only one page, just return
        if paginator.total_pages == 1:
            console.print()
            return

        # Show pagination info
        console.print(
            f"\n[dim]Showing {paginator.start_index}-{paginator.end_index} "
            f"of {paginator.total_items} (page {paginator.current_page + 1}/"
            f"{paginator.total_pages})[/]"
        )

        # Build hints
        hints = []
        if paginator.has_next:
            hints.append("Enter=more")
        if paginator.has_prev:
            hints.append("b=back")
        hints.append("q=done")
        console.print(f"[dim]{' | '.join(hints)}[/]")

        # Get input
        try:
            nav = console.input(f"[bold magenta]{prompt}>[/] ").strip().lower()

            if nav == "" and paginator.has_next:
                paginator.next_page()
            elif nav == "b" and paginator.has_prev:
                paginator.prev_page()
            elif nav in ("q", "quit", "") or (nav == "" and not paginator.has_next):
                break
        except (EOFError, KeyboardInterrupt):
            break

    console.print()


def format_score_bar(score: float, width: int = 5) -> tuple[str, str]:
    """Format a score as a visual bar with appropriate color.

    Args:
        score: Score from 0.0 to 1.0
        width: Width of the bar in characters

    Returns:
        Tuple of (bar_string, style_name)
    """
    filled = int(score * width)
    bar = "●" * filled + "○" * (width - filled)

    if score >= 0.8:
        style = "bright_green"
    elif score >= 0.6:
        style = "green"
    elif score >= 0.4:
        style = "yellow"
    else:
        style = "dim"

    return bar, style
