"""Base database class with shared connection patterns."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite

from ...config import get_settings

logger = logging.getLogger(__name__)


class BaseDatabase:
    """Base class for all database access.

    Provides shared patterns for connection management, query execution with
    concurrency limiting, and slow query logging.

    Subclasses receive an already-connected aiosqlite.Connection and use the
    _execute() context manager for all queries.
    """

    def __init__(
        self,
        db: aiosqlite.Connection,
        max_connections: int = 5,
        semaphore: asyncio.Semaphore | None = None,
    ):
        """Initialize with a database connection.

        Args:
            db: An open aiosqlite connection with row_factory set.
            max_connections: Maximum concurrent queries (only used if semaphore is None).
            semaphore: Optional shared semaphore for global concurrency control.
                      If provided, max_connections is ignored.
        """
        self._db = db
        # Use shared semaphore if provided, otherwise create our own
        self._semaphore = semaphore if semaphore is not None else asyncio.Semaphore(max_connections)

    @property
    def connection(self) -> aiosqlite.Connection:
        """Access the underlying database connection."""
        return self._db

    @asynccontextmanager
    async def _execute(
        self, query: str, params: Sequence[Any] = ()
    ) -> AsyncIterator[aiosqlite.Cursor]:
        """Execute a query with concurrency limiting and optional slow query logging.

        Args:
            query: SQL query string.
            params: Query parameters.

        Yields:
            aiosqlite.Cursor for the executed query.
        """
        settings = get_settings()
        async with self._semaphore:
            start = time.perf_counter()
            try:
                async with self._db.execute(query, params) as cursor:
                    yield cursor
            except Exception as e:
                logger.error(
                    "SQL error: %s\nQuery: %s\nParams: %s",
                    e,
                    query[:500],
                    params[:20] if params else [],
                )
                raise
            finally:
                if settings.log_slow_queries:
                    duration_ms = (time.perf_counter() - start) * 1000
                    if duration_ms > settings.slow_query_threshold_ms:
                        logger.warning("Slow query (%.1fms): %s", duration_ms, query[:100])
