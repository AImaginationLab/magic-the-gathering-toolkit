"""Deck editor panel widget with live stats."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import ListItem, ListView, Static

from ..formatting import prettify_mana
from ..ui.theme import ui_colors
from .messages import DeckSelected
from .stats_panel import DeckStatsPanel

if TYPE_CHECKING:
    from ..deck_manager import DeckCardWithData, DeckManager, DeckWithCards


class SortOrder(Enum):
    """Sort orders for deck cards."""

    NAME = "name"
    CMC = "cmc"
    TYPE = "type"


class DeckCardItem(ListItem):
    """A single card in the deck editor.

    Uses shared CardFormatters for consistent styling with search results.
    """

    def __init__(
        self,
        card_name: str,
        quantity: int,
        mana_cost: str | None = None,
        card_type: str | None = None,
        cmc: float = 0,
        is_sideboard: bool = False,
        set_code: str | None = None,
        collector_number: str | None = None,
        rarity: str | None = None,
        is_owned: bool | None = None,  # None = unknown, True = owned, False = needed
    ) -> None:
        super().__init__()
        self.card_name = card_name
        self.quantity = quantity
        self.mana_cost = mana_cost
        self.card_type = card_type
        self.cmc = cmc
        self.is_sideboard = is_sideboard
        self.set_code = set_code
        self.collector_number = collector_number
        self.rarity = rarity
        self.is_owned = is_owned

    def compose(self) -> ComposeResult:
        from ..ui.formatters import CardFormatters

        mana = prettify_mana(self.mana_cost) if self.mana_cost else ""
        qty_color = ui_colors.GOLD if self.quantity > 1 else "white"
        rarity_color = CardFormatters.get_rarity_color(self.rarity)
        type_icon = CardFormatters.get_type_icon(self.card_type or "")
        type_color = CardFormatters.get_type_color(self.card_type or "")

        # Ownership indicator
        if self.is_owned is True:
            owned_indicator = "[green]✓[/] "
        elif self.is_owned is False:
            owned_indicator = "[yellow]⚠[/] "
        else:
            owned_indicator = ""

        # Line 1: owned indicator + quantity + name + mana (colored by rarity)
        line1 = f"{owned_indicator}[{qty_color}]{self.quantity}x[/] [bold {rarity_color}]{self.card_name}[/]  {mana}"

        # Line 2: type icon + type (compact, optional)
        line2_parts = []
        if type_icon:
            line2_parts.append(f"[{type_color}]{type_icon}[/]")
        if self.card_type:
            type_str = self.card_type if len(self.card_type) <= 20 else self.card_type[:17] + "..."
            line2_parts.append(f"[dim]{type_str}[/]")
        line2 = "   " + "  ".join(line2_parts) if line2_parts else ""

        yield Static(f"{line1}\n{line2}" if line2 else line1)


class CardQuantityChanged(Message):
    """Message sent when a card quantity changes."""

    def __init__(self, card_name: str, new_quantity: int, is_sideboard: bool) -> None:
        super().__init__()
        self.card_name = card_name
        self.new_quantity = new_quantity
        self.is_sideboard = is_sideboard


class CardRemoved(Message):
    """Message sent when a card is removed."""

    def __init__(self, card_name: str, is_sideboard: bool) -> None:
        super().__init__()
        self.card_name = card_name
        self.is_sideboard = is_sideboard


class CardMovedToSideboard(Message):
    """Message sent when a card is moved to/from sideboard."""

    def __init__(self, card_name: str, to_sideboard: bool) -> None:
        super().__init__()
        self.card_name = card_name
        self.to_sideboard = to_sideboard


class DeckEditorPanel(Vertical):
    """Panel for editing deck contents with live statistics.

    Features:
    - Mainboard and sideboard card lists with quantities
    - Quantity adjustment with +/- keys
    - Card removal with delete key
    - Sort options (name, CMC, type)
    - Move cards between main/sideboard with 's' key
    - Real-time stats panel showing curve, types, colors
    """

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("up", "nav_up", "Up", show=False),
        Binding("down", "nav_down", "Down", show=False),
        Binding("plus", "increase_qty", "+1", show=True),
        Binding("equal", "increase_qty", "+1", show=False),
        Binding("minus", "decrease_qty", "-1", show=True),
        Binding("s", "toggle_sideboard", "Sideboard", show=True),
        Binding("delete", "remove_card", "Remove", show=True),
        Binding("backspace,q", "back_to_list", "Back", show=True),
        Binding("o", "cycle_sort", "Sort", show=True),
        Binding("v", "validate", "Validate", show=True),
        Binding("m", "focus_mainboard", "Mainboard", show=False),
        Binding("b", "focus_sideboard", "Focus Sideboard", show=False),
    ]

    DEFAULT_CSS = """
    DeckEditorPanel {
        width: 100%;
        height: 100%;
        background: #0d0d0d;
    }

    #deck-editor-header {
        height: 3;
        background: #1a1a2e;
        border-bottom: heavy #c9a227;
        padding: 0 1;
        content-align: center middle;
        color: #e6c84a;
        text-style: bold;
    }

    #deck-editor-content {
        width: 100%;
        height: 1fr;
    }

    #deck-cards-container {
        width: 60%;
        height: 100%;
        background: #0f0f0f;
        border-right: solid #3d3d3d;
    }

    #mainboard-header, #sideboard-header {
        height: 2;
        padding: 0 1;
        background: #1a1a1a;
        border-bottom: solid #3d3d3d;
    }

    #mainboard-list, #sideboard-list {
        height: 1fr;
        scrollbar-color: #c9a227;
        scrollbar-color-hover: #e6c84a;
    }

    #mainboard-list > ListItem, #sideboard-list > ListItem {
        padding: 0 1;
        height: auto;
        border-bottom: solid #1a1a1a;
        background: #121212;
    }

    #mainboard-list > ListItem:hover, #sideboard-list > ListItem:hover {
        background: #1a1a2e;
        border-left: solid #5a5a6e;
    }

    #mainboard-list > ListItem.-highlight, #sideboard-list > ListItem.-highlight {
        background: #2a2a4e;
        border-left: heavy #c9a227;
    }

    #deck-stats-container {
        width: 40%;
        height: 100%;
        background: #151515;
        padding: 1;
        overflow-y: auto;
    }

    #deck-editor-footer {
        height: 2;
        padding: 0 1;
        background: #1a1a1a;
        border-top: solid #3d3d3d;
    }

    .sort-indicator {
        color: #e6c84a;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._deck: DeckWithCards | None = None
        self._deck_manager: DeckManager | None = None
        self._card_sort_order: SortOrder = SortOrder.NAME
        self._active_list: str = "mainboard"

    def compose(self) -> ComposeResult:
        yield Static("[bold]No deck loaded[/]", id="deck-editor-header")
        with Horizontal(id="deck-editor-content"):
            with Vertical(id="deck-cards-container"):
                yield Static(
                    f"[{ui_colors.GOLD_DIM}]Mainboard[/] [dim](sorted by name)[/]",
                    id="mainboard-header",
                )
                yield ListView(id="mainboard-list")
                yield Static(
                    f"[{ui_colors.GOLD_DIM}]Sideboard[/]",
                    id="sideboard-header",
                )
                yield ListView(id="sideboard-list")
            with Vertical(id="deck-stats-container"):
                yield DeckStatsPanel(id="deck-stats-panel")
        # Enhanced footer with color-coded shortcuts
        shortcuts = [
            ("+/-", "Qty"),
            ("S", "Sideboard"),
            ("Del", "Remove"),
            ("O", "Sort"),
            ("V", "Validate"),
            ("M/B", "Main/Side"),
            ("Bksp", "Back"),
        ]
        footer_text = " · ".join(
            f"[{ui_colors.GOLD}]{key}[/] [dim]{action}[/]" for key, action in shortcuts
        )
        yield Static(footer_text, id="deck-editor-footer")

    def set_deck_manager(self, manager: DeckManager) -> None:
        """Set the deck manager for operations."""
        self._deck_manager = manager

    def update_deck(self, deck: DeckWithCards | None) -> None:
        """Update the displayed deck."""
        self._deck = deck
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Refresh the entire display."""
        deck = self._deck
        header = self.query_one("#deck-editor-header", Static)
        mainboard = self.query_one("#mainboard-list", ListView)
        sideboard = self.query_one("#sideboard-list", ListView)
        stats_panel = self.query_one("#deck-stats-panel", DeckStatsPanel)

        mainboard.clear()
        sideboard.clear()

        if deck is None:
            header.update("[bold]No deck loaded[/]")
            stats_panel.update_stats(None)
            # Add empty state message
            mainboard.append(
                ListItem(
                    Static(
                        f"\n[dim]No deck selected.\n\nPress [{ui_colors.GOLD}]Backspace[/] to return to deck list.[/]"
                    )
                )
            )
            return

        # Update header
        format_str = f" ({deck.format})" if deck.format else ""
        header.update(f"[bold {ui_colors.GOLD_DIM}]{deck.name}[/]{format_str}")

        # Update sort indicator with prominent display
        sort_arrows = {"name": "▲ A-Z", "cmc": "▲ CMC", "type": "▲ Type"}
        sort_label = sort_arrows.get(self._card_sort_order.value, self._card_sort_order.value)
        main_header = self.query_one("#mainboard-header", Static)
        main_header.update(
            f"[{ui_colors.GOLD_DIM}]Mainboard[/] [{ui_colors.GOLD}]{deck.mainboard_count}[/] "
            f"[{ui_colors.GOLD}]{sort_label}[/]"
        )

        side_header = self.query_one("#sideboard-header", Static)
        side_header.update(
            f"[{ui_colors.GOLD_DIM}]Sideboard[/] [{ui_colors.GOLD}]{deck.sideboard_count}[/]"
        )

        # Sort and populate mainboard
        sorted_main = self._sort_cards(deck.mainboard)
        if sorted_main:
            for card in sorted_main:
                mainboard.append(self._create_card_item(card, is_sideboard=False))
        else:
            # Add empty mainboard message
            mainboard.append(
                ListItem(
                    Static(
                        f"\n[dim]Deck is empty.\n\nAdd cards with [{ui_colors.GOLD}]Ctrl+E[/] from search.[/]"
                    )
                )
            )

        # Sort and populate sideboard
        sorted_side = self._sort_cards(deck.sideboard)
        for card in sorted_side:
            sideboard.append(self._create_card_item(card, is_sideboard=True))

        # Update stats
        stats_panel.update_stats(deck)

        # Focus the active list
        if self._active_list == "mainboard" and deck.mainboard:
            mainboard.focus()
        elif self._active_list == "sideboard" and deck.sideboard:
            sideboard.focus()

    def _sort_cards(self, cards: list[DeckCardWithData]) -> list[DeckCardWithData]:
        """Sort cards based on current sort order."""
        if self._card_sort_order == SortOrder.NAME:
            return sorted(cards, key=lambda c: c.card_name.lower())
        if self._card_sort_order == SortOrder.CMC:
            return sorted(
                cards, key=lambda c: (c.card.cmc or 0 if c.card else 0, c.card_name.lower())
            )
        if self._card_sort_order == SortOrder.TYPE:

            def type_key(c: DeckCardWithData) -> tuple[int, str]:
                type_order = {
                    "Creature": 0,
                    "Planeswalker": 1,
                    "Instant": 2,
                    "Sorcery": 3,
                    "Artifact": 4,
                    "Enchantment": 5,
                    "Land": 6,
                }
                if c.card and c.card.type:
                    for t, order in type_order.items():
                        if t in c.card.type:
                            return (order, c.card_name.lower())
                return (99, c.card_name.lower())

            return sorted(cards, key=type_key)
        # Fallback for any future SortOrder values
        return list(cards)

    def _create_card_item(self, card: DeckCardWithData, is_sideboard: bool) -> DeckCardItem:
        """Create a DeckCardItem from card data."""
        mana_cost = card.card.mana_cost if card.card else None
        card_type = card.card.type if card.card else None
        cmc = card.card.cmc or 0 if card.card else 0
        rarity = card.card.rarity if card.card else None
        return DeckCardItem(
            card_name=card.card_name,
            quantity=card.quantity,
            mana_cost=mana_cost,
            card_type=card_type,
            cmc=cmc,
            is_sideboard=is_sideboard,
            set_code=card.set_code,
            collector_number=card.collector_number,
            rarity=rarity,
        )

    def _get_selected_card(self) -> tuple[DeckCardItem | None, bool]:
        """Get the currently selected card and whether it's in sideboard."""
        mainboard = self.query_one("#mainboard-list", ListView)
        sideboard = self.query_one("#sideboard-list", ListView)

        if (
            self._active_list == "mainboard"
            and mainboard.highlighted_child
            and isinstance(mainboard.highlighted_child, DeckCardItem)
        ):
            return mainboard.highlighted_child, False
        if (
            self._active_list == "sideboard"
            and sideboard.highlighted_child
            and isinstance(sideboard.highlighted_child, DeckCardItem)
        ):
            return sideboard.highlighted_child, True

        return None, False

    def action_nav_up(self) -> None:
        """Navigate up in the active list."""
        list_id = f"#{self._active_list}-list"
        self.query_one(list_id, ListView).action_cursor_up()

    def action_nav_down(self) -> None:
        """Navigate down in the active list."""
        list_id = f"#{self._active_list}-list"
        self.query_one(list_id, ListView).action_cursor_down()

    def action_focus_mainboard(self) -> None:
        """Focus the mainboard list."""
        self._active_list = "mainboard"
        self.query_one("#mainboard-list", ListView).focus()

    def action_focus_sideboard(self) -> None:
        """Focus the sideboard list."""
        self._active_list = "sideboard"
        self.query_one("#sideboard-list", ListView).focus()

    @on(ListView.Highlighted)
    def on_list_highlighted(self, event: ListView.Highlighted) -> None:
        """Track which list is active."""
        if event.list_view.id == "mainboard-list":
            self._active_list = "mainboard"
        elif event.list_view.id == "sideboard-list":
            self._active_list = "sideboard"

    def action_cycle_sort(self) -> None:
        """Cycle through sort orders."""
        orders = list(SortOrder)
        current_idx = orders.index(self._card_sort_order)
        self._card_sort_order = orders[(current_idx + 1) % len(orders)]
        self._refresh_display()
        self.app.notify(
            f"Sorted by [{ui_colors.GOLD}]{self._card_sort_order.value}[/]",
            severity="information",
            timeout=2,
        )

    def action_increase_qty(self) -> None:
        """Increase quantity of selected card."""
        card, is_sideboard = self._get_selected_card()
        if card and self._deck_manager and self._deck:
            new_qty = card.quantity + 1
            location = "sideboard" if is_sideboard else "mainboard"
            self._change_quantity(card.card_name, new_qty, is_sideboard)
            self.app.notify(
                f"[{ui_colors.GOLD}]{card.card_name}[/]: {card.quantity}x → {new_qty}x ({location})",
                severity="information",
                timeout=2,
            )

    def action_decrease_qty(self) -> None:
        """Decrease quantity of selected card."""
        card, is_sideboard = self._get_selected_card()
        if card and self._deck_manager and self._deck:
            new_qty = max(1, card.quantity - 1)
            if new_qty != card.quantity:
                location = "sideboard" if is_sideboard else "mainboard"
                self._change_quantity(card.card_name, new_qty, is_sideboard)
                self.app.notify(
                    f"[{ui_colors.GOLD}]{card.card_name}[/]: {card.quantity}x → {new_qty}x ({location})",
                    severity="information",
                    timeout=2,
                )

    def _change_quantity(self, card_name: str, new_quantity: int, is_sideboard: bool) -> None:
        """Change card quantity via deck manager."""
        if not self._deck_manager or not self._deck:
            return

        async def do_change() -> None:
            assert self._deck_manager is not None
            assert self._deck is not None
            await self._deck_manager.set_quantity(
                self._deck.id, card_name, new_quantity, is_sideboard
            )
            # Reload deck data
            updated = await self._deck_manager.get_deck(self._deck.id)
            self.update_deck(updated)
            self.post_message(CardQuantityChanged(card_name, new_quantity, is_sideboard))

        self.app.call_later(do_change)

    def action_remove_card(self) -> None:
        """Remove the selected card from the deck."""
        card, is_sideboard = self._get_selected_card()
        if card and self._deck_manager and self._deck:
            self._remove_card(card.card_name, is_sideboard)

    def _remove_card(self, card_name: str, is_sideboard: bool) -> None:
        """Remove card via deck manager."""
        if not self._deck_manager or not self._deck:
            return

        async def do_remove() -> None:
            assert self._deck_manager is not None
            assert self._deck is not None
            await self._deck_manager.remove_card(self._deck.id, card_name, is_sideboard)
            # Reload deck data
            updated = await self._deck_manager.get_deck(self._deck.id)
            self.update_deck(updated)
            self.app.notify(f"Removed {card_name}")
            self.post_message(CardRemoved(card_name, is_sideboard))

        self.app.call_later(do_remove)

    def action_toggle_sideboard(self) -> None:
        """Move selected card to/from sideboard."""
        card, is_sideboard = self._get_selected_card()
        if card and self._deck_manager and self._deck:
            self._move_card(card.card_name, not is_sideboard)

    def _move_card(self, card_name: str, to_sideboard: bool) -> None:
        """Move card between mainboard and sideboard."""
        if not self._deck_manager or not self._deck:
            return

        async def do_move() -> None:
            assert self._deck_manager is not None
            assert self._deck is not None
            if to_sideboard:
                await self._deck_manager.move_to_sideboard(self._deck.id, card_name)
            else:
                await self._deck_manager.move_to_mainboard(self._deck.id, card_name)
            # Reload deck data
            updated = await self._deck_manager.get_deck(self._deck.id)
            self.update_deck(updated)
            location = "sideboard" if to_sideboard else "mainboard"
            self.app.notify(f"Moved {card_name} to {location}")
            self.post_message(CardMovedToSideboard(card_name, to_sideboard))

        self.app.call_later(do_move)

    def action_back_to_list(self) -> None:
        """Go back to deck list."""
        self.post_message(DeckSelected(-1))

    def action_validate(self) -> None:
        """Validate the deck."""
        if not self._deck or not self._deck_manager:
            return

        async def do_validate() -> None:
            assert self._deck_manager is not None
            assert self._deck is not None
            try:
                result = await self._deck_manager.validate_deck(self._deck.id)
                if result.is_valid:
                    self.app.notify(
                        f"[green]✓ Deck is valid![/] Format: {result.format}",
                        severity="information",
                        timeout=4,
                    )
                else:
                    # Show up to 5 issues inline, suggest full analysis for more
                    total_issues = len(result.issues)
                    display_limit = 5
                    issue_msgs = [
                        f"{issue.card_name}: {issue.issue}"
                        + (f" - {issue.details}" if issue.details else "")
                        for issue in result.issues[:display_limit]
                    ]
                    issues = "\n".join(f"- {msg}" for msg in issue_msgs)
                    if total_issues > display_limit:
                        issues += f"\n\n[dim]...and {total_issues - display_limit} more issues[/]"
                    self.app.notify(
                        f"[red]✗ Invalid deck ({total_issues} issues)[/]\n{issues}",
                        severity="warning",
                        timeout=10,
                    )
            except Exception as e:
                self.app.notify(f"Validation error: {e}", severity="error")

        self.app.call_later(do_validate)
