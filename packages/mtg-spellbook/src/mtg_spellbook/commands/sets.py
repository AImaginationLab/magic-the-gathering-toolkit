"""Set browsing and statistics commands."""

from __future__ import annotations

from typing import Any

from textual import work
from textual.widgets import Label, ListItem, Static

from mtg_core.tools import sets


class SetCommandsMixin:
    """Mixin providing set browsing and statistics commands."""

    _db: Any

    def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...
    def _hide_synergy_panel(self) -> None: ...
    def _update_results_header(self, text: str) -> None: ...
    def _show_message(self, message: str) -> None: ...

    @work
    async def browse_sets(self, query: str = "") -> None:
        """Browse available sets."""
        if not self._db:
            return

        self._hide_synergy_panel()

        result = await sets.get_sets(self._db, name=query if query else None)

        from ..widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        for s in result.sets[:50]:
            label = (
                f"[cyan]{s.code.upper()}[/] {s.name} "
                f"[dim]({s.release_date or '?'})[/]"
            )
            results_list.append(ListItem(Label(label)))

        self._update_results_header(f"Sets ({len(result.sets)})")

    @work
    async def show_set(self, code: str) -> None:
        """Show set details."""
        if not self._db:
            return

        self._hide_synergy_panel()

        try:
            result = await sets.get_set(self._db, code)

            from ..widgets import CardPanel

            panel = self.query_one("#card-panel", CardPanel)
            card_text = panel.query_one(panel.get_child_id("card-text"), Static)

            lines = [
                f"[bold]{result.name}[/] [{result.code.upper()}]",
                "",
                f"[bold]Type:[/] {result.type}",
                f"[bold]Released:[/] {result.release_date or 'Unknown'}",
                f"[bold]Cards:[/] {result.total_set_size or 'Unknown'}",
            ]
            card_text.update("\n".join(lines))

        except Exception:
            self._show_message(f"[red]Set not found: {code}[/]")

    @work
    async def show_stats(self) -> None:
        """Show database statistics."""
        if not self._db:
            return

        stats = await self._db.get_database_stats()

        from ..widgets import CardPanel

        panel = self.query_one("#card-panel", CardPanel)
        card_text = panel.query_one(panel.get_child_id("card-text"), Static)

        lines = [
            "[bold]📊 Database Statistics[/]",
            "",
            f"  [bold]Cards:[/]   [cyan]{stats.get('unique_cards', '?'):,}[/]",
            f"  [bold]Sets:[/]    [cyan]{stats.get('total_sets', '?'):,}[/]",
            f"  [bold]Version:[/] [dim]{stats.get('data_version', 'unknown')}[/]",
        ]
        card_text.update("\n".join(lines))
