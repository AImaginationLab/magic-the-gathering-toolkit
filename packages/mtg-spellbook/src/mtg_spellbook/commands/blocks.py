"""Block browsing commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import work

if TYPE_CHECKING:
    from mtg_core.data.models.responses import BlockSummary


class BlockCommandsMixin:
    """Mixin providing block browsing commands."""

    if TYPE_CHECKING:
        _db: Any

        def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...
        def _show_message(self, message: str) -> None: ...
        def notify(
            self, message: str, *, severity: str = "information", timeout: float = 3
        ) -> None: ...
        def run_worker(self, coro: Any) -> Any: ...

    @work
    async def browse_blocks(self) -> None:
        """Open block browser widget with tree view of all blocks."""
        if not self._db:
            return

        from textual.css.query import NoMatches

        from ..widgets import BlockBrowser

        # Get all blocks
        blocks: list[BlockSummary] = await self._db.get_all_blocks()

        if not blocks:
            self._show_message("[yellow]No blocks found in database[/]")
            return

        # Check if browser already exists
        try:
            existing = self.query_one("#block-browser", BlockBrowser)
            await existing.load_blocks(blocks)
            existing.remove_class("hidden")
            return
        except NoMatches:
            pass

        # Create and mount new block browser
        browser = BlockBrowser(id="block-browser", classes="block-browser-overlay")

        try:
            main_container = self.query_one("#main-container")
            main_container.mount(browser)
            await browser.load_blocks(blocks)
        except NoMatches:
            self._show_message("[red]Could not display block browser[/]")

    @work
    async def show_recent_sets(self, limit: int = 10) -> None:
        """Show recent set releases."""
        if not self._db:
            return

        from textual.widgets import Label, ListItem

        from ..widgets import ResultsList

        # Get recent sets (expansions and core sets only)
        sets = await self._db.get_recent_sets(
            limit=limit,
            set_types=["expansion", "core", "masters", "draft_innovation"],
        )

        if not sets:
            self._show_message("[yellow]No recent sets found[/]")
            return

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        for s in sets:
            type_display = (s.type or "").replace("_", " ").title()
            label = (
                f"[cyan]{s.code.upper()}[/] [bold]{s.name}[/]  "
                f"[dim]{s.release_date or '?'}[/]  "
                f"[dim]{type_display}[/]"
            )
            results_list.append(ListItem(Label(label)))

        self._update_results_header(f"Recent Sets ({len(sets)})")

    def _update_results_header(self, text: str) -> None:
        """Update the results header text."""
        from textual.css.query import NoMatches
        from textual.widgets import Static

        try:
            header = self.query_one("#results-header", Static)
            header.update(text)
        except NoMatches:
            pass
