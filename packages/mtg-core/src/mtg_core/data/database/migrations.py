"""Database migrations and schema optimizations.

This module provides idempotent migration functions for adding performance
indexes and enabling database optimizations. All migrations are safe to run
multiple times.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger(__name__)

ARTIST_STATS_CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS artist_stats_cache (
    artist TEXT PRIMARY KEY,
    card_count INTEGER NOT NULL,
    sets_count INTEGER NOT NULL,
    first_year INTEGER,
    last_year INTEGER,
    avg_edhrec_rank REAL,
    top_cards TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_artist_stats_card_count
    ON artist_stats_cache(card_count DESC);
"""


async def enable_wal_mode(conn: aiosqlite.Connection) -> bool:
    """Enable WAL (Write-Ahead Logging) mode for better concurrent read performance.

    WAL mode allows multiple readers to operate concurrently with a single writer,
    significantly improving performance for read-heavy workloads.

    Args:
        conn: The database connection.

    Returns:
        True if WAL mode was enabled or already active, False on failure.
    """
    try:
        async with conn.execute("PRAGMA journal_mode") as cursor:
            row = await cursor.fetchone()
            current_mode = row[0] if row else None

        if current_mode and current_mode.lower() == "wal":
            logger.debug("WAL mode already enabled")
            return True

        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        logger.info("Enabled WAL mode for database")
        return True
    except Exception:
        logger.exception("Failed to enable WAL mode")
        return False


async def _index_exists(conn: aiosqlite.Connection, index_name: str) -> bool:
    """Check if an index exists in the database."""
    async with conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,),
    ) as cursor:
        return await cursor.fetchone() is not None


async def _create_index_if_not_exists(
    conn: aiosqlite.Connection,
    index_name: str,
    create_sql: str,
) -> bool:
    """Create an index if it doesn't already exist.

    Args:
        conn: The database connection.
        index_name: Name of the index to check/create.
        create_sql: The CREATE INDEX SQL statement.

    Returns:
        True if index was created or already exists, False on failure.
    """
    try:
        if await _index_exists(conn, index_name):
            logger.debug("Index %s already exists", index_name)
            return True

        logger.info("Creating index %s", index_name)
        await conn.execute(create_sql)
        await conn.commit()
        return True
    except Exception:
        logger.exception("Failed to create index %s", index_name)
        return False


async def run_mtg_migrations(conn: aiosqlite.Connection) -> dict[str, bool]:
    """Run all migrations for the MTGJson database.

    Creates performance indexes for common query patterns. All migrations
    are idempotent - safe to run multiple times.

    Args:
        conn: The MTGJson database connection.

    Returns:
        Dict mapping migration name to success status.
    """
    results: dict[str, bool] = {}

    # Enable WAL mode first
    results["wal_mode"] = await enable_wal_mode(conn)

    # Index: cards by artist (for artist browsing/filtering)
    # Note: The schema optimization doc suggests this index already exists,
    # but we ensure it's present for installations that may not have it
    results["idx_cards_artist"] = await _create_index_if_not_exists(
        conn,
        "idx_cards_artist",
        "CREATE INDEX idx_cards_artist ON cards(artist)",
    )

    # Index: cards by setCode + number (for set browsing and card lookup by collector number)
    results["idx_cards_setcode_number"] = await _create_index_if_not_exists(
        conn,
        "idx_cards_setcode_number",
        "CREATE INDEX idx_cards_setcode_number ON cards(setCode, number)",
    )

    # Index: cardLegalities by format + status (for format-legal card filtering)
    # Using commander as primary example - most common format filter
    results["idx_cardlegalities_commander"] = await _create_index_if_not_exists(
        conn,
        "idx_cardlegalities_commander",
        "CREATE INDEX idx_cardlegalities_commander ON cardLegalities(uuid) WHERE commander = 'Legal'",
    )

    results["idx_cardlegalities_modern"] = await _create_index_if_not_exists(
        conn,
        "idx_cardlegalities_modern",
        "CREATE INDEX idx_cardlegalities_modern ON cardLegalities(uuid) WHERE modern = 'Legal'",
    )

    results["idx_cardlegalities_standard"] = await _create_index_if_not_exists(
        conn,
        "idx_cardlegalities_standard",
        "CREATE INDEX idx_cardlegalities_standard ON cardLegalities(uuid) WHERE standard = 'Legal'",
    )

    results["idx_cardlegalities_pioneer"] = await _create_index_if_not_exists(
        conn,
        "idx_cardlegalities_pioneer",
        "CREATE INDEX idx_cardlegalities_pioneer ON cardLegalities(uuid) WHERE pioneer = 'Legal'",
    )

    results["idx_cardlegalities_legacy"] = await _create_index_if_not_exists(
        conn,
        "idx_cardlegalities_legacy",
        "CREATE INDEX idx_cardlegalities_legacy ON cardLegalities(uuid) WHERE legacy = 'Legal'",
    )

    results["idx_cardlegalities_vintage"] = await _create_index_if_not_exists(
        conn,
        "idx_cardlegalities_vintage",
        "CREATE INDEX idx_cardlegalities_vintage ON cardLegalities(uuid) WHERE vintage = 'Legal'",
    )

    results["idx_cardlegalities_pauper"] = await _create_index_if_not_exists(
        conn,
        "idx_cardlegalities_pauper",
        "CREATE INDEX idx_cardlegalities_pauper ON cardLegalities(uuid) WHERE pauper = 'Legal'",
    )

    # Index: case-insensitive name search
    results["idx_cards_name_ci"] = await _create_index_if_not_exists(
        conn,
        "idx_cards_name_ci",
        "CREATE INDEX idx_cards_name_ci ON cards(name COLLATE NOCASE)",
    )

    # Index: cards with keywords (for keyword-based filtering)
    results["idx_cards_keywords"] = await _create_index_if_not_exists(
        conn,
        "idx_cards_keywords",
        "CREATE INDEX idx_cards_keywords ON cards(keywords) WHERE keywords IS NOT NULL",
    )

    # Index: EDHREC rank (for commander suggestions and sorting)
    results["idx_cards_edhrec"] = await _create_index_if_not_exists(
        conn,
        "idx_cards_edhrec",
        "CREATE INDEX idx_cards_edhrec ON cards(edhrecRank) WHERE edhrecRank IS NOT NULL",
    )

    # Log summary
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    if success_count == total_count:
        logger.info("All %d MTG migrations completed successfully", total_count)
    else:
        logger.warning(
            "MTG migrations: %d/%d succeeded",
            success_count,
            total_count,
        )

    return results


