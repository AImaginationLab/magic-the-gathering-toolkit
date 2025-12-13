"""Reusable widgets for the MTG Spellbook TUI.

This package provides the UI components:
- CardPanel: Main card display with tabs for details, art, rulings, etc.
- ArtNavigator: Focusable art navigation with arrow keys
- CardImageWidget: Image display widget with async loading
- SynergyPanel: Source card display for synergy mode
- ResultsList: Search results list with keyboard navigation
"""

from .art_navigator import HAS_IMAGE_SUPPORT, ArtNavigator, CardImageWidget
from .card_panel import CardPanel
from .results_list import ResultsList
from .synergy_panel import SynergyPanel

__all__ = [
    "HAS_IMAGE_SUPPORT",
    "ArtNavigator",
    "CardImageWidget",
    "CardPanel",
    "ResultsList",
    "SynergyPanel",
]
