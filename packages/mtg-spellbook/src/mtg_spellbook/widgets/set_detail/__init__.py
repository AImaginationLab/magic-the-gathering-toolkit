"""Set detail view widgets for set exploration.

This package provides the set detail view components:
- SetDetailView: Main container with info, card list, and preview
- SetInfoPanel: Set metadata and statistics display
- SetCardList: Scrollable card list with filtering
- SetCardPreviewPanel: Selected card quick preview
"""

from __future__ import annotations

from .card_list import SetCardList
from .card_preview import SetCardPreviewPanel
from .info_panel import SetInfoPanel, SetStats
from .messages import SetCardSelected, SetDetailClosed
from .widget import SetDetailView

__all__ = [
    "SetCardList",
    "SetCardPreviewPanel",
    "SetCardSelected",
    "SetDetailClosed",
    "SetDetailView",
    "SetInfoPanel",
    "SetStats",
]