async def run_scryfall_migrations(conn: aiosqlite.Connection) -> dict[str, bool]:
    """Run all migrations for the Scryfall database.

    Args:
        conn: The Scryfall database connection.

    Returns:
        Dict mapping migration name to success status.
    """
    results: dict[str, bool] = {}

    # Enable WAL mode
    results["wal_mode"] = await enable_wal_mode(conn)

    # Index: price range queries
    results["idx_cards_price_range"] = await _create_index_if_not_exists(
        conn,
        "idx_cards_price_range",
        "CREATE INDEX idx_cards_price_range ON cards(price_usd, price_usd_foil) WHERE price_usd IS NOT NULL",
    )

    # Index: illustration grouping for unique artwork queries
    results["idx_cards_illustration_name"] = await _create_index_if_not_exists(
        conn,
        "idx_cards_illustration_name",
        "CREATE INDEX idx_cards_illustration_name ON cards(name, illustration_id, art_priority)",
    )

    # Log summary
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    if success_count == total_count:
        logger.info("All %d Scryfall migrations completed successfully", total_count)
    else:
        logger.warning(
            "Scryfall migrations: %d/%d succeeded",
            success_count,
            total_count,
        )

    return results


async def ensure_artist_stats_cache(conn: aiosqlite.Connection) -> bool:
    """Ensure the artist_stats_cache table exists.

    Args:
        conn: The aiosqlite connection to the MTGJson database.

    Returns:
        True if the table was created, False if it already existed.
    """
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='artist_stats_cache'"
    ) as cursor:
        exists = await cursor.fetchone() is not None

    if not exists:
        logger.info("Creating artist_stats_cache table")
        await conn.executescript(ARTIST_STATS_CACHE_SCHEMA)
        await conn.commit()
        return True

    return False


