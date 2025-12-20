"""Unified card result item for search results and dropdowns."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Protocol, TypeVar, runtime_checkable

from textual.app import ComposeResult
from textual.widgets import Label, ListItem

from ..formatting import prettify_mana
from ..ui.formatters import CardFormatters

if TYPE_CHECKING:
    pass


@runtime_checkable
class CardLike(Protocol):
    """Protocol for card-like objects with display fields."""

    name: str
    mana_cost: str | None
    type: str | None
    rarity: str | None
    set_code: str | None
    flavor_name: str | None


# TypeVar for generic card type
CardT = TypeVar("CardT", bound=CardLike)


class CardResultItem(ListItem, Generic[CardT]):
    """Unified card result item for search results and dropdowns.

    Combines the best of both dashboard dropdown and results list designs:
    - Rarity symbol and name in rarity color
    - Flavor name as primary (e.g., SpongeBob SquarePants)
    - Original card name shown below in dim
    - Mana cost with colored symbols
    - Type icon and type line
    - Set code

    Two-line format:
        Line 1: ● Flavor Name (or Card Name)  {W}{U}{B}
        Line 2:    Card Name (if different)  ⚔ Type Line  SET
    """

    DEFAULT_CSS = """
    CardResultItem {
        height: auto;
        min-height: 3;
        padding: 0 1;
        background: #121218;
    }

    CardResultItem:hover {
        background: #1a1a2e;
    }

    CardResultItem.-highlight {
        background: #2a2a4e;
    }
    """

    def __init__(self, card: CardT) -> None:
        super().__init__()
        self.card: CardT = card

    def compose(self) -> ComposeResult:
        """Compose the result item display."""
        yield Label(self._format_card())

    def _format_card(self) -> str:
        """Format the card for display."""
        card = self.card

        # Get display name (flavor_name if present, otherwise name)
        display_name = card.flavor_name if card.flavor_name else card.name
        has_flavor = card.flavor_name is not None and card.flavor_name != card.name

        # Get formatting helpers
        rarity_color = CardFormatters.get_rarity_color(card.rarity)
        rarity_symbol = CardFormatters.get_rarity_symbol(card.rarity)
        type_icon = CardFormatters.get_type_icon(card.type or "")
        type_color = CardFormatters.get_type_color(card.type or "")

        # Mana cost
        mana = prettify_mana(card.mana_cost or "")

        # Set code
        set_code = (card.set_code or "").upper()

        # Card type (truncate if too long)
        card_type = card.type or ""

        # Build Line 1: rarity symbol + display name + mana
        line1 = f"[{rarity_color}]{rarity_symbol}[/] [bold {rarity_color}]{display_name}[/]"
        if mana:
            line1 += f"  {mana}"

        # Build Line 2: original name (if flavor) + type icon + type + set
        line2_parts = []

        # If there's a flavor name, show original name first
        if has_flavor:
            line2_parts.append(f"[dim]{card.name}[/]")

        # Type info
        if type_icon:
            line2_parts.append(f"[{type_color}]{type_icon}[/]")
        if card_type:
            line2_parts.append(f"[dim]{card_type}[/]")

        # Set code
        if set_code:
            line2_parts.append(f"[dim]{set_code}[/]")

        # Always include line2 for consistent height (even if empty)
        line2 = "   " + "  ".join(line2_parts) if line2_parts else "   "

        return f"{line1}\n{line2}"


class CardResultFormatter:
    """Static formatter for card results (when you need a string, not a widget)."""

    @staticmethod
    def format(card: CardLike) -> str:
        """Format a card for display as a rich text string.

        Use this when you need the formatted string without the ListItem wrapper.
        """
        item = CardResultItem(card)
        return item._format_card()
