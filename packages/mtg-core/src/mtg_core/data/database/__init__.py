"""Database access module."""

from .cache import CacheEntry, CardCache
from .combos import ComboCardRow, ComboDatabase, ComboRow
from .constants import (
    CARD_COLUMNS,
    EXCLUDE_EXTRAS,
    EXCLUDE_FUNNY,
    EXCLUDE_PROMOS,
    VALID_FORMATS,
)
from .fts import check_fts_available, prepare_fts_query, search_cards_fts
from .manager import DatabaseManager, create_database
from .mtg import MTGDatabase
from .query import QueryBuilder
from .scryfall import ScryfallDatabase
from .user import DeckCardRow, DeckRow, DeckSummary, UserDatabase

__all__ = [
    "CARD_COLUMNS",
    "EXCLUDE_EXTRAS",
    "EXCLUDE_FUNNY",
    "EXCLUDE_PROMOS",
    "VALID_FORMATS",
    "CacheEntry",
    "CardCache",
    "ComboCardRow",
    "ComboDatabase",
    "ComboRow",
    "DatabaseManager",
    "DeckCardRow",
    "DeckRow",
    "DeckSummary",
    "MTGDatabase",
    "QueryBuilder",
    "ScryfallDatabase",
    "UserDatabase",
    "check_fts_available",
    "create_database",
    "prepare_fts_query",
    "search_cards_fts",
]
