"""Database context manager for CLI."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from mtg_core.config import get_settings
from mtg_core.data.database import DatabaseManager, UnifiedDatabase, UserDatabase

if TYPE_CHECKING:
    from types import TracebackType

    from mtg_spellbook.collection_manager import CollectionManager
    from mtg_spellbook.deck_manager import DeckManager


class DatabaseContext:
    """Lazy database connection manager for CLI.

    Supports async context manager protocol for guaranteed cleanup:
        async with DatabaseContext() as ctx:
            db = await ctx.get_db()
            ...
    """

    def __init__(self) -> None:
        self._manager: DatabaseManager | None = None
        self._db: UnifiedDatabase | None = None
        self._user: UserDatabase | None = None
        self._deck_manager: DeckManager | None = None
        self._collection_manager: CollectionManager | None = None
        self._keywords: set[str] | None = None

    async def __aenter__(self) -> DatabaseContext:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager, ensuring cleanup."""
        await self.close()

    async def get_db(self) -> UnifiedDatabase:
        """Get UnifiedDatabase, connecting if needed."""
        if self._manager is None:
            settings = get_settings()
            self._manager = DatabaseManager(settings)
            await self._manager.start()
            self._db = self._manager.db
        assert self._db is not None
        return self._db

    async def get_user_db(self) -> UserDatabase | None:
        """Get UserDatabase, connecting if needed."""
        await self.get_db()
        if self._user is None and self._manager is not None:
            self._user = self._manager.user
        return self._user

    async def get_deck_manager(self) -> DeckManager | None:
        """Get DeckManager, connecting if needed."""
        if self._deck_manager is None:
            db = await self.get_db()
            user = await self.get_user_db()
            if user is not None:
                from mtg_spellbook.deck_manager import DeckManager

                self._deck_manager = DeckManager(user, db)
        return self._deck_manager

    async def get_collection_manager(self) -> CollectionManager | None:
        """Get CollectionManager, connecting if needed."""
        if self._collection_manager is None:
            db = await self.get_db()
            user = await self.get_user_db()
            if user is not None:
                from mtg_spellbook.collection_manager import CollectionManager

                self._collection_manager = CollectionManager(user, db)
        return self._collection_manager

    async def get_keywords(self) -> set[str]:
        """Get all MTG keywords from database, cached after first load."""
        if self._keywords is None:
            db = await self.get_db()
            self._keywords = await db.get_all_keywords()
        return self._keywords

    async def close(self) -> None:
        """Close database connections."""
        if self._manager is not None:
            await self._manager.stop()
            self._manager = None
            self._db = None


def run_async(coro: Any) -> Any:
    """Run async coroutine in sync context."""
    return asyncio.run(coro)


def output_json(data: Any) -> None:
    """Output data as JSON (plain text, no Rich formatting)."""
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    # Use regular print, not rprint, to avoid ANSI codes in JSON output
    print(json.dumps(data, indent=2, default=str))
