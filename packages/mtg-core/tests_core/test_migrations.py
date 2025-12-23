"""Comprehensive tests for database migrations module.

Tests cover all migration functions, index creation, WAL mode, artist stats cache,
and error handling. Target coverage: 90%+.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import aiosqlite
import pytest

from mtg_core.data.database.migrations import (
    _create_index_if_not_exists,
    _index_exists,
    _update_top_cards_batch,
    enable_wal_mode,
    ensure_artist_stats_cache,
    get_cached_artist_for_spotlight,
    is_artist_cache_populated,
    refresh_artist_stats_cache,
    run_mtg_migrations,
    run_scryfall_migrations,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
async def temp_db() -> AsyncIterator[aiosqlite.Connection]:
    """Create temporary in-memory database for testing."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row

    # Create minimal schema for testing
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            name TEXT,
            artist TEXT,
            setCode TEXT,
            number TEXT,
            oracle_id TEXT,
            keywords TEXT,
            edhrecRank INTEGER,
            isPromo INTEGER,
            isFunny INTEGER,
            price_usd INTEGER,
            price_usd_foil INTEGER,
            illustration_id TEXT,
            art_priority INTEGER
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sets (
            code TEXT PRIMARY KEY,
            name TEXT,
            releaseDate TEXT
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cardLegalities (
            uuid TEXT,
            commander TEXT,
            modern TEXT,
            standard TEXT,
            pioneer TEXT,
            legacy TEXT,
            vintage TEXT,
            pauper TEXT
        )
        """
    )

    await conn.commit()
    yield conn
    await conn.close()


@pytest.fixture
async def populated_db(temp_db: aiosqlite.Connection) -> aiosqlite.Connection:
    """Database with sample data for artist stats testing."""
    # Insert sample sets
    await temp_db.executemany(
        "INSERT INTO sets (code, name, releaseDate) VALUES (?, ?, ?)",
        [
            ("SET1", "Test Set 1", "2020-01-01"),
            ("SET2", "Test Set 2", "2021-06-15"),
            ("SET3", "Test Set 3", "2022-12-31"),
        ],
    )

    # Insert sample cards
    await temp_db.executemany(
        "INSERT INTO cards (id, name, artist, setCode, edhrecRank, isPromo, isFunny) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("card1", "Card One", "Alice Artist", "SET1", 100, 0, 0),
            ("card2", "Card Two", "Alice Artist", "SET1", 200, 0, 0),
            ("card3", "Card Three", "Alice Artist", "SET2", 50, 0, 0),
            ("card4", "Card Four", "Bob Artist", "SET2", 150, 0, 0),
            ("card5", "Card Five", "Bob Artist", "SET3", 300, 0, 0),
            ("card6", "Promo Card", "Alice Artist", "SET3", 75, 1, 0),  # Promo - should be excluded
            ("card7", "Funny Card", "Alice Artist", "SET3", 80, 0, 1),  # Funny - should be excluded
            ("card8", "Card Eight", "Charlie Artist", "SET1", 400, 0, 0),
        ],
    )

    await temp_db.commit()
    return temp_db


class TestEnableWalMode:
    """Tests for enable_wal_mode function."""

    async def test_enable_wal_mode_success(self, temp_db: aiosqlite.Connection) -> None:
        """Test enabling WAL mode successfully."""
        result = await enable_wal_mode(temp_db)

        assert result is True

        # Note: In-memory databases use 'memory' journal mode, not WAL
        # The function still returns True as it handles this gracefully

    async def test_enable_wal_mode_already_enabled(self, temp_db: aiosqlite.Connection) -> None:
        """Test WAL mode when already enabled."""
        # Enable first time
        await enable_wal_mode(temp_db)

        # Enable second time (should detect already enabled)
        result = await enable_wal_mode(temp_db)

        assert result is True

    async def test_enable_wal_mode_sets_synchronous(self, temp_db: aiosqlite.Connection) -> None:
        """Test WAL mode sets synchronous to NORMAL."""
        await enable_wal_mode(temp_db)

        async with temp_db.execute("PRAGMA synchronous") as cursor:
            row = await cursor.fetchone()
            assert row is not None
            # NORMAL synchronous mode is typically 1
            assert row[0] in (1, "1", "NORMAL")

    async def test_enable_wal_mode_exception_handling(self) -> None:
        """Test WAL mode handles exceptions gracefully."""
        mock_conn = AsyncMock(spec=aiosqlite.Connection)
        mock_conn.execute.side_effect = Exception("Database error")

        result = await enable_wal_mode(mock_conn)

        assert result is False


class TestIndexOperations:
    """Tests for index existence and creation functions."""

    async def test_index_exists_true(self, temp_db: aiosqlite.Connection) -> None:
        """Test checking for existing index."""
        # Create an index
        await temp_db.execute("CREATE INDEX idx_test ON cards(name)")
        await temp_db.commit()

        exists = await _index_exists(temp_db, "idx_test")

        assert exists is True

    async def test_index_exists_false(self, temp_db: aiosqlite.Connection) -> None:
        """Test checking for non-existent index."""
        exists = await _index_exists(temp_db, "idx_nonexistent")

        assert exists is False

    async def test_create_index_if_not_exists_creates_new(
        self, temp_db: aiosqlite.Connection
    ) -> None:
        """Test creating a new index."""
        result = await _create_index_if_not_exists(
            temp_db, "idx_cards_artist", "CREATE INDEX idx_cards_artist ON cards(artist)"
        )

        assert result is True

        # Verify index was created
        exists = await _index_exists(temp_db, "idx_cards_artist")
        assert exists is True

    async def test_create_index_if_not_exists_already_exists(
        self, temp_db: aiosqlite.Connection
    ) -> None:
        """Test creating index when it already exists."""
        # Create index first time
        await _create_index_if_not_exists(
            temp_db, "idx_cards_artist", "CREATE INDEX idx_cards_artist ON cards(artist)"
        )

        # Try creating again
        result = await _create_index_if_not_exists(
            temp_db, "idx_cards_artist", "CREATE INDEX idx_cards_artist ON cards(artist)"
        )

        assert result is True

    async def test_create_index_if_not_exists_handles_errors(
        self, temp_db: aiosqlite.Connection
    ) -> None:
        """Test index creation with invalid SQL."""
        result = await _create_index_if_not_exists(temp_db, "idx_invalid", "INVALID SQL STATEMENT")

        assert result is False


class TestMtgMigrations:
    """Tests for MTGJson database migrations."""

    async def test_run_mtg_migrations_success(self, temp_db: aiosqlite.Connection) -> None:
        """Test running all MTG migrations successfully."""
        results = await run_mtg_migrations(temp_db)

        assert isinstance(results, dict)
        assert "wal_mode" in results
        assert "idx_cards_artist" in results
        assert "idx_cards_setcode_number" in results
        assert "idx_cardlegalities_commander" in results
        assert "idx_cards_name_ci" in results
        assert "idx_cards_keywords" in results
        assert "idx_cards_edhrec" in results

        # Check that most migrations succeeded
        success_count = sum(1 for v in results.values() if v)
        assert success_count >= len(results) - 1  # Allow one failure

    async def test_run_mtg_migrations_creates_indexes(self, temp_db: aiosqlite.Connection) -> None:
        """Test migrations create expected indexes."""
        await run_mtg_migrations(temp_db)

        # Check some key indexes were created
        assert await _index_exists(temp_db, "idx_cards_artist")
        assert await _index_exists(temp_db, "idx_cards_setcode_number")
        assert await _index_exists(temp_db, "idx_cards_name_ci")

    async def test_run_mtg_migrations_enables_wal(self, temp_db: aiosqlite.Connection) -> None:
        """Test migrations enable WAL mode."""
        results = await run_mtg_migrations(temp_db)

        assert results["wal_mode"] is True

        # Note: In-memory databases use 'memory' journal mode, not WAL

    async def test_run_mtg_migrations_idempotent(self, temp_db: aiosqlite.Connection) -> None:
        """Test migrations can be run multiple times safely."""
        results1 = await run_mtg_migrations(temp_db)
        results2 = await run_mtg_migrations(temp_db)

        assert results1 == results2
        assert all(v for v in results2.values())

    async def test_run_mtg_migrations_partial_success(self) -> None:
        """Test migrations return partial results on some failures."""
        mock_conn = AsyncMock(spec=aiosqlite.Connection)

        # Mock WAL mode success
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(None,))
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock(return_value=None)

        async def execute_side_effect(sql, *args):  # noqa: ARG001
            if "PRAGMA journal_mode" in sql or "SELECT 1 FROM sqlite_master" in sql:
                return mock_cursor
            else:
                raise Exception("Test error")

        mock_conn.execute = AsyncMock(side_effect=execute_side_effect)

        results = await run_mtg_migrations(mock_conn)

        # WAL mode should succeed, some indexes should fail
        assert isinstance(results, dict)


class TestScryfallMigrations:
    """Tests for Scryfall database migrations."""

    async def test_run_scryfall_migrations_success(self, temp_db: aiosqlite.Connection) -> None:
        """Test running all Scryfall migrations successfully."""
        results = await run_scryfall_migrations(temp_db)

        assert isinstance(results, dict)
        assert "wal_mode" in results
        assert "idx_cards_price_range" in results
        assert "idx_cards_illustration_name" in results

    async def test_run_scryfall_migrations_enables_wal(self, temp_db: aiosqlite.Connection) -> None:
        """Test Scryfall migrations enable WAL mode."""
        results = await run_scryfall_migrations(temp_db)

        assert results["wal_mode"] is True

    async def test_run_scryfall_migrations_creates_price_index(
        self, temp_db: aiosqlite.Connection
    ) -> None:
        """Test Scryfall migrations create price index."""
        await run_scryfall_migrations(temp_db)

        assert await _index_exists(temp_db, "idx_cards_price_range")

    async def test_run_scryfall_migrations_creates_illustration_index(
        self, temp_db: aiosqlite.Connection
    ) -> None:
        """Test Scryfall migrations create illustration index."""
        await run_scryfall_migrations(temp_db)

        assert await _index_exists(temp_db, "idx_cards_illustration_name")

    async def test_run_scryfall_migrations_idempotent(self, temp_db: aiosqlite.Connection) -> None:
        """Test Scryfall migrations can be run multiple times."""
        results1 = await run_scryfall_migrations(temp_db)
        results2 = await run_scryfall_migrations(temp_db)

        assert results1 == results2


class TestArtistStatsCache:
    """Tests for artist stats cache operations."""

    async def test_ensure_artist_stats_cache_creates_table(
        self, temp_db: aiosqlite.Connection
    ) -> None:
        """Test creating artist_stats_cache table."""
        result = await ensure_artist_stats_cache(temp_db)

        assert result is True

        # Verify table exists
        async with temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='artist_stats_cache'"
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None

    async def test_ensure_artist_stats_cache_already_exists(
        self, temp_db: aiosqlite.Connection
    ) -> None:
        """Test table creation when table already exists."""
        # Create first time
        await ensure_artist_stats_cache(temp_db)

        # Create second time
        result = await ensure_artist_stats_cache(temp_db)

        assert result is False

    async def test_ensure_artist_stats_cache_has_schema(
        self, temp_db: aiosqlite.Connection
    ) -> None:
        """Test created table has expected columns."""
        await ensure_artist_stats_cache(temp_db)

        # Check columns exist
        async with temp_db.execute("PRAGMA table_info(artist_stats_cache)") as cursor:
            columns = [row[1] async for row in cursor]

        assert "artist" in columns
        assert "card_count" in columns
        assert "sets_count" in columns
        assert "first_year" in columns
        assert "last_year" in columns
        assert "avg_edhrec_rank" in columns
        assert "top_cards" in columns

    async def test_is_artist_cache_populated_true(self, temp_db: aiosqlite.Connection) -> None:
        """Test checking if cache is populated."""
        await ensure_artist_stats_cache(temp_db)
        await temp_db.execute(
            "INSERT INTO artist_stats_cache (artist, card_count, sets_count) VALUES (?, ?, ?)",
            ("Test Artist", 10, 5),
        )
        await temp_db.commit()

        result = await is_artist_cache_populated(temp_db)

        assert result is True

    async def test_is_artist_cache_populated_false(self, temp_db: aiosqlite.Connection) -> None:
        """Test checking empty cache."""
        await ensure_artist_stats_cache(temp_db)

        result = await is_artist_cache_populated(temp_db)

        assert result is False

    async def test_is_artist_cache_populated_no_table(self, temp_db: aiosqlite.Connection) -> None:
        """Test checking cache when table doesn't exist."""
        result = await is_artist_cache_populated(temp_db)

        assert result is False

    async def test_refresh_artist_stats_cache_basic(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test refreshing artist stats cache."""
        count = await refresh_artist_stats_cache(populated_db)

        assert count > 0

        # Verify data was inserted
        async with populated_db.execute(
            "SELECT * FROM artist_stats_cache ORDER BY card_count DESC"
        ) as cursor:
            rows = [dict(row) async for row in cursor]

        assert len(rows) > 0

        # Check Alice Artist stats (should have 3 non-promo/funny cards)
        alice = next((r for r in rows if r["artist"] == "Alice Artist"), None)
        assert alice is not None
        assert alice["card_count"] == 3  # card1, card2, card3 (excluding promo and funny)
        assert alice["sets_count"] == 2  # SET1, SET2

    async def test_refresh_artist_stats_cache_excludes_promo(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test cache refresh excludes promo cards."""
        await refresh_artist_stats_cache(populated_db)

        async with populated_db.execute(
            "SELECT card_count FROM artist_stats_cache WHERE artist = ?", ("Alice Artist",)
        ) as cursor:
            row = await cursor.fetchone()

        assert row is not None
        # Should be 3 cards (not 5 - excluding promo and funny)
        assert row[0] == 3

    async def test_refresh_artist_stats_cache_excludes_funny(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test cache refresh excludes funny cards."""
        await refresh_artist_stats_cache(populated_db)

        async with populated_db.execute(
            "SELECT card_count FROM artist_stats_cache WHERE artist = ?", ("Alice Artist",)
        ) as cursor:
            row = await cursor.fetchone()

        assert row is not None
        assert row[0] == 3  # Excludes funny card

    async def test_refresh_artist_stats_cache_year_range(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test cache includes year range."""
        await refresh_artist_stats_cache(populated_db)

        async with populated_db.execute(
            "SELECT first_year, last_year FROM artist_stats_cache WHERE artist = ?",
            ("Alice Artist",),
        ) as cursor:
            row = await cursor.fetchone()

        assert row is not None
        assert row[0] == 2020  # SET1
        assert row[1] == 2021  # SET2

    async def test_refresh_artist_stats_cache_avg_edhrec(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test cache computes average EDHREC rank."""
        await refresh_artist_stats_cache(populated_db)

        async with populated_db.execute(
            "SELECT avg_edhrec_rank FROM artist_stats_cache WHERE artist = ?", ("Alice Artist",)
        ) as cursor:
            row = await cursor.fetchone()

        assert row is not None
        assert row[0] is not None
        # Average of 100, 200, 50 = 116.67
        assert 110 < row[0] < 125

    async def test_refresh_artist_stats_cache_clears_old_data(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test refresh clears old cache data."""
        # First refresh
        await refresh_artist_stats_cache(populated_db)

        # Manually insert extra row
        await populated_db.execute(
            "INSERT INTO artist_stats_cache (artist, card_count, sets_count) VALUES (?, ?, ?)",
            ("Fake Artist", 999, 999),
        )
        await populated_db.commit()

        # Second refresh should clear fake data
        await refresh_artist_stats_cache(populated_db)

        async with populated_db.execute(
            "SELECT * FROM artist_stats_cache WHERE artist = ?", ("Fake Artist",)
        ) as cursor:
            row = await cursor.fetchone()

        assert row is None

    async def test_update_top_cards_batch_basic(self, populated_db: aiosqlite.Connection) -> None:
        """Test updating top cards for artists."""
        await ensure_artist_stats_cache(populated_db)
        await populated_db.execute(
            "INSERT INTO artist_stats_cache (artist, card_count, sets_count) VALUES (?, ?, ?)",
            ("Alice Artist", 15, 2),
        )
        await populated_db.commit()

        await _update_top_cards_batch(populated_db, min_cards=10)

        async with populated_db.execute(
            "SELECT top_cards FROM artist_stats_cache WHERE artist = ?", ("Alice Artist",)
        ) as cursor:
            row = await cursor.fetchone()

        assert row is not None
        assert row[0] is not None

        top_cards = json.loads(row[0])
        assert isinstance(top_cards, list)
        assert len(top_cards) > 0

    async def test_update_top_cards_batch_min_cards_filter(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test top cards only updated for artists with enough cards."""
        await ensure_artist_stats_cache(populated_db)
        await populated_db.execute(
            "INSERT INTO artist_stats_cache (artist, card_count, sets_count) VALUES (?, ?, ?)",
            ("Bob Artist", 5, 1),
        )
        await populated_db.commit()

        await _update_top_cards_batch(populated_db, min_cards=10)

        async with populated_db.execute(
            "SELECT top_cards FROM artist_stats_cache WHERE artist = ?", ("Bob Artist",)
        ) as cursor:
            row = await cursor.fetchone()

        assert row is not None
        assert row[0] is None  # Should not update top_cards

    async def test_update_top_cards_batch_no_eligible_artists(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test top cards update with no eligible artists."""
        await ensure_artist_stats_cache(populated_db)

        # Should not raise exception
        await _update_top_cards_batch(populated_db, min_cards=9999)

    async def test_update_top_cards_batch_sorts_by_edhrec(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test top cards are sorted by EDHREC rank."""
        await ensure_artist_stats_cache(populated_db)
        await populated_db.execute(
            "INSERT INTO artist_stats_cache (artist, card_count, sets_count) VALUES (?, ?, ?)",
            ("Alice Artist", 15, 2),
        )
        await populated_db.commit()

        await _update_top_cards_batch(populated_db, min_cards=1)

        async with populated_db.execute(
            "SELECT top_cards FROM artist_stats_cache WHERE artist = ?", ("Alice Artist",)
        ) as cursor:
            row = await cursor.fetchone()

        assert row is not None
        top_cards = json.loads(row[0])

        # Card Three (rank 50) should be first
        assert "Card Three" in top_cards[0]


class TestGetCachedArtistForSpotlight:
    """Tests for get_cached_artist_for_spotlight function."""

    async def test_get_cached_artist_for_spotlight_basic(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test getting random artist from cache."""
        await refresh_artist_stats_cache(populated_db)

        artist = await get_cached_artist_for_spotlight(populated_db, min_cards=1)

        assert artist is not None
        assert len(artist) == 5
        assert isinstance(artist[0], str)  # name
        assert isinstance(artist[1], int)  # card_count
        assert isinstance(artist[2], int)  # sets_count
        assert artist[3] is None or isinstance(artist[3], int)  # first_year
        assert artist[4] is None or isinstance(artist[4], int)  # last_year

    async def test_get_cached_artist_for_spotlight_min_cards(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test artist selection respects min_cards filter."""
        await refresh_artist_stats_cache(populated_db)

        artist = await get_cached_artist_for_spotlight(populated_db, min_cards=2)

        assert artist is not None
        assert artist[1] >= 2  # card_count

    async def test_get_cached_artist_for_spotlight_no_eligible(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test returns None when no eligible artists."""
        await refresh_artist_stats_cache(populated_db)

        artist = await get_cached_artist_for_spotlight(populated_db, min_cards=9999)

        assert artist is None

    async def test_get_cached_artist_for_spotlight_deterministic(
        self, populated_db: aiosqlite.Connection
    ) -> None:
        """Test same artist returned for same day."""
        await refresh_artist_stats_cache(populated_db)

        artist1 = await get_cached_artist_for_spotlight(populated_db, min_cards=1)
        artist2 = await get_cached_artist_for_spotlight(populated_db, min_cards=1)

        assert artist1 is not None
        assert artist2 is not None
        assert artist1[0] == artist2[0]  # Same artist name

    async def test_get_cached_artist_for_spotlight_empty_cache(
        self, temp_db: aiosqlite.Connection
    ) -> None:
        """Test returns None for empty cache."""
        await ensure_artist_stats_cache(temp_db)

        artist = await get_cached_artist_for_spotlight(temp_db, min_cards=1)

        assert artist is None

    async def test_get_cached_artist_for_spotlight_no_table(
        self, temp_db: aiosqlite.Connection
    ) -> None:
        """Test returns None when table doesn't exist."""
        artist = await get_cached_artist_for_spotlight(temp_db, min_cards=1)

        assert artist is None

    async def test_get_cached_artist_for_spotlight_exception_handling(self) -> None:
        """Test handles exceptions gracefully."""
        mock_conn = AsyncMock(spec=aiosqlite.Connection)
        mock_cursor = AsyncMock()
        mock_cursor.__aenter__ = AsyncMock(side_effect=Exception("Database error"))
        mock_conn.execute.return_value = mock_cursor

        artist = await get_cached_artist_for_spotlight(mock_conn, min_cards=1)

        assert artist is None
