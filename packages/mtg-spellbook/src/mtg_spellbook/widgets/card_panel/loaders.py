"""Data loading utilities for card panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mtg_core.exceptions import CardNotFoundError, DatabaseNotAvailableError
from mtg_core.tools import images

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase
    from mtg_core.data.models.responses import PrintingInfo


async def load_printings(
    db: UnifiedDatabase,
    card_name: str,
) -> tuple[list[PrintingInfo], str | None]:
    """Load all printings for a card.

    Args:
        db: Unified database for card data
        card_name: Card name to search for

    Returns:
        Tuple of (printings list, error message if any)
    """
    try:
        result = await images.get_card_printings(db, card_name)
        if not result.printings:
            return [], f"[yellow]No printings found for {card_name}[/]"

        # Sort by price, highest first
        printings = sorted(
            result.printings,
            key=lambda p: p.price_usd if p.price_usd is not None else -1,
            reverse=True,
        )
        return printings, None
    except CardNotFoundError:
        return [], f"[red]Card not found: {card_name}[/]"
    except DatabaseNotAvailableError as e:
        return [], f"[red]Database error: {e}[/]"
