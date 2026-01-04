"""Database connection management."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import aiosqlite

from ...config import Settings, get_settings
from .cache import CardCache
from .unified import UnifiedDatabase
from .user import UserDatabase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database lifecycle for the MCP server.

    IMPORTANT: Each FastAPI worker should have its own DatabaseManager instance.
    The connection and databases are NOT safe to share across processes/workers.
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._conn: aiosqlite.Connection | None = None
        self._db: UnifiedDatabase | None = None
        self._user: UserDatabase | None = None
        self._cache = CardCache(max_size=self._settings.cache_max_size)
        # Global semaphore to limit total concurrent DB operations across all databases
        self._global_semaphore = asyncio.Semaphore(self._settings.db_max_connections)

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

    async def start(self) -> None:
        """Open the database connections."""
        db_path = self._settings.mtg_db_path
        if not db_path.exists():
            raise FileNotFoundError(
                f"MTG database not found at {db_path}. "
                "Run 'create-mtg-db' to build the unified database."
            )

        # Create connection with better concurrency settings
        self._conn = await aiosqlite.connect(
            db_path,
            timeout=30.0,  # Increase timeout for concurrent access
            check_same_thread=False,  # Allow access from multiple async tasks
        )
        self._conn.row_factory = aiosqlite.Row

        # Set performance pragmas
        await self._conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for concurrency
        await self._conn.execute("PRAGMA synchronous = NORMAL")  # Balance safety and speed
        await self._conn.execute("PRAGMA cache_size = -64000")  # 64MB page cache
        await self._conn.execute("PRAGMA mmap_size = 268435456")  # 256MB memory-mapped I/O
        await self._conn.execute("PRAGMA busy_timeout = 10000")  # 10 seconds for lock waits
        await self._conn.execute("PRAGMA temp_store = MEMORY")
        await self._conn.execute("PRAGMA threads = 4")  # Enable multi-threaded operations

        # Pass the global semaphore to the database
        self._db = UnifiedDatabase(self._conn, self._cache, semaphore=self._global_semaphore)
        logger.info("Unified MTG database loaded from %s", db_path)

        # User database (always created, stores decks/collections)
        user_db = UserDatabase(self._settings.user_db_path, semaphore=self._global_semaphore)
        try:
            await user_db.connect()
            self._user = user_db
        except (aiosqlite.Error, OSError):
            logger.exception("Failed to open user database at %s", self._settings.user_db_path)
            # CRITICAL: Close connection if opened to avoid orphaned threads
            if user_db._conn:
                try:  # noqa: SIM105 - can't use suppress with await
                    await user_db.close()
                except Exception:
                    pass
            self._user = None

        # NOTE: ComboDatabase is NOT initialized here because the combo database
        # is managed by SpellbookComboDetector which uses a different schema
        # (Commander Spellbook format downloaded from GitHub releases).

    async def start_user_db(self) -> UserDatabase:
        """Explicitly start user database. Used by apps that need deck management."""
        if self._user is None:
            self._user = UserDatabase(
                self._settings.user_db_path,
                semaphore=self._global_semaphore,
            )
            await self._user.connect()
        return self._user

    async def stop(self) -> None:
        """Close the database connections."""
        if self._conn:
            # Save reference to thread before closing
            conn_thread = self._conn if hasattr(self._conn, "join") else None
            await self._conn.close()

            # Wait for aiosqlite thread to terminate to avoid hang on exit
            if conn_thread is not None:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, conn_thread.join, 2.0)

            self._conn = None
            self._db = None

        if self._user:
            await self._user.close()
            self._user = None

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
