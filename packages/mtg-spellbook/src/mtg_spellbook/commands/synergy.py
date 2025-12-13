"""Synergy and combo discovery commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import work
from textual.widgets import Label, ListItem, Static

from mtg_core.exceptions import CardNotFoundError
from mtg_core.tools import cards, synergy

from ..formatting import prettify_mana


class SynergyCommandsMixin:
    """Mixin providing synergy and combo commands."""

    if TYPE_CHECKING:
        _db: Any
        _scryfall: Any
        _current_results: list[Any]
        _current_card: Any
        _synergy_mode: bool
        _synergy_info: dict[str, Any]

        def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...
        def _show_synergy_panel(self) -> None: ...
        def _show_message(self, message: str) -> None: ...
        def _update_results_header(self, text: str) -> None: ...

    @work
    async def find_synergies(self, card_name: str) -> None:
        """Find synergistic cards and show in results list."""
        if not self._db:
            return

        self._synergy_mode = True
        self._synergy_info = {}

        try:
            source_card = await cards.get_card(
                self._db, self._scryfall, name=card_name
            )
        except CardNotFoundError:
            self._show_message(f"[red]Card not found: {card_name}[/]")
            self._synergy_mode = False
            return

        result = await synergy.find_synergies(
            self._db, card_name=card_name, max_results=50
        )

        if not result.synergies:
            self._show_message(f"[yellow]No synergies found for {card_name}[/]")
            self._synergy_mode = False
            return

        for syn in result.synergies:
            self._synergy_info[syn.name] = {
                "type": syn.synergy_type,
                "reason": syn.reason,
                "score": syn.score,
            }

        self._current_results = []
        for syn in result.synergies[:25]:
            try:
                detail = await cards.get_card(
                    self._db, self._scryfall, name=syn.name
                )
                self._current_results.append(detail)
            except CardNotFoundError:
                pass

        self._update_synergy_results(
            self._current_results, card_name, len(result.synergies)
        )
        self._show_source_card(source_card)

        if self._current_results:
            self._current_card = self._current_results[0]
            self._update_card_panel_with_synergy(self._current_results[0])
            await self._load_card_extras(self._current_results[0])

    def _update_synergy_results(
        self, results: list[Any], source_card: str, total_found: int
    ) -> None:
        """Update results list with synergy cards and detailed info."""
        from ..widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        type_icons = {
            "keyword": "🔑",
            "tribal": "👥",
            "ability": "✨",
            "theme": "🎯",
            "archetype": "🏛️",
        }

        for card in results:
            info = self._synergy_info.get(card.name, {})
            score = info.get("score", 0)
            synergy_type = info.get("type", "")
            reason = info.get("reason", "")
            icon = type_icons.get(synergy_type, "•")

            score_color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "dim"
            score_bar = "●" * int(score * 5) + "○" * (5 - int(score * 5))
            mana = prettify_mana(card.mana_cost) if card.mana_cost else ""

            lines = []
            line1 = f"[{score_color}]{score_bar}[/] {icon} [bold]{card.name}[/]"
            if mana:
                line1 += f"  {mana}"
            lines.append(line1)
            if reason:
                lines.append(f"    [dim italic]{reason}[/]")

            results_list.append(ListItem(Label("\n".join(lines))))

        self._update_results_header(f"Synergies for {source_card} ({total_found})")

        if results:
            results_list.focus()
            results_list.index = 0

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
        self._load_source_extras(card)

    @work
    async def _load_source_extras(self, card: Any) -> None:
        """Load extras for the source card panel."""
        await self._load_card_extras(card, "#source-card-panel")

    async def _load_card_extras(
        self, card: Any, panel_id: str = "#card-panel"
    ) -> None:
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
            lines.append(
                f"[bold yellow]Potential Combos ({len(result.potential_combos)}):[/]"
            )
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
