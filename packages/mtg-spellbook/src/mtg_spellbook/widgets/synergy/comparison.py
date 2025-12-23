"""Comparison view widget for side-by-side synergy comparison."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Static

from ...formatting import prettify_mana
from ...ui.theme import ui_colors
from .messages import SynergyCompareClear, SynergyCompareRemove, SynergySelected

if TYPE_CHECKING:
    from mtg_core.data.models.responses import SynergyResult


class CompareSlot(Vertical):
    """A single slot in the comparison view."""

    is_selected: reactive[bool] = reactive(False)

    def __init__(
        self,
        slot_index: int,
        synergy: SynergyResult | None = None,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.slot_index = slot_index
        self._synergy = synergy

    def compose(self) -> ComposeResult:
        yield Static(
            self._render_header(),
            id=f"compare-slot-header-{self.slot_index}",
            classes="compare-slot-header",
        )
        with VerticalScroll(classes="compare-slot-content"):
            yield Static(
                self._render_slot_content(),
                id=f"compare-slot-body-{self.slot_index}",
                classes="compare-slot-body",
            )

    def _render_header(self) -> str:
        """Render the slot header."""
        if not self._synergy:
            return f"[{ui_colors.TEXT_DIM}]Empty Slot {self.slot_index + 1}[/]"

        syn = self._synergy
        mana = prettify_mana(syn.mana_cost) if syn.mana_cost else ""
        score_color = self._get_score_color(min(syn.score, 1.0))
        score_pct = min(100, int(syn.score * 100))

        header = f"[bold {ui_colors.GOLD}]{syn.name}[/] {mana}"
        header += f"  [{score_color}][{score_pct}%][/]"
        return header

    def _render_slot_content(self) -> str:
        """Render the slot content."""
        if not self._synergy:
            return f"[{ui_colors.TEXT_DIM}]Press [c] on a synergy to add[/]"

        syn = self._synergy
        lines: list[str] = []

        # Type line
        if syn.type_line:
            lines.append(f"[{ui_colors.TEXT_DIM}]{syn.type_line}[/]")
            lines.append("")

        # Synergy type
        type_display = syn.synergy_type.title()
        lines.append(f"[bold]Type:[/] {type_display}")
        lines.append("")

        # Reason
        lines.append("[bold]Why:[/]")
        lines.append(f"  {syn.reason}")
        lines.append("")

        # Score visualization
        lines.append(f"[bold]Score:[/] {self._render_score_bar(syn.score)}")

        return "\n".join(lines)

    def _render_score_bar(self, score: float) -> str:
        """Render a visual score bar (capped at 100%)."""
        filled = min(20, int(score * 20))
        bar = "[" * filled + "." * (20 - filled)
        color = self._get_score_color(min(score, 1.0))
        return f"[{color}]{bar}[/] [{color}]{min(100, int(score * 100))}%[/]"

    def _get_score_color(self, score: float) -> str:
        """Get color for score display."""
        if score >= 0.8:
            return ui_colors.SYNERGY_STRONG
        elif score >= 0.6:
            return ui_colors.SYNERGY_MODERATE
        elif score >= 0.4:
            return ui_colors.SYNERGY_WEAK
        return ui_colors.TEXT_DIM

    def set_synergy(self, synergy: SynergyResult | None) -> None:
        """Set the synergy for this slot."""
        self._synergy = synergy
        self._update_display()

    def _update_display(self) -> None:
        """Update the slot display."""
        try:
            header = self.query_one(f"#compare-slot-header-{self.slot_index}", Static)
            header.update(self._render_header())
        except NoMatches:
            pass

        try:
            body = self.query_one(f"#compare-slot-body-{self.slot_index}", Static)
            body.update(self._render_slot_content())
        except NoMatches:
            pass

    def watch_is_selected(self, selected: bool) -> None:
        """Update styling when selection changes."""
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")

    @property
    def synergy(self) -> SynergyResult | None:
        """Get the synergy in this slot."""
        return self._synergy


class ComparisonView(Vertical, can_focus=True):
    """Side-by-side comparison view for synergies."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape", "close", "Close"),
        Binding("left,h", "prev_slot", "Prev", show=False),
        Binding("right,l", "next_slot", "Next", show=False),
        Binding("enter", "select_current", "Select"),
        Binding("r,delete", "remove_current", "Remove"),
        Binding("c", "clear_all", "Clear All"),
    ]

    is_visible: reactive[bool] = reactive(False, toggle_class="visible")
    selected_slot: reactive[int] = reactive(0)

    MAX_SLOTS: ClassVar[int] = 4

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._synergies: list[SynergyResult] = []

    def compose(self) -> ComposeResult:
        yield Static(
            self._render_header(),
            id="compare-view-header",
            classes="compare-view-header",
        )
        with Horizontal(id="compare-slots-container", classes="compare-slots-container"):
            for i in range(self.MAX_SLOTS):
                yield CompareSlot(
                    i,
                    synergy=None,
                    id=f"compare-slot-{i}",
                    classes="compare-slot",
                )
        yield Static(
            self._render_decision_helper(),
            id="compare-decision",
            classes="compare-decision",
        )
        yield Static(
            self._render_statusbar(),
            id="compare-statusbar",
            classes="compare-statusbar",
        )

    def _render_header(self) -> str:
        """Render the comparison header."""
        count = len(self._synergies)
        return (
            f"[bold {ui_colors.GOLD}]Compare Synergies[/] "
            f"[{ui_colors.TEXT_DIM}]({count}/{self.MAX_SLOTS} cards)[/]"
        )

    def _render_decision_helper(self) -> str:
        """Render the decision helper section."""
        if len(self._synergies) < 2:
            return f"[{ui_colors.TEXT_DIM}]Add at least 2 cards to compare[/]"

        lines: list[str] = []
        lines.append(f"[bold {ui_colors.GOLD}]Decision Helper:[/]")

        # Find best/worst scores
        scores = [(syn.name, syn.score) for syn in self._synergies]
        if scores:
            best = max(scores, key=lambda x: x[1])
            worst = min(scores, key=lambda x: x[1])

            if best[1] != worst[1]:
                lines.append(
                    f"  - [{ui_colors.SYNERGY_STRONG}]{best[0]}[/] has highest synergy score "
                    f"({int(best[1] * 100)}%)"
                )

        # CMC comparison
        cmcs: list[tuple[str, float | None]] = []
        for syn in self._synergies:
            # Parse CMC from mana cost if available
            cmc = self._estimate_cmc(syn.mana_cost) if syn.mana_cost else None
            cmcs.append((syn.name, cmc))

        valid_cmcs = [(name, cmc) for name, cmc in cmcs if cmc is not None]
        if len(valid_cmcs) >= 2:
            cheapest = min(valid_cmcs, key=lambda x: x[1] or 999)
            lines.append(
                f"  - [{ui_colors.SYNERGY_MODERATE}]{cheapest[0]}[/] is cheapest to cast "
                f"(CMC {int(cheapest[1] or 0)})"
            )

        # Type comparison
        types = set()
        for syn in self._synergies:
            types.add(syn.synergy_type)
        if len(types) > 1:
            lines.append(
                f"  - Cards offer [{ui_colors.GOLD}]{len(types)} different[/] synergy types"
            )

        # Recommendation
        lines.append("")
        if best[1] >= 0.8:
            lines.append(
                f"[bold]Recommendation:[/] [{ui_colors.SYNERGY_STRONG}]{best[0]}[/] "
                f"for strongest synergy"
            )
        else:
            lines.append("[bold]Recommendation:[/] Consider deck needs and mana curve")

        return "\n".join(lines)

    def _estimate_cmc(self, mana_cost: str | None) -> float | None:
        """Estimate CMC from mana cost string."""
        if not mana_cost:
            return None

        import re

        cmc = 0.0

        # Count generic mana
        generic = re.findall(r"\{(\d+)\}", mana_cost)
        for g in generic:
            cmc += int(g)

        # Count colored mana
        colored = re.findall(r"\{([WUBRG])\}", mana_cost)
        cmc += len(colored)

        # Count hybrid as 1 each
        hybrid = re.findall(r"\{[WUBRGC]/[WUBRGCP]\}", mana_cost)
        cmc += len(hybrid)

        return cmc if cmc > 0 else None

    def _render_statusbar(self) -> str:
        """Render the status bar."""
        parts = [
            f"[{ui_colors.TEXT_DIM}]arrows: navigate slots[/]",
            f"[{ui_colors.GOLD}]Enter[/]: view full",
            f"[{ui_colors.GOLD}]r[/]: remove",
            f"[{ui_colors.GOLD}]c[/]: clear all",
            f"[{ui_colors.GOLD}]Esc[/]: close",
        ]
        return "  |  ".join(parts)

    def add_synergy(self, synergy: SynergyResult) -> bool:
        """Add a synergy to the comparison. Returns True if added."""
        # Check if already in comparison
        for existing in self._synergies:
            if existing.name == synergy.name:
                return False

        # Check if at capacity
        if len(self._synergies) >= self.MAX_SLOTS:
            return False

        self._synergies.append(synergy)
        self._update_display()
        return True

    def remove_synergy(self, synergy: SynergyResult) -> bool:
        """Remove a synergy from the comparison. Returns True if removed."""
        for i, existing in enumerate(self._synergies):
            if existing.name == synergy.name:
                self._synergies.pop(i)
                self._update_display()
                return True
        return False

    def clear_all(self) -> None:
        """Clear all synergies from comparison."""
        self._synergies.clear()
        self.selected_slot = 0
        self._update_display()

    def _update_display(self) -> None:
        """Update all display elements."""
        # Update slots
        for i in range(self.MAX_SLOTS):
            try:
                slot = self.query_one(f"#compare-slot-{i}", CompareSlot)
                synergy = self._synergies[i] if i < len(self._synergies) else None
                slot.set_synergy(synergy)
            except NoMatches:
                pass

        # Update header
        try:
            header = self.query_one("#compare-view-header", Static)
            header.update(self._render_header())
        except NoMatches:
            pass

        # Update decision helper
        try:
            decision = self.query_one("#compare-decision", Static)
            decision.update(self._render_decision_helper())
        except NoMatches:
            pass

    def watch_selected_slot(self, slot: int) -> None:
        """Update slot selection visual."""
        for i in range(self.MAX_SLOTS):
            try:
                slot_widget = self.query_one(f"#compare-slot-{i}", CompareSlot)
                slot_widget.is_selected = i == slot
            except NoMatches:
                pass

    def watch_is_visible(self, visible: bool) -> None:
        """Update display state."""
        self.display = visible

    def action_close(self) -> None:
        """Close the comparison view."""
        self.is_visible = False

    def action_prev_slot(self) -> None:
        """Move to previous slot."""
        if self._synergies:
            self.selected_slot = (self.selected_slot - 1) % len(self._synergies)

    def action_next_slot(self) -> None:
        """Move to next slot."""
        if self._synergies:
            self.selected_slot = (self.selected_slot + 1) % len(self._synergies)

    def action_select_current(self) -> None:
        """Select the current slot's synergy for full view."""
        if 0 <= self.selected_slot < len(self._synergies):
            synergy = self._synergies[self.selected_slot]
            self.post_message(SynergySelected(synergy))

    def action_remove_current(self) -> None:
        """Remove the current slot's synergy."""
        if 0 <= self.selected_slot < len(self._synergies):
            synergy = self._synergies[self.selected_slot]
            self.post_message(SynergyCompareRemove(synergy))
            self.remove_synergy(synergy)

    def action_clear_all(self) -> None:
        """Clear all comparisons."""
        self.clear_all()
        self.post_message(SynergyCompareClear())

    def has_synergy(self, synergy: SynergyResult) -> bool:
        """Check if synergy is in comparison."""
        return any(s.name == synergy.name for s in self._synergies)

    @property
    def synergy_count(self) -> int:
        """Get count of synergies in comparison."""
        return len(self._synergies)

    @property
    def synergies(self) -> list[SynergyResult]:
        """Get all synergies in comparison."""
        return self._synergies.copy()
