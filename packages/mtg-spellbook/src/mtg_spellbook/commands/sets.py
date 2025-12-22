"""Set browsing and statistics commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import work
from textual.widgets import Label, ListItem, Static

from mtg_core.exceptions import SetNotFoundError
from mtg_core.tools import sets

if TYPE_CHECKING:
    from mtg_core.data.models import Set
    from mtg_core.data.models.responses import CardSummary

    from ..widgets.set_detail import SetStats


class SetCommandsMixin:
    """Mixin providing set browsing and statistics commands."""

    if TYPE_CHECKING:
        _db: Any

        def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...
        def _hide_synergy_panel(self) -> None: ...
        def _update_results_header(self, text: str) -> None: ...
        def _show_message(self, message: str) -> None: ...
        def notify(
            self, message: str, *, severity: str = "information", timeout: float = 3
        ) -> None: ...
        def run_worker(self, coro: Any) -> Any: ...

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
            label = f"[cyan]{s.code.upper()}[/] {s.name} [dim]({s.release_date or '?'})[/]"
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

            from ..widgets import ResultsList

            results_list = self.query_one("#results-list", ResultsList)
            results_list.clear()

            lines = [
                f"[bold]{result.name}[/] [{result.code.upper()}]",
                "",
                f"[bold]Type:[/] {result.type}",
                f"[bold]Released:[/] {result.release_date or 'Unknown'}",
                f"[bold]Cards:[/] {result.total_set_size or 'Unknown'}",
            ]
            from textual.widgets import ListItem

            results_list.append(ListItem(Static("\n".join(lines))))

        except SetNotFoundError:
            self._show_message(f"[red]Set not found: {code}[/]")

    @work
    async def show_stats(self) -> None:
        """Show database statistics."""
        if not self._db:
            return

        stats = await self._db.get_database_stats()

        from ..widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        lines = [
            "[bold]📊 Database Statistics[/]",
            "",
            f"  [bold]Cards:[/]   [cyan]{stats.get('unique_cards', '?'):,}[/]",
            f"  [bold]Sets:[/]    [cyan]{stats.get('total_sets', '?'):,}[/]",
            f"  [bold]Version:[/] [dim]{stats.get('data_version', 'unknown')}[/]",
        ]
        from textual.widgets import ListItem

        results_list.append(ListItem(Static("\n".join(lines))))

    @work
    async def show_set_detail(self, set_code: str) -> None:
        """Show detailed set view with all cards."""
        if not self._db:
            return

        from ..widgets.set_detail import SetStats as SetStatsClass

        try:
            # Get set info - returns a SetDetail response, need to get the Set model
            set_data = await self._db.get_set(set_code)

            # Get all cards in set
            cards = await self._db.get_cards_in_set(set_code)

            if not cards:
                self._show_message(f"[yellow]No cards found in set: {set_code.upper()}[/]")
                return

            # Convert Card objects to CardSummary
            summaries: list[CardSummary] = []
            for card in cards:
                from mtg_core.data.models.responses import CardSummary

                summaries.append(
                    CardSummary(
                        name=card.name,
                        mana_cost=card.mana_cost,
                        cmc=card.cmc,
                        type=card.type,
                        colors=card.colors or [],
                        color_identity=card.color_identity or [],
                        rarity=card.rarity,
                        set_code=card.set_code,
                        keywords=card.keywords or [],
                        power=card.power,
                        toughness=card.toughness,
                    )
                )

            # Get set statistics
            db_stats = await self._db.get_set_stats(set_code)

            # Convert to widget's SetStats class
            stats = SetStatsClass(
                total_cards=db_stats.total_cards,
                rarity_distribution=db_stats.rarity_distribution,
                color_distribution=db_stats.color_distribution,
                mechanics=db_stats.mechanics,
                avg_cmc=db_stats.avg_cmc,
            )

            # Mount and show the set detail view
            self._show_set_detail_view(set_data, summaries, stats)

        except SetNotFoundError:
            self._show_message(f"[red]Set not found: {set_code}[/]")

    def _show_set_detail_view(
        self,
        set_data: Set,
        cards: list[CardSummary],
        stats: SetStats,
    ) -> None:
        """Mount and display the set detail view."""
        from textual.css.query import NoMatches

        from ..widgets import SetDetailView

        # Check if set detail view already exists
        try:
            existing = self.query_one("#set-detail", SetDetailView)
            # Update existing view - use run_worker to handle the coroutine
            self.run_worker(existing.load_set(set_data, cards, stats))
            existing.remove_class("hidden")
            return
        except NoMatches:
            pass

        # Create and mount new set detail view as overlay
        set_view = SetDetailView(id="set-detail", classes="set-detail-overlay")

        # Mount to the main container
        try:
            main_container = self.query_one("#main-container")
            main_container.mount(set_view)
            self.run_worker(set_view.load_set(set_data, cards, stats))
        except NoMatches:
            self._show_message("[red]Could not display set details[/]")
