"""Database access module."""

from .base import BaseDatabase
from .cache import CacheEntry, CardCache
from .combos import ComboCardRow, ComboDatabase, ComboRow
from .constants import (
    CARD_COLUMNS,
    CARD_COLUMNS_PLAIN,
    EXCLUDE_EXTRAS,
    EXCLUDE_FUNNY,
    EXCLUDE_PROMOS,
    VALID_FORMATS,
)
from .fts import check_fts_available, prepare_fts_query, search_cards_fts
from .manager import DatabaseManager, create_database
from .migrations import (
    enable_wal_mode,
    ensure_artist_stats_cache,
    get_cached_artist_for_spotlight,
    is_artist_cache_populated,
    refresh_artist_stats_cache,
    run_mtg_migrations,
    run_scryfall_migrations,
)
from .mtg import MTGDatabase
from .query import QueryBuilder
from .scryfall import ScryfallDatabase
from .user import (
    CollectionCardRow,
    CollectionHistoryRow,
    DeckCardRow,
    DeckRow,
    DeckSummary,
    UserDatabase,
)

__all__ = [
    "CARD_COLUMNS",
    "CARD_COLUMNS_PLAIN",
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
    "MTGDatabase",
    "QueryBuilder",
    "ScryfallDatabase",
    "UserDatabase",
    "check_fts_available",
    "create_database",
    "enable_wal_mode",
    "ensure_artist_stats_cache",
    "get_cached_artist_for_spotlight",
    "is_artist_cache_populated",
    "prepare_fts_query",
    "refresh_artist_stats_cache",
    "run_mtg_migrations",
    "run_scryfall_migrations",
    "search_cards_fts",
]
