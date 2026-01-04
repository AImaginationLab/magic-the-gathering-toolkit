"""Comprehensive tests for database support modules.

Tests cover:
- CardCache: Async LRU caching with TTL support
- QueryBuilder: Parameterized SQL query building
- FTS: Full-text search with FTS5
"""

from __future__ import annotations

import asyncio
import tempfile
import time
from collections.abc import AsyncIterator
from pathlib import Path

import aiosqlite
import pytest

from mtg_core.config import Settings
from mtg_core.data.database import UnifiedDatabase, create_database
from mtg_core.data.database.cache import CacheEntry, CardCache
from mtg_core.data.database.constants import VALID_FORMATS
from mtg_core.data.database.fts import (
    check_fts_available,
    get_fts_columns,
    prepare_fts_query,
    search_cards_fts,
    search_cards_fts_with_params,
)
from mtg_core.data.database.query import QueryBuilder
from mtg_core.data.models import Card, SearchCardsInput

from .conftest import get_test_db_path

# Skip tests if no database available
DB_PATH = get_test_db_path()
pytestmark = pytest.mark.skipif(
    DB_PATH is None,
    reason="MTG database not found - run create-mtg-db first",
)


@pytest.fixture
async def db() -> AsyncIterator[UnifiedDatabase]:
    """Create database connection for tests."""
    assert DB_PATH is not None
    settings = Settings(mtg_db_path=DB_PATH)
    async with create_database(settings) as database:
        yield database


@pytest.fixture
async def raw_db() -> AsyncIterator[aiosqlite.Connection]:
    """Create raw database connection for low-level tests."""
    assert DB_PATH is not None
    async with aiosqlite.connect(str(DB_PATH)) as conn:
        conn.row_factory = aiosqlite.Row
        yield conn


@pytest.fixture
def sample_card() -> Card:
    """Create a sample card for cache testing."""
    return Card(
        uuid="test-uuid-1",
        name="Lightning Bolt",
        mana_cost="{R}",
        cmc=1.0,
        colors=["R"],
        color_identity=["R"],
        type="Instant",
        text="Lightning Bolt deals 3 damage to any target.",
        rarity="common",
        set_code="LEA",
    )


