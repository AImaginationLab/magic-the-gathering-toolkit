"""Database connection management."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import aiosqlite

from ...config import Settings, get_settings
from .cache import CardCache
from .combos import ComboDatabase
from .unified import UnifiedDatabase
from .user import UserDatabase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database lifecycle for the MCP server."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._conn: aiosqlite.Connection | None = None
        self._db: UnifiedDatabase | None = None
        self._user: UserDatabase | None = None
        self._combos: ComboDatabase | None = None
        self._cache = CardCache(max_size=self._settings.cache_max_size)

    @property
    def db(self) -> UnifiedDatabase:
        """Get the unified MTG database instance."""
        if self._db is None:
            raise RuntimeError("DatabaseManager not started. Call start() first.")
        return self._db

    @property
    def user(self) -> UserDatabase | None:
        """Get the user database instance (may be None if not initialized)."""
        return self._user

    @property
    def combos(self) -> ComboDatabase | None:
        """Get the combo database instance (may be None if not initialized)."""
        return self._combos

    async def start(self) -> None:
        """Open the database connections."""
        db_path = self._settings.mtg_db_path
        if not db_path.exists():
            raise FileNotFoundError(
                f"MTG database not found at {db_path}. "
                "Run 'create-mtg-db' to build the unified database."
            )

        max_conn = self._settings.db_max_connections

        self._conn = await aiosqlite.connect(db_path)
        self._conn.row_factory = aiosqlite.Row

        # Set performance pragmas (WAL mode set during database creation)
        await self._conn.execute("PRAGMA cache_size = -64000")  # 64MB
        await self._conn.execute("PRAGMA mmap_size = 268435456")  # 256MB
        await self._conn.execute("PRAGMA busy_timeout = 5000")  # 5 seconds
        await self._conn.execute("PRAGMA temp_store = MEMORY")

        self._db = UnifiedDatabase(self._conn, self._cache, max_connections=max_conn)
        logger.info("Unified MTG database loaded from %s", db_path)

        # User database (always created, stores decks/collections)
        try:
            self._user = UserDatabase(self._settings.user_db_path, max_connections=max_conn)
            await self._user.connect()
        except (aiosqlite.Error, OSError):
            logger.exception("Failed to open user database at %s", self._settings.user_db_path)
            self._user = None

        # Combo database (stores combo data)
        try:
            self._combos = ComboDatabase(self._settings.combo_db_path, max_connections=max_conn)
            await self._combos.connect()
        except (aiosqlite.Error, OSError):
            logger.exception("Failed to open combo database at %s", self._settings.combo_db_path)
            self._combos = None

    async def start_user_db(self) -> UserDatabase:
        """Explicitly start user database. Used by apps that need deck management."""
        if self._user is None:
            self._user = UserDatabase(
                self._settings.user_db_path,
                max_connections=self._settings.db_max_connections,
            )
            await self._user.connect()
        return self._user

    async def stop(self) -> None:
        """Close the database connections."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            self._db = None
        if self._user:
            await self._user.close()
            self._user = None
        if self._combos:
            await self._combos.close()
            self._combos = None
        await self._cache.clear()


@asynccontextmanager
async def create_database(settings: Settings | None = None) -> AsyncIterator[UnifiedDatabase]:
    """Create a database instance as a context manager."""
    manager = DatabaseManager(settings)
    await manager.start()
    try:
        yield manager.db
    finally:
        await manager.stop()
