"""FTS5 full-text search support for MTG card database."""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger(__name__)


def prepare_fts_query(search_text: str) -> str:
    """Prepare a search string for FTS5 MATCH query.

    Handles special characters and converts to FTS5 query syntax.
    Supports phrases in quotes and prefix matching with *.
    """
    # If the query looks like a phrase (contains spaces and no operators), wrap it
    if " " in search_text and not any(c in search_text for c in ['"', "*", "OR", "AND"]):
        # Split into words and search as prefix matches for better partial matching
        words = search_text.split()
        # Escape special FTS5 characters
        escaped_words = []
        for word in words:
            # Remove FTS5 special characters that could break the query
            clean_word = re.sub(r'["\'\(\)\*\-\+\:]', "", word)
            if clean_word:
                escaped_words.append(f'"{clean_word}"*')
        return " ".join(escaped_words)
    else:
        # Single word or advanced query - just clean up dangerous chars
        clean = re.sub(r'["\'\(\)\-\+\:]', "", search_text)
        if clean:
            return f'"{clean}"*'
        return ""


async def check_fts_available(db: aiosqlite.Connection) -> bool:
    """Check if FTS5 table exists and is available."""
    try:
        async with db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cards_fts'"
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None
    except Exception:
        return False


async def search_cards_fts(
    db: aiosqlite.Connection,
    query: str,
    limit: int = 100,
    search_name: bool = True,
    search_type: bool = True,
    search_text: bool = True,
) -> list[str]:
    """Search cards using FTS5 full-text search.

    Args:
        db: Database connection
        query: Search query string
        limit: Maximum number of UUIDs to return
        search_name: Include card name in search
        search_type: Include card type in search
        search_text: Include oracle text in search

    Returns:
        List of matching card UUIDs, ordered by relevance (bm25 rank).
        Returns empty list if FTS5 is not available or query is invalid.
    """
    fts_query = prepare_fts_query(query)
    if not fts_query:
        return []

    # Build column filter for targeted search
    columns = []
    if search_name:
        columns.append("name")
    if search_type:
        columns.append("type")
    if search_text:
        columns.append("text")

    if not columns:
        return []

    # Build FTS5 query with column targeting
    if len(columns) == 3:
        # Search all columns - simpler syntax
        match_expr = fts_query
    else:
        # Target specific columns using FTS5 column filter syntax
        column_queries = [f"{col}:{fts_query}" for col in columns]
        match_expr = " OR ".join(column_queries)

    try:
        uuids: list[str] = []
        async with db.execute(
            """
            SELECT uuid FROM cards_fts
            WHERE cards_fts MATCH ?
            ORDER BY bm25(cards_fts)
            LIMIT ?
            """,
            (match_expr, limit),
        ) as cursor:
            async for row in cursor:
                uuids.append(row[0])
        return uuids
    except Exception as e:
        logger.warning("FTS5 search failed: %s", e)
        return []


async def search_cards_fts_with_params(
    db: aiosqlite.Connection,
    query: str,
    additional_conditions: Sequence[str] = (),
    additional_params: Sequence[object] = (),
    limit: int = 100,
) -> list[str]:
    """Search cards using FTS5 with additional SQL conditions.

    Args:
        db: Database connection
        query: Search query string
        additional_conditions: Extra WHERE conditions (joined with AND)
        additional_params: Parameters for additional conditions
        limit: Maximum number of UUIDs to return

    Returns:
        List of matching card UUIDs, ordered by relevance.
    """
    fts_query = prepare_fts_query(query)
    if not fts_query:
        return []

    conditions = ["cards_fts MATCH ?"]
    params: list[object] = [fts_query]

    for cond in additional_conditions:
        conditions.append(cond)
    params.extend(additional_params)
    params.append(limit)

    where_clause = " AND ".join(conditions)

    try:
        uuids: list[str] = []
        async with db.execute(
            f"""
            SELECT uuid FROM cards_fts
            WHERE {where_clause}
            ORDER BY bm25(cards_fts)
            LIMIT ?
            """,
            params,
        ) as cursor:
            async for row in cursor:
                uuids.append(row[0])
        return uuids
    except Exception as e:
        logger.warning("FTS5 search failed: %s", e)
        return []
