"""Database context manager for CLI."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from rich import print as rprint

from mtg_mcp.config import get_settings
from mtg_mcp.data.database import DatabaseManager, MTGDatabase, ScryfallDatabase


class DatabaseContext:
    """Lazy database connection manager for CLI."""

    def __init__(self) -> None:
        self._manager: DatabaseManager | None = None
        self._db: MTGDatabase | None = None
        self._scryfall: ScryfallDatabase | None = None

    async def get_db(self) -> MTGDatabase:
        """Get MTGDatabase, connecting if needed."""
        if self._manager is None:
            settings = get_settings()
            self._manager = DatabaseManager(settings)
            await self._manager.start()
            self._db = self._manager.db
            self._scryfall = self._manager.scryfall
        assert self._db is not None
        return self._db

    async def get_scryfall(self) -> ScryfallDatabase | None:
        """Get ScryfallDatabase, connecting if needed."""
        await self.get_db()
        return self._scryfall

    async def close(self) -> None:
        """Close database connections."""
        if self._manager is not None:
            await self._manager.stop()
            self._manager = None


def run_async(coro: Any) -> Any:
    """Run async coroutine in sync context."""
    return asyncio.run(coro)


def output_json(data: Any) -> None:
    """Output data as JSON (plain text, no Rich formatting)."""
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    # Use regular print, not rprint, to avoid ANSI codes in JSON output
    print(json.dumps(data, indent=2, default=str))
