"""Synergy and combo discovery commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from textual import work
from textual.widgets import Static

from mtg_core.exceptions import CardNotFoundError
from mtg_core.tools import cards, synergy

from ..pagination import PaginationState


@dataclass
class SynergyItem:
    """Wrapper for synergy items to use with pagination."""

    name: str
    synergy_type: str
    reason: str
    score: float


class SynergyCommandsMixin:
    """Mixin providing synergy and combo commands."""

    if TYPE_CHECKING:
        _db: Any
        _scryfall: Any
        _current_results: list[Any]
        _current_card: Any
        _synergy_mode: bool
        _synergy_info: dict[str, Any]
        _pagination: PaginationState | None

        def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...
        def _show_synergy_panel(self) -> None: ...
        def _show_message(self, message: str) -> None: ...
        def _display_synergy_results(self) -> None: ...

    @work
    async def find_synergies(self, card_name: str) -> None:
        """Find synergistic cards and show in results list."""
        if not self._db:
            return

        self._synergy_mode = True
        self._synergy_info = {}

        try:
            source_card = await cards.get_card(self._db, self._scryfall, name=card_name)
        except CardNotFoundError:
            self._show_message(f"[red]Card not found: {card_name}[/]")
            self._synergy_mode = False
            return

        result = await synergy.find_synergies(self._db, card_name=card_name, max_results=100)

        if not result.synergies:
            self._show_message(f"[yellow]No synergies found for {card_name}[/]")
            self._synergy_mode = False
            self._pagination = None
            return

        # Build synergy info and items for pagination
        synergy_items: list[SynergyItem] = []
        for syn in result.synergies:
            self._synergy_info[syn.name] = {
                "type": syn.synergy_type,
                "reason": syn.reason,
                "score": syn.score,
            }
            synergy_items.append(
                SynergyItem(
                    name=syn.name,
                    synergy_type=syn.synergy_type,
                    reason=syn.reason,
                    score=syn.score,
                )
            )

        # Create pagination state
        self._pagination = PaginationState(
            all_items=synergy_items,
            current_page=1,
            page_size=25,
            source_type="synergy",
            source_query=card_name,
        )

        # Load first page of card details
        self._current_results = []
        for item in self._pagination.current_page_items:
            try:
                detail = await cards.get_card(self._db, self._scryfall, name=item.name)
                self._current_results.append(detail)
            except CardNotFoundError:
                pass

        # Cache first page
        self._pagination.cache_details(1, self._current_results)

        self._display_synergy_results()
        self._show_source_card(source_card)

        if self._current_results:
            self._current_card = self._current_results[0]
            self._update_card_panel_with_synergy(self._current_results[0])
            await self._load_card_extras(self._current_results[0])

    def _update_card_panel_with_synergy(self, card: Any) -> None:
        """Update card panel and show synergy reason."""
        from ..widgets import CardPanel

        panel = self.query_one("#card-panel", CardPanel)
        panel.update_card_with_synergy(card, self._synergy_info.get(card.name))

    def _show_source_card(self, card: Any) -> None:
        """Show source card in the right panel for side-by-side comparison."""
        from ..widgets import CardPanel

        source_panel = self.query_one("#source-card-panel", CardPanel)
        source_panel.update_card(card)
        self.query_one("#source-card-panel").add_class("visible")
        self.query_one("#card-panel").add_class("synergy-mode")
        self._load_source_extras(card)  # type: ignore[no-untyped-call]

    @work
    async def _load_source_extras(self, card: Any) -> None:
        """Load extras for the source card panel."""
        await self._load_card_extras(card, "#source-card-panel")

    async def _load_card_extras(self, card: Any, panel_id: str = "#card-panel") -> None:
        """Load rulings, legalities, and printings for a card."""
        ...

    @work
    async def find_combos(self, card_name: str) -> None:
        """Find combos for a card."""
        if not self._db:
            return

        self._show_synergy_panel()

        result = await synergy.detect_combos(self._db, card_name=card_name)

        content = self.query_one("#synergy-content", Static)

        lines = [f"[bold]🔗 Combos involving {card_name}[/]", ""]

        if result.combos:
            lines.append(f"[bold green]Complete Combos ({len(result.combos)}):[/]")
            for combo in result.combos:
                lines.append(f"  [bold cyan]{combo.id}[/] [{combo.combo_type}]")
                lines.append(f"    {combo.description}")
                for card in combo.cards:
                    lines.append(f"      • [cyan]{card.name}[/] — {card.role}")
                lines.append("")

        if result.potential_combos:
            lines.append(f"[bold yellow]Potential Combos ({len(result.potential_combos)}):[/]")
            for combo in result.potential_combos:
                missing = result.missing_cards.get(combo.id, [])
                lines.append(f"  [bold cyan]{combo.id}[/] [{combo.combo_type}]")
                lines.append(f"    {combo.description}")
                if missing:
                    lines.append(f"    [red]Missing:[/] {', '.join(missing)}")
                lines.append("")

        if not result.combos and not result.potential_combos:
            lines.append("[dim]No known combos found for this card.[/]")

        content.update("\n".join(lines))
