"""Deck management widgets for the MTG Spellbook TUI.

This package provides deck-related UI components:
- Messages: DeckSelected, DeckCreated, AddToDeckRequested, CardAddedToDeck
- FullDeckScreen: Full-screen deck management (primary UI)
- DeckListPanel: Panel showing list of user's decks
- DeckEditorPanel: Panel for editing a deck with live stats
- DeckStatsPanel: Real-time deck statistics display
- EnhancedDeckStats: Beautiful deck statistics with visualizations
- Modals: NewDeckModal, ConfirmDeleteModal, AddToDeckModal
- FullDeckBuilder: Full-screen split-pane deck building mode (legacy)
- QuickFilterBar: CMC/Color/Type filter toggles
"""

from .editor_panel import (
    CardMovedToSideboard,
    CardQuantityChanged,
    CardRemoved,
    DeckCardItem,
    DeckEditorPanel,
    SortOrder,
)
from .enhanced_stats import EnhancedDeckStats
from .full_builder import FullDeckBuilder
from .full_screen import FullDeckScreen
from .list_panel import DeckListItem, DeckListPanel
from .messages import AddToDeckRequested, CardAddedToDeck, DeckCreated, DeckSelected
from .modals import AddToDeckModal, ConfirmDeleteModal, NewDeckModal
from .quick_filter_bar import QuickFilterBar
from .stats_bar import DeckStatsBar
from .stats_panel import DeckStatsPanel

__all__ = [
    "AddToDeckModal",
    "AddToDeckRequested",
    "CardAddedToDeck",
    "CardMovedToSideboard",
    "CardQuantityChanged",
    "CardRemoved",
    "ConfirmDeleteModal",
    "DeckCardItem",
    "DeckCreated",
    "DeckEditorPanel",
    "DeckListItem",
    "DeckListPanel",
    "DeckSelected",
    "DeckStatsBar",
    "DeckStatsPanel",
    "EnhancedDeckStats",
    "FullDeckBuilder",
    "FullDeckScreen",
    "NewDeckModal",
    "QuickFilterBar",
    "SortOrder",
]
