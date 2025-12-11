"""Database connection management."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import aiosqlite

from ...config import Settings, get_settings
from .cache import CardCache
from .mtg import MTGDatabase
from .scryfall import ScryfallDatabase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database lifecycle for the MCP server."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._conn: aiosqlite.Connection | None = None
        self._scryfall_conn: aiosqlite.Connection | None = None
        self._db: MTGDatabase | None = None
        self._scryfall: ScryfallDatabase | None = None
        self._cache = CardCache(max_size=self._settings.cache_max_size)

    @property
    def db(self) -> MTGDatabase:
        """Get the MTGJson database instance."""
        if self._db is None:
            raise RuntimeError("DatabaseManager not started. Call start() first.")
        return self._db

    @property
    def scryfall(self) -> ScryfallDatabase | None:
        """Get the Scryfall database instance (may be None)."""
        return self._scryfall

    async def start(self) -> None:
        """Open the database connections."""
        db_path = self._settings.mtg_db_path
        if not db_path.exists():
            raise FileNotFoundError(
                f"MTGJson database not found at {db_path}. "
                "Download AllPrintings.sqlite from https://mtgjson.com/downloads/all-files/"
            )

        self._conn = await aiosqlite.connect(db_path)
        self._conn.row_factory = aiosqlite.Row
        self._db = MTGDatabase(self._conn, self._cache)

        # Scryfall database (optional)
        scryfall_path = self._settings.scryfall_db_path
        if scryfall_path.exists():
            self._scryfall_conn = await aiosqlite.connect(scryfall_path)
            self._scryfall_conn.row_factory = aiosqlite.Row
            self._scryfall = ScryfallDatabase(self._scryfall_conn)
            logger.info("Scryfall database loaded from %s", scryfall_path)
        else:
            logger.warning("Scryfall database not found at %s", scryfall_path)

    async def stop(self) -> None:
        """Close the database connections."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            self._db = None
        if self._scryfall_conn:
            await self._scryfall_conn.close()
            self._scryfall_conn = None
            self._scryfall = None
        await self._cache.clear()


@asynccontextmanager
async def create_database(settings: Settings | None = None) -> AsyncIterator[MTGDatabase]:
    """Create a database instance as a context manager."""
    manager = DatabaseManager(settings)
    await manager.start()
    try:
        yield manager.db
    finally:
        await manager.stop()
