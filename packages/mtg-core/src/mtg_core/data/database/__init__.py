"""Database access module."""

from .base import BaseDatabase
from .cache import CacheEntry, CardCache
from .combos import ComboCardRow, ComboDatabase, ComboRow
from .constants import (
    EXCLUDE_EXTRAS,
    EXCLUDE_FUNNY,
    EXCLUDE_PROMOS,
    VALID_FORMATS,
)
from .fts import check_fts_available, get_fts_columns, prepare_fts_query, search_cards_fts
from .manager import DatabaseManager, create_database
from .migrations import (
    enable_wal_mode,
    ensure_artist_stats_cache,
    get_cached_artist_for_spotlight,
    is_artist_cache_populated,
    refresh_artist_stats_cache,
)
from .query import QueryBuilder
from .unified import UnifiedDatabase
from .user import (
    CollectionCardRow,
    CollectionHistoryRow,
    DeckCardRow,
    DeckRow,
    DeckSummary,
    UserDatabase,
)

__all__ = [
    "EXCLUDE_EXTRAS",
    "EXCLUDE_FUNNY",
    "EXCLUDE_PROMOS",
    "VALID_FORMATS",
    "BaseDatabase",
    "CacheEntry",
    "CardCache",
    "CollectionCardRow",
    "CollectionHistoryRow",
    "ComboCardRow",
    "ComboDatabase",
    "ComboRow",
    "DatabaseManager",
    "DeckCardRow",
    "DeckRow",
    "DeckSummary",
    "QueryBuilder",
    "UnifiedDatabase",
    "UserDatabase",
    "check_fts_available",
    "create_database",
    "enable_wal_mode",
    "ensure_artist_stats_cache",
    "get_cached_artist_for_spotlight",
    "get_fts_columns",
    "is_artist_cache_populated",
    "prepare_fts_query",
    "refresh_artist_stats_cache",
    "search_cards_fts",
]
