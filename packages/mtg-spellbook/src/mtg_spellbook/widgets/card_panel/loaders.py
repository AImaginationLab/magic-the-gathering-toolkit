"""Data loading utilities for card panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mtg_core.exceptions import CardNotFoundError, DatabaseNotAvailableError
from mtg_core.tools import images

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase, ScryfallDatabase
    from mtg_core.data.models.responses import PrintingInfo


async def load_printings(
    scryfall: ScryfallDatabase | None,
    mtg_db: MTGDatabase | None,
    card_name: str,
) -> tuple[list[PrintingInfo], str | None]:
    """Load all printings for a card.

    Args:
        scryfall: Scryfall database for images and prices
        mtg_db: MTGJson database for card metadata
        card_name: Card name to search for

    Returns:
        Tuple of (printings list, error message if any)
    """
    if not scryfall:
        return [], "[yellow]Scryfall database not available[/]"

    try:
        result = await images.get_card_printings(scryfall, mtg_db, card_name)
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
