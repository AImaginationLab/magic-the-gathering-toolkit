"""Shared fixtures and helpers for screenshot tests.

This module provides shared constants, fixtures, and helper functions
used across all screenshot test modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.pilot import Pilot


# Menu item indices (0-indexed from the first item)
# Menu order: Search, Artists, Sets, Decks, Collection
MENU_SEARCH = 0
MENU_ARTISTS = 1
MENU_SETS = 2
MENU_DECKS = 3
MENU_COLLECTION = 4

# Fixed delay for menu to open (consistent timing for animations)
MENU_OPEN_DELAY = 0.3


async def navigate_via_menu(pilot: Pilot[None], menu_index: int, delay: float = 0.3) -> None:
    """Navigate to a menu item using F10 and arrow keys.

    Args:
        pilot: The Textual pilot instance.
        menu_index: Index of the menu item (0=Artists, 1=Sets, 2=Decks, 3=Collection).
        delay: Pause delay after navigation completes.
    """
    # Open menu
    await pilot.press("f10")
    await pilot.pause(delay=MENU_OPEN_DELAY)
    # Navigate down to the desired item
    for _ in range(menu_index):
        await pilot.press("down")
    # Select item
    await pilot.press("enter")
    # Wait for screen/widget to load
    await pilot.pause(delay=delay)