async def refresh_artist_stats_cache(conn: aiosqlite.Connection) -> int:
    """Refresh the artist stats cache with current data.

    Computes statistics for all artists and stores them in the cache table.
    This is an expensive operation that should be run periodically (e.g., daily
    or after database updates).

    Args:
        conn: The aiosqlite connection to the MTGJson database.

    Returns:
        Number of artists cached.
    """
    await ensure_artist_stats_cache(conn)

    logger.info("Refreshing artist stats cache...")

    # Clear existing cache
    await conn.execute("DELETE FROM artist_stats_cache")

    # Compute and insert artist stats using a single INSERT...SELECT
    insert_query = """
    INSERT INTO artist_stats_cache (
        artist, card_count, sets_count, first_year, last_year,
        avg_edhrec_rank, top_cards, updated_at
    )
    SELECT
        c.artist,
        COUNT(DISTINCT c.name) as card_count,
        COUNT(DISTINCT c.setCode) as sets_count,
        MIN(CAST(SUBSTR(s.releaseDate, 1, 4) AS INTEGER)) as first_year,
        MAX(CAST(SUBSTR(s.releaseDate, 1, 4) AS INTEGER)) as last_year,
        AVG(c.edhrecRank) as avg_edhrec_rank,
        NULL as top_cards,
        CURRENT_TIMESTAMP as updated_at
    FROM cards c
    JOIN sets s ON c.setCode = s.code
    WHERE c.artist IS NOT NULL
        AND c.artist != ''
        AND (c.isPromo IS NULL OR c.isPromo = 0)
        AND (c.isFunny IS NULL OR c.isFunny = 0)
    GROUP BY c.artist
    """
    await conn.execute(insert_query)

    # Get count before updating top cards
    async with conn.execute("SELECT COUNT(*) FROM artist_stats_cache") as cursor:
        row = await cursor.fetchone()
        artist_count = row[0] if row else 0

    # Update top_cards JSON for artists with significant card counts
    await _update_top_cards_batch(conn, min_cards=10)

    await conn.commit()
    logger.info("Artist stats cache refreshed: %d artists", artist_count)
    return artist_count


async def _update_top_cards_batch(conn: aiosqlite.Connection, min_cards: int = 10) -> None:
    """Update top_cards JSON for artists with significant card counts.

    Args:
        conn: The aiosqlite connection.
        min_cards: Minimum card count to include top cards for an artist.
    """
    # Get artists that need top cards populated
    async with conn.execute(
        "SELECT artist FROM artist_stats_cache WHERE card_count >= ?",
        (min_cards,),
    ) as cursor:
        artists = [row[0] async for row in cursor]

    if not artists:
        return

    # For each artist, get their top 5 cards by EDHREC rank
    for artist in artists:
        async with conn.execute(
            """
            SELECT DISTINCT c.name
            FROM cards c
            WHERE c.artist = ?
                AND c.edhrecRank IS NOT NULL
                AND (c.isPromo IS NULL OR c.isPromo = 0)
                AND (c.isFunny IS NULL OR c.isFunny = 0)
            ORDER BY c.edhrecRank ASC
            LIMIT 5
            """,
            (artist,),
        ) as cursor:
            top_cards = [row[0] async for row in cursor]

        if top_cards:
            await conn.execute(
                "UPDATE artist_stats_cache SET top_cards = ? WHERE artist = ?",
                (json.dumps(top_cards), artist),
            )


async def is_artist_cache_populated(conn: aiosqlite.Connection) -> bool:
    """Check if the artist stats cache has data.

    Args:
        conn: The aiosqlite connection.

    Returns:
        True if the cache has at least one entry.
    """
    try:
        async with conn.execute("SELECT 1 FROM artist_stats_cache LIMIT 1") as cursor:
            return await cursor.fetchone() is not None
    except Exception:
        # Table doesn't exist
        return False


async def get_cached_artist_for_spotlight(
    conn: aiosqlite.Connection,
    min_cards: int = 20,
) -> tuple[str, int, int, int | None, int | None] | None:
    """Get a random artist from the cache for dashboard spotlight.

    Uses a deterministic daily seed so the same artist appears all day.

    Args:
        conn: The aiosqlite connection.
        min_cards: Minimum number of cards an artist must have.

    Returns:
        Tuple of (artist, card_count, sets_count, first_year, last_year) or None.
    """
    import hashlib
    from datetime import date

    # Get deterministic seed for today
    today = date.today().isoformat()
    seed = int(hashlib.md5(today.encode()).hexdigest()[:8], 16)

    # Get count of eligible artists
    try:
        async with conn.execute(
            "SELECT COUNT(*) FROM artist_stats_cache WHERE card_count >= ?",
            (min_cards,),
        ) as cursor:
            row = await cursor.fetchone()
            total = row[0] if row else 0
    except Exception:
        return None

    if total == 0:
        return None

    # Select artist deterministically
    offset = seed % total
    async with conn.execute(
        """
        SELECT artist, card_count, sets_count, first_year, last_year
        FROM artist_stats_cache
        WHERE card_count >= ?
        ORDER BY artist
        LIMIT 1 OFFSET ?
        """,
        (min_cards, offset),
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            return (row[0], row[1], row[2], row[3], row[4])

    return None