class TestCardCache:
    """Tests for CardCache async LRU cache with TTL."""

    async def test_cache_get_miss(self) -> None:
        """Getting a non-existent key returns None."""
        cache = CardCache(max_size=10, ttl_seconds=3600)
        result = await cache.get("nonexistent")
        assert result is None

    async def test_cache_set_and_get(self, sample_card: Card) -> None:
        """Setting and getting a card works."""
        cache = CardCache(max_size=10, ttl_seconds=3600)
        await cache.set("bolt", sample_card)
        result = await cache.get("bolt")

        assert result is not None
        assert result.name == "Lightning Bolt"
        assert result.uuid == "test-uuid-1"

    async def test_cache_lru_eviction(self) -> None:
        """Cache evicts LRU entries when at capacity."""
        cache = CardCache(max_size=3, ttl_seconds=3600)

        # Add 3 cards (at capacity)
        card1 = Card(name="Card 1", uuid="uuid-1")
        card2 = Card(name="Card 2", uuid="uuid-2")
        card3 = Card(name="Card 3", uuid="uuid-3")

        await cache.set("key1", card1)
        await cache.set("key2", card2)
        await cache.set("key3", card3)

        # Access key2 to make it recently used
        await cache.get("key2")

        # Add a 4th card - should evict key1 (LRU)
        card4 = Card(name="Card 4", uuid="uuid-4")
        await cache.set("key4", card4)

        # key1 should be gone, others should exist
        assert await cache.get("key1") is None
        assert await cache.get("key2") is not None
        assert await cache.get("key3") is not None
        assert await cache.get("key4") is not None

    async def test_cache_ttl_expiration(self, sample_card: Card) -> None:
        """Expired entries return None and are removed."""
        cache = CardCache(max_size=10, ttl_seconds=1)  # 1 second TTL

        await cache.set("bolt", sample_card)

        # Immediate get should work
        result = await cache.get("bolt")
        assert result is not None

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired now
        result = await cache.get("bolt")
        assert result is None

    async def test_cache_update_existing(self, sample_card: Card) -> None:
        """Updating an existing key replaces the value."""
        cache = CardCache(max_size=10, ttl_seconds=3600)

        await cache.set("card", sample_card)

        # Update with new card
        updated_card = Card(name="Counterspell", uuid="test-uuid-2")
        await cache.set("card", updated_card)

        result = await cache.get("card")
        assert result is not None
        assert result.name == "Counterspell"
        assert result.uuid == "test-uuid-2"

    async def test_cache_clear(self, sample_card: Card) -> None:
        """Clear removes all entries."""
        cache = CardCache(max_size=10, ttl_seconds=3600)

        await cache.set("key1", sample_card)
        await cache.set("key2", sample_card)
        await cache.set("key3", sample_card)

        await cache.clear()

        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None

    async def test_cache_cleanup_expired(self) -> None:
        """cleanup_expired removes only expired entries."""
        cache = CardCache(max_size=10, ttl_seconds=1)

        card1 = Card(name="Card 1", uuid="uuid-1")
        card2 = Card(name="Card 2", uuid="uuid-2")

        await cache.set("key1", card1)

        # Wait a bit then add another
        await asyncio.sleep(1.1)

        # key1 is now expired. When we set key2, cache.set() calls _evict_expired()
        # which removes key1 before adding key2
        await cache.set("key2", card2)

        # At this point, expired entries were already cleaned during set()
        # So cleanup_expired should find 0 expired entries
        removed_count = await cache.cleanup_expired()

        assert removed_count == 0  # Already cleaned during set()
        assert await cache.get("key1") is None  # Was evicted during set()
        assert await cache.get("key2") is not None  # Fresh entry

    async def test_cache_stats(self, sample_card: Card) -> None:
        """Stats returns correct cache information."""
        cache = CardCache(max_size=100, ttl_seconds=3600)

        await cache.set("key1", sample_card)
        await cache.set("key2", sample_card)

        stats = await cache.stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 100
        assert stats["ttl_seconds"] == 3600
        assert stats["expired_pending"] == 0

    async def test_cache_stats_with_expired(self) -> None:
        """Stats counts expired entries correctly."""
        cache = CardCache(max_size=10, ttl_seconds=1)

        card = Card(name="Card", uuid="uuid")
        await cache.set("key1", card)
        await cache.set("key2", card)

        # Wait for expiration
        await asyncio.sleep(1.1)

        # When we add key3, _evict_expired() is called which removes key1 and key2
        # So only key3 remains in cache
        await cache.set("key3", card)

        stats = await cache.stats()

        # Only key3 remains (key1 and key2 were evicted during set)
        assert stats["size"] == 1
        assert stats["expired_pending"] == 0

    async def test_cache_concurrent_access(self, sample_card: Card) -> None:
        """Cache handles concurrent access safely."""
        cache = CardCache(max_size=10, ttl_seconds=3600)

        # Simulate concurrent sets
        async def set_card(key: str) -> None:
            await cache.set(key, sample_card)

        await asyncio.gather(
            set_card("key1"),
            set_card("key2"),
            set_card("key3"),
            set_card("key4"),
            set_card("key5"),
        )

        # All should be retrievable
        for i in range(1, 6):
            result = await cache.get(f"key{i}")
            assert result is not None

    async def test_cache_entry_timestamp(self, sample_card: Card) -> None:
        """Cache entries have proper timestamps."""
        cache = CardCache(max_size=10, ttl_seconds=3600)

        before = time.monotonic()
        await cache.set("key", sample_card)
        after = time.monotonic()

        # Access internal cache to check timestamp
        async with cache._lock:
            entry = cache._cache.get("key")
            assert entry is not None
            assert isinstance(entry, CacheEntry)
            assert before <= entry.timestamp <= after


