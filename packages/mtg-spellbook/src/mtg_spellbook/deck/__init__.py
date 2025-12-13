"""Deck management widgets for the MTG Spellbook TUI.

This package provides deck-related UI components:
- Messages: DeckSelected, DeckCreated, AddToDeckRequested, CardAddedToDeck
- DeckListPanel: Panel showing list of user's decks
- DeckEditorPanel: Panel for editing a deck
- Modals: NewDeckModal, ConfirmDeleteModal, AddToDeckModal
"""

from .editor_panel import DeckCardItem, DeckEditorPanel
from .list_panel import DeckListItem, DeckListPanel
from .messages import AddToDeckRequested, CardAddedToDeck, DeckCreated, DeckSelected
from .modals import AddToDeckModal, ConfirmDeleteModal, NewDeckModal

__all__ = [
    "AddToDeckModal",
    "AddToDeckRequested",
    "CardAddedToDeck",
    "ConfirmDeleteModal",
    "DeckCardItem",
    "DeckCreated",
    "DeckEditorPanel",
    "DeckListItem",
    "DeckListPanel",
    "DeckSelected",
    "NewDeckModal",
]
