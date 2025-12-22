"""Synergy and combo discovery commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from textual import work

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
        from ..collection_manager import CollectionManager

        _db: Any
        _current_results: list[Any]
        _current_card: Any
        _synergy_mode: bool
        _synergy_info: dict[str, Any]
        _pagination: PaginationState | None
        _collection_manager: CollectionManager | None

        def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...
        def _show_synergy_panel(self) -> None: ...
        def _show_message(self, message: str) -> None: ...
        def _display_synergy_results(self) -> None: ...
        def run_worker(self, coro: Any) -> Any: ...

    @work
    async def find_synergies(self, card_name: str) -> None:
        """Find synergistic cards and show in enhanced synergy panel."""
        if not self._db:
            return

        from ..widgets import EnhancedSynergyPanel

        self._synergy_mode = True
        self._synergy_info = {}

        try:
            source_card = await cards.get_card(self._db, name=card_name)
        except CardNotFoundError:
            self._show_message(f"[red]Card not found: {card_name}[/]")
            self._synergy_mode = False
            return

        result = await synergy.find_synergies(self._db, card_name=card_name, max_results=100)

        if not result.synergies:
            self._show_message(f"[yellow]No synergies found for {card_name}[/]")
            self._synergy_mode = False
            return

        # Build synergy info for card panel display
        for syn in result.synergies:
            self._synergy_info[syn.name] = {
                "type": syn.synergy_type,
                "reason": syn.reason,
                "score": syn.score,
            }

        # Hide dashboard, show synergy layout (synergy list on top, cards side-by-side)
        self.query_one("#dashboard").add_class("hidden")
        self.query_one("#results-container").add_class("hidden")  # Hide normal results
        self.query_one("#detail-container").remove_class("hidden")
        # Enable synergy layout mode (stacks synergy panel on top, cards below)
        self.query_one("#main-container").add_class("synergy-layout")

        # Show enhanced synergy panel
        synergy_panel = self.query_one("#synergy-panel", EnhancedSynergyPanel)
        synergy_panel.remove_class("hidden")

        # Get collection card names for owned-first sorting
        collection_cards: set[str] = set()
        if self._collection_manager:
            collection_cards = await self._collection_manager.get_collection_card_names()

        # Load synergies into the enhanced panel
        await synergy_panel.load_synergies(result, source_card, collection_cards)

        # Show source card in the right panel
        self._show_source_card(source_card)

        # Focus the synergy panel
        synergy_panel.focus()

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

        result = await synergy.detect_combos(self._db, card_name=card_name)

        lines: list[str] = []

        if result.combos:
            lines.append(f"[bold green]Complete Combos ({len(result.combos)}):[/]")
            for combo in result.combos:
                lines.append(f"  {combo.id} [{combo.combo_type}]: {combo.description}")

        if result.potential_combos:
            lines.append(f"[bold yellow]Potential Combos ({len(result.potential_combos)}):[/]")
            for combo in result.potential_combos:
                missing = result.missing_cards.get(combo.id, [])
                missing_str = f" (missing: {', '.join(missing)})" if missing else ""
                lines.append(f"  {combo.id}: {combo.description}{missing_str}")

        if lines:
            self._show_message("\n".join(lines))
        else:
            self._show_message(f"[dim]No known combos found for {card_name}[/]")