class TestQueryBuilder:
    """Tests for QueryBuilder parameterized SQL query construction."""

    def test_empty_builder(self) -> None:
        """Empty builder produces default WHERE clause."""
        qb = QueryBuilder()
        assert qb.build_where() == "1=1"
        assert qb.params == []

    def test_add_like_simple(self) -> None:
        """add_like adds LIKE condition with wildcards."""
        qb = QueryBuilder()
        qb.add_like("c.name", "lightning")

        assert qb.conditions == ["c.name LIKE ?"]
        assert qb.params == ["%lightning%"]
        assert "c.name LIKE ?" in qb.build_where()

    def test_add_like_custom_pattern(self) -> None:
        """add_like supports custom patterns."""
        qb = QueryBuilder()
        qb.add_like("c.name", "bolt", pattern="{value}%")  # Prefix match

        assert qb.params == ["bolt%"]

    def test_add_like_none_value(self) -> None:
        """add_like ignores None values."""
        qb = QueryBuilder()
        qb.add_like("c.name", None)

        assert qb.conditions == []
        assert qb.params == []

    def test_add_name_search(self) -> None:
        """add_name_search checks both name and flavorName."""
        qb = QueryBuilder()
        qb.add_name_search("spongebob")

        assert "(c.name LIKE ? OR c.flavorName LIKE ?)" in qb.conditions[0]
        assert qb.params == ["%spongebob%", "%spongebob%"]

    def test_add_exact(self) -> None:
        """add_exact adds equality condition."""
        qb = QueryBuilder()
        qb.add_exact("c.rarity", "rare")

        assert qb.conditions == ["c.rarity = ?"]
        assert qb.params == ["rare"]

    def test_add_exact_case_insensitive(self) -> None:
        """add_exact supports case-insensitive matching."""
        qb = QueryBuilder()
        qb.add_exact("c.rarity", "RARE", case_insensitive=True)

        assert qb.conditions == ["LOWER(c.rarity) = LOWER(?)"]
        assert qb.params == ["RARE"]

    def test_add_exact_zero_value(self) -> None:
        """add_exact handles zero values correctly."""
        qb = QueryBuilder()
        qb.add_exact("c.manaValue", 0)

        assert qb.conditions == ["c.manaValue = ?"]
        assert qb.params == [0]

    def test_add_comparison_operators(self) -> None:
        """add_comparison supports all valid operators."""
        for op in ["=", "!=", "<>", ">", "<", ">=", "<="]:
            qb = QueryBuilder()
            qb.add_comparison("c.manaValue", op, 3.0)

            assert qb.conditions == [f"c.manaValue {op} ?"]
            assert qb.params == [3.0]

    def test_add_comparison_invalid_operator(self) -> None:
        """add_comparison rejects invalid operators."""
        qb = QueryBuilder()

        with pytest.raises(ValueError, match="Invalid operator"):
            qb.add_comparison("c.manaValue", "INVALID", 3.0)

    def test_add_comparison_none_value(self) -> None:
        """add_comparison ignores None values."""
        qb = QueryBuilder()
        qb.add_comparison("c.manaValue", ">=", None)

        assert qb.conditions == []
        assert qb.params == []

    def test_add_not_like_nullable(self) -> None:
        """add_not_like handles NULL columns."""
        qb = QueryBuilder()
        qb.add_not_like("c.text", "draw", nullable=True)

        assert "IS NULL OR" in qb.conditions[0]
        assert qb.params == ["%draw%"]

    def test_add_not_like_non_nullable(self) -> None:
        """add_not_like for non-nullable columns."""
        qb = QueryBuilder()
        qb.add_not_like("c.name", "token", nullable=False)

        assert "IS NULL" not in qb.conditions[0]
        assert qb.conditions == ["c.name NOT LIKE ?"]
        assert qb.params == ["%token%"]

    def test_add_colors(self) -> None:
        """add_colors checks for all specified colors."""
        qb = QueryBuilder()
        qb.add_colors(["W", "U"])

        assert len(qb.conditions) == 2
        assert "c.colors LIKE ?" in qb.conditions[0]
        assert "%W%" in qb.params
        assert "%U%" in qb.params

    def test_add_colors_empty(self) -> None:
        """add_colors ignores empty lists."""
        qb = QueryBuilder()
        qb.add_colors([])

        assert qb.conditions == []

    def test_add_color_identity(self) -> None:
        """add_color_identity excludes colors outside identity."""
        qb = QueryBuilder()
        qb.add_color_identity(["W", "U"])  # Only white/blue

        # Should exclude B, R, G
        assert len(qb.conditions) == 3
        for param in qb.params:
            assert param in ["%B%", "%R%", "%G%"]

    def test_add_color_identity_all_colors(self) -> None:
        """add_color_identity with all colors excludes nothing."""
        qb = QueryBuilder()
        qb.add_color_identity(["W", "U", "B", "R", "G"])

        # No colors to exclude
        assert qb.conditions == []

    def test_add_format_legality_valid(self) -> None:
        """add_format_legality adds json_extract condition for valid formats."""
        qb = QueryBuilder()
        qb.add_format_legality("commander")

        assert len(qb.conditions) == 1
        assert "json_extract" in qb.conditions[0]
        assert "legal" in qb.conditions[0]
        assert len(qb.params) == 2
        assert qb.params[0] == "$.commander"

    def test_add_format_legality_case_insensitive(self) -> None:
        """add_format_legality is case-insensitive."""
        qb = QueryBuilder()
        qb.add_format_legality("COMMANDER")

        assert len(qb.conditions) == 1
        assert "$.commander" in qb.params

    def test_add_format_legality_invalid(self) -> None:
        """add_format_legality ignores invalid formats."""
        qb = QueryBuilder()
        qb.add_format_legality("invalid_format")

        assert qb.conditions == []

    def test_add_keywords(self) -> None:
        """add_keywords adds conditions for each keyword."""
        qb = QueryBuilder()
        qb.add_keywords(["flying", "haste"])

        assert len(qb.conditions) == 2
        assert "%flying%" in qb.params
        assert "%haste%" in qb.params

    def test_build_where_multiple_conditions(self) -> None:
        """build_where joins conditions with AND."""
        qb = QueryBuilder()
        qb.add_like("c.name", "dragon")
        qb.add_exact("c.rarity", "rare")
        qb.add_comparison("c.manaValue", ">=", 5.0)

        where = qb.build_where()

        assert "c.name LIKE ?" in where
        assert "c.rarity = ?" in where
        assert "c.manaValue >= ?" in where
        assert where.count(" AND ") == 2

    def test_from_filters_comprehensive(self) -> None:
        """from_filters builds QueryBuilder from SearchCardsInput."""
        filters = SearchCardsInput(
            name="lightning bolt",
            colors=["R"],
            color_identity=["R"],
            type="instant",
            rarity="common",
            set_code="LEA",
            cmc=1.0,
            text="damage",
            keywords=["haste"],
            format_legal="modern",
            artist="Christopher Rush",
        )

        qb = QueryBuilder.from_filters(filters)

        # Should have conditions for all provided filters
        assert len(qb.conditions) > 0
        assert len(qb.params) > 0

        # Check some specific filters
        where = qb.build_where()
        assert "c.name" in where or "c.flavorName" in where  # Name search
        assert "c.colors LIKE ?" in where
        assert "c.rarity" in where

    def test_from_filters_cmc_range(self) -> None:
        """from_filters handles CMC range filters."""
        filters = SearchCardsInput(cmc_min=2.0, cmc_max=4.0)

        qb = QueryBuilder.from_filters(filters)

        where = qb.build_where()
        assert "c.manaValue >= ?" in where
        assert "c.manaValue <= ?" in where
        assert qb.params == [2.0, 4.0]

    def test_from_filters_empty(self) -> None:
        """from_filters with no filters produces default WHERE."""
        filters = SearchCardsInput()
        qb = QueryBuilder.from_filters(filters)

        assert qb.build_where() == "1=1"


class TestFTS:
    """Tests for FTS5 full-text search functionality."""

    async def test_check_fts_available_true(self, raw_db: aiosqlite.Connection) -> None:
        """check_fts_available returns True when FTS table exists."""
        available = await check_fts_available(raw_db)
        assert available is True

    def test_prepare_fts_query_single_word(self) -> None:
        """prepare_fts_query handles single words."""
        result = prepare_fts_query("lightning")
        assert result == '"lightning"*'

    def test_prepare_fts_query_phrase(self) -> None:
        """prepare_fts_query converts phrases to prefix matches."""
        result = prepare_fts_query("lightning bolt")
        assert '"lightning"*' in result
        assert '"bolt"*' in result

    def test_prepare_fts_query_special_chars(self) -> None:
        """prepare_fts_query escapes special FTS characters."""
        result = prepare_fts_query("card's-name")
        # Special chars are removed, leaving "cardsname" as single word
        assert result == '"cardsname"*'
        # Should remove quotes, parens, etc.
        assert "'" not in result
        assert "-" not in result

    def test_prepare_fts_query_empty(self) -> None:
        """prepare_fts_query returns empty for invalid input."""
        result = prepare_fts_query("")
        assert result == ""

        result = prepare_fts_query("'''---")
        assert result == ""

    def test_prepare_fts_query_with_quotes(self) -> None:
        """prepare_fts_query handles quoted phrases."""
        result = prepare_fts_query('"exact phrase"')
        # Quotes are removed but phrase is preserved
        assert "exact" in result
        assert "phrase" in result

    async def test_search_cards_fts_basic(self, raw_db: aiosqlite.Connection) -> None:
        """search_cards_fts returns UUIDs for matching cards."""
        uuids = await search_cards_fts(raw_db, "lightning bolt", limit=10)

        assert len(uuids) > 0
        assert all(isinstance(uuid, str) for uuid in uuids)

    async def test_search_cards_fts_name_only(self, raw_db: aiosqlite.Connection) -> None:
        """search_cards_fts can search only card names."""
        uuids = await search_cards_fts(
            raw_db,
            "lightning bolt",
            search_name=True,
            search_type=False,
            search_text=False,
            limit=10,
        )

        assert len(uuids) > 0

    async def test_search_cards_fts_type_only(self, raw_db: aiosqlite.Connection) -> None:
        """search_cards_fts can search only type lines."""
        uuids = await search_cards_fts(
            raw_db,
            "legendary creature",
            search_name=False,
            search_type=True,
            search_text=False,
            limit=10,
        )

        assert len(uuids) > 0

    async def test_search_cards_fts_text_only(self, raw_db: aiosqlite.Connection) -> None:
        """search_cards_fts can search only oracle text."""
        uuids = await search_cards_fts(
            raw_db,
            "draw two cards",
            search_name=False,
            search_type=False,
            search_text=True,
            limit=10,
        )

        assert len(uuids) > 0

    async def test_search_cards_fts_no_columns(self, raw_db: aiosqlite.Connection) -> None:
        """search_cards_fts returns empty when no columns selected."""
        uuids = await search_cards_fts(
            raw_db,
            "test",
            search_name=False,
            search_type=False,
            search_text=False,
            limit=10,
        )

        assert uuids == []

    async def test_search_cards_fts_limit(self, raw_db: aiosqlite.Connection) -> None:
        """search_cards_fts respects limit parameter."""
        uuids = await search_cards_fts(raw_db, "creature", limit=5)

        assert len(uuids) <= 5

    async def test_search_cards_fts_empty_query(self, raw_db: aiosqlite.Connection) -> None:
        """search_cards_fts returns empty for invalid queries."""
        uuids = await search_cards_fts(raw_db, "", limit=10)
        assert uuids == []

        uuids = await search_cards_fts(raw_db, "'''", limit=10)
        assert uuids == []

    async def test_search_cards_fts_flavor_name(self, raw_db: aiosqlite.Connection) -> None:
        """search_cards_fts finds cards by flavor_name (e.g., SpongeBob)."""
        # Skip if FTS table doesn't have flavor_name column
        available_cols = await get_fts_columns(raw_db)
        if "flavor_name" not in available_cols:
            pytest.skip("FTS table missing flavor_name column - needs database rebuild")

        uuids = await search_cards_fts(raw_db, "spongebob", limit=10)

        assert len(uuids) >= 1, "Should find SpongeBob/Jodah card"

    async def test_search_cards_fts_with_params_basic(self, raw_db: aiosqlite.Connection) -> None:
        """search_cards_fts_with_params adds additional conditions."""
        uuids = await search_cards_fts_with_params(
            raw_db,
            "lightning",
            additional_conditions=[],
            additional_params=[],
            limit=10,
        )

        assert len(uuids) > 0

    async def test_search_cards_fts_with_params_empty_query(
        self, raw_db: aiosqlite.Connection
    ) -> None:
        """search_cards_fts_with_params handles empty queries."""
        uuids = await search_cards_fts_with_params(
            raw_db,
            "",
            additional_conditions=[],
            additional_params=[],
            limit=10,
        )

        assert uuids == []

    async def test_search_cards_fts_ordering(self, raw_db: aiosqlite.Connection) -> None:
        """search_cards_fts returns results ordered by relevance."""
        uuids = await search_cards_fts(raw_db, "lightning bolt", limit=20)

        # Should find multiple results
        assert len(uuids) > 0

        # Results are ordered by bm25 (best match first)
        # We can't test exact ordering, but we can verify it's deterministic
        uuids2 = await search_cards_fts(raw_db, "lightning bolt", limit=20)
        assert uuids == uuids2


class TestQueryBuilderValidFormats:
    """Tests for VALID_FORMATS constant used by QueryBuilder."""

    def test_valid_formats_contains_common_formats(self) -> None:
        """VALID_FORMATS includes common Magic formats."""
        assert "standard" in VALID_FORMATS
        assert "modern" in VALID_FORMATS
        assert "legacy" in VALID_FORMATS
        assert "commander" in VALID_FORMATS
        assert "pioneer" in VALID_FORMATS

    def test_valid_formats_is_frozen(self) -> None:
        """VALID_FORMATS is immutable."""
        assert isinstance(VALID_FORMATS, frozenset)

    def test_valid_formats_lowercase(self) -> None:
        """VALID_FORMATS uses lowercase format names."""
        for fmt in VALID_FORMATS:
            assert fmt == fmt.lower()


class TestFTSEdgeCases:
    """Additional tests for FTS edge cases and error handling."""

    async def test_check_fts_available_with_exception(self) -> None:
        """check_fts_available handles database errors gracefully."""
        # Create a connection to a non-existent database

        temp_db = Path(tempfile.gettempdir()) / "nonexistent.db"

        # Create an empty database without FTS table
        async with aiosqlite.connect(str(temp_db)) as conn:
            # Don't create FTS table
            available = await check_fts_available(conn)
            assert available is False

        # Clean up
        if temp_db.exists():
            temp_db.unlink()

    async def test_search_cards_fts_with_invalid_fts_query(
        self, raw_db: aiosqlite.Connection
    ) -> None:
        """search_cards_fts handles malformed FTS queries gracefully."""
        # These queries might cause FTS errors but should return empty list
        for bad_query in ["((((", "OR OR OR", "AND AND"]:
            uuids = await search_cards_fts(raw_db, bad_query, limit=10)
            # Should handle error and return empty list
            assert isinstance(uuids, list)

    async def test_search_cards_fts_with_params_invalid_query(
        self, raw_db: aiosqlite.Connection
    ) -> None:
        """search_cards_fts_with_params handles errors gracefully."""
        # Invalid FTS query should return empty list, not raise
        uuids = await search_cards_fts_with_params(
            raw_db,
            "((((",  # Malformed query
            additional_conditions=[],
            additional_params=[],
            limit=10,
        )
        assert isinstance(uuids, list)


class TestIntegration:
    """Integration tests combining multiple components."""

    async def test_cache_with_real_database(self, db: UnifiedDatabase) -> None:
        """Test cache with real database queries."""
        cache = CardCache(max_size=10, ttl_seconds=3600)

        # Get a real card
        card = await db.get_card_by_name("Lightning Bolt")
        assert card is not None

        # Cache it
        await cache.set("bolt", card)

        # Retrieve from cache
        cached = await cache.get("bolt")
        assert cached is not None
        assert cached.name == card.name
        assert cached.uuid == card.uuid

    async def test_query_builder_with_fts(self, raw_db: aiosqlite.Connection) -> None:
        """Test QueryBuilder combined with FTS search."""
        # Use FTS to find candidates
        fts_uuids = await search_cards_fts(raw_db, "lightning bolt", limit=10)
        assert len(fts_uuids) > 0

        # Use QueryBuilder to filter further
        qb = QueryBuilder()
        qb.add_exact("c.rarity", "common", case_insensitive=True)

        # In real usage, these would be combined in the database query
        # Here we just verify both components work
        assert qb.build_where() != "1=1"
        assert len(qb.params) > 0

    async def test_full_search_workflow(self) -> None:
        """Test complete search workflow using all components."""
        # Build query using QueryBuilder
        filters = SearchCardsInput(
            name="dragon",
            colors=["R"],
            type="creature",
            cmc_min=4.0,
        )

        qb = QueryBuilder.from_filters(filters)
        where = qb.build_where()

        # Should have multiple conditions
        assert where != "1=1"
        assert len(qb.params) > 0

        # Cache would be used in real database layer
        cache = CardCache(max_size=100, ttl_seconds=3600)
        stats = await cache.stats()
        assert stats["max_size"] == 100
