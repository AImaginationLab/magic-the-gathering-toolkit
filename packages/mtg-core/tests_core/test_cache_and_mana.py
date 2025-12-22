"""Comprehensive tests for cache.py and utils/mana.py modules.

Tests cover:
- cache.py: Caching, expiration, eviction, metadata management
- utils/mana.py: Mana cost parsing, color identity calculation, formatting
"""

# ruff: noqa: ARG002
from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel

from mtg_core import cache
from mtg_core.config import Settings
from mtg_core.utils import mana

if TYPE_CHECKING:
    from collections.abc import Generator


# Test Pydantic models for cache testing
class CardData(BaseModel):
    """Test model for cache testing."""

    name: str
    mana_cost: str
    colors: list[str]


class PrintingData(BaseModel):
    """Test model for cache testing."""

    set_code: str
    collector_number: str
    price_usd: float | None


# ============================================================================
# Cache Module Tests
# ============================================================================


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create temporary cache directory and configure settings."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True)

    # Store original settings
    original_settings = cache._settings if hasattr(cache, "_settings") else None

    # Configure test settings
    import mtg_core.config as config_module

    config_module._settings = Settings(
        data_cache_dir=cache_dir,
        data_cache_max_mb=1,  # 1MB for testing eviction
    )

    yield cache_dir

    # Restore original settings
    config_module._settings = original_settings


class TestCacheKeyGeneration:
    """Tests for cache key generation functions."""

    def test_get_cache_key_basic(self) -> None:
        """Test basic cache key generation."""
        key = cache._get_cache_key("cards", "Lightning Bolt")
        assert isinstance(key, str)
        assert key.startswith("cards_")
        assert len(key.split("_")[1]) == 12  # SHA256 hash truncated to 12 chars

    def test_get_cache_key_case_insensitive(self) -> None:
        """Test that cache keys are case-insensitive."""
        key1 = cache._get_cache_key("cards", "Lightning Bolt")
        key2 = cache._get_cache_key("cards", "LIGHTNING BOLT")
        key3 = cache._get_cache_key("cards", "lightning bolt")
        assert key1 == key2 == key3

    def test_get_cache_key_special_characters(self) -> None:
        """Test cache key generation with special characters."""
        key = cache._get_cache_key("cards", "Jace, the Mind Sculptor")
        assert isinstance(key, str)
        assert "/" not in key  # No filesystem-unsafe chars

    def test_get_cache_path_structure(self, temp_cache_dir: Path) -> None:
        """Test cache path structure."""
        path = cache._get_cache_path("printings", "Sol Ring")
        assert path.parent == temp_cache_dir
        assert path.suffix == ".xz"
        assert path.name.endswith(".json.xz")


class TestCacheMetadata:
    """Tests for cache metadata management."""

    def test_metadata_path(self, temp_cache_dir: Path) -> None:
        """Test metadata file path."""
        meta_path = cache._get_metadata_path()
        assert meta_path.parent == temp_cache_dir
        assert meta_path.name == "data_cache_metadata.json"

    def test_load_metadata_empty(self, temp_cache_dir: Path) -> None:
        """Test loading metadata when file doesn't exist."""
        metadata = cache._load_metadata()
        assert metadata["files"] == {}
        assert metadata["total_bytes"] == 0
        assert metadata["version"] == cache._CACHE_VERSION

    def test_save_and_load_metadata(self, temp_cache_dir: Path) -> None:
        """Test saving and loading metadata."""
        test_metadata = {
            "files": {
                "test_key": {
                    "namespace": "test",
                    "size": 1024,
                    "created": time.time(),
                }
            },
            "total_bytes": 1024,
            "version": cache._CACHE_VERSION,
        }
        cache._save_metadata(test_metadata)

        loaded = cache._load_metadata()
        assert loaded["total_bytes"] == 1024
        assert "test_key" in loaded["files"]

    def test_load_metadata_corrupted(self, temp_cache_dir: Path) -> None:
        """Test loading corrupted metadata returns default."""
        meta_path = cache._get_metadata_path()
        meta_path.write_text("invalid json {{{")

        metadata = cache._load_metadata()
        assert metadata["files"] == {}
        assert metadata["total_bytes"] == 0


class TestCacheSetAndGet:
    """Tests for basic cache set and get operations."""

    def test_set_and_get_cached(self, temp_cache_dir: Path) -> None:
        """Test basic cache set and get."""
        card = CardData(
            name="Lightning Bolt",
            mana_cost="{R}",
            colors=["R"],
        )

        cache.set_cached("cards", "lightning_bolt", card)
        retrieved = cache.get_cached("cards", "lightning_bolt", CardData)

        assert retrieved is not None
        assert retrieved.name == "Lightning Bolt"
        assert retrieved.mana_cost == "{R}"
        assert retrieved.colors == ["R"]

    def test_get_cached_nonexistent(self, temp_cache_dir: Path) -> None:
        """Test getting non-existent cache entry."""
        retrieved = cache.get_cached("cards", "nonexistent", CardData)
        assert retrieved is None

    def test_cache_compression(self, temp_cache_dir: Path) -> None:
        """Test that cache files are compressed."""
        card = CardData(
            name="A" * 1000,  # Large name for compression test
            mana_cost="{R}",
            colors=["R"],
        )

        cache.set_cached("cards", "test", card)
        cache_path = cache._get_cache_path("cards", "test")

        assert cache_path.exists()
        # Compressed size should be smaller than JSON string
        json_size = len(card.model_dump_json())
        compressed_size = cache_path.stat().st_size
        assert compressed_size < json_size

    def test_cache_metadata_updated(self, temp_cache_dir: Path) -> None:
        """Test that metadata is updated when caching."""
        card = CardData(name="Test", mana_cost="{1}", colors=[])

        cache.set_cached("test_ns", "test_key", card)

        metadata = cache._load_metadata()
        cache_key = cache._get_cache_key("test_ns", "test_key")

        assert cache_key in metadata["files"]
        assert metadata["files"][cache_key]["namespace"] == "test_ns"
        assert metadata["total_bytes"] > 0


class TestCacheTTL:
    """Tests for cache TTL (time-to-live) expiration."""

    def test_cache_ttl_valid(self, temp_cache_dir: Path) -> None:
        """Test that cache is valid within TTL."""
        card = CardData(name="Test", mana_cost="{1}", colors=[])

        cache.set_cached("cards", "test", card)
        retrieved = cache.get_cached("cards", "test", CardData, ttl_days=7)

        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_cache_ttl_expired(self, temp_cache_dir: Path) -> None:
        """Test that cache expires after TTL."""
        card = CardData(name="Test", mana_cost="{1}", colors=[])

        # Set cache entry
        cache.set_cached("cards", "test", card)

        # Manually modify metadata to simulate expiration
        metadata = cache._load_metadata()
        cache_key = cache._get_cache_key("cards", "test")
        metadata["files"][cache_key]["created"] = time.time() - (8 * 86400)  # 8 days ago
        cache._save_metadata(metadata)

        # Should return None due to expiration
        retrieved = cache.get_cached("cards", "test", CardData, ttl_days=7)
        assert retrieved is None

    def test_cache_ttl_cleans_up_expired(self, temp_cache_dir: Path) -> None:
        """Test that expired entries are cleaned up."""
        card = CardData(name="Test", mana_cost="{1}", colors=[])

        cache.set_cached("cards", "test", card)
        cache_path = cache._get_cache_path("cards", "test")
        assert cache_path.exists()

        # Expire the cache
        metadata = cache._load_metadata()
        cache_key = cache._get_cache_key("cards", "test")
        metadata["files"][cache_key]["created"] = time.time() - (8 * 86400)
        cache._save_metadata(metadata)

        # Access expired cache - should clean up
        cache.get_cached("cards", "test", CardData, ttl_days=7)

        # File and metadata should be removed
        assert not cache_path.exists()
        metadata = cache._load_metadata()
        assert cache_key not in metadata["files"]


class TestCacheVersioning:
    """Tests for cache version management."""

    def test_cache_version_mismatch(self, temp_cache_dir: Path) -> None:
        """Test that old cache version is invalidated."""
        card = CardData(name="Test", mana_cost="{1}", colors=[])

        cache.set_cached("cards", "test", card)

        # Manually set old version
        metadata = cache._load_metadata()
        cache_key = cache._get_cache_key("cards", "test")
        metadata["files"][cache_key]["version"] = cache._CACHE_VERSION - 1
        cache._save_metadata(metadata)

        # Should return None due to version mismatch
        retrieved = cache.get_cached("cards", "test", CardData)
        assert retrieved is None

    def test_cache_version_cleanup(self, temp_cache_dir: Path) -> None:
        """Test that old version entries are cleaned up."""
        card = CardData(name="Test", mana_cost="{1}", colors=[])

        cache.set_cached("cards", "test", card)

        # Set old version
        metadata = cache._load_metadata()
        cache_key = cache._get_cache_key("cards", "test")
        metadata["files"][cache_key]["version"] = cache._CACHE_VERSION - 1
        cache._save_metadata(metadata)

        # Access with version mismatch - should clean up
        cache.get_cached("cards", "test", CardData)

        # Metadata should be updated
        metadata = cache._load_metadata()
        assert cache_key not in metadata["files"]
        # Size should be subtracted
        assert metadata["total_bytes"] == 0


class TestCacheEviction:
    """Tests for LRU cache eviction."""

    def test_eviction_lru_order(self, temp_cache_dir: Path) -> None:
        """Test that oldest entries are evicted first."""
        metadata = {
            "files": {
                "old": {"namespace": "test", "size": 100, "last_access": 1000},
                "new": {"namespace": "test", "size": 100, "last_access": 2000},
            },
            "total_bytes": 200,
            "version": cache._CACHE_VERSION,
        }

        # Create dummy files
        (temp_cache_dir / "old.json.xz").touch()
        (temp_cache_dir / "new.json.xz").touch()

        # Evict to 150 bytes - should remove "old" only
        evicted = cache._evict_lru(metadata, max_bytes=150)

        assert "old" not in evicted["files"]
        assert "new" in evicted["files"]
        assert evicted["total_bytes"] == 100

    def test_eviction_multiple_entries(self, temp_cache_dir: Path) -> None:
        """Test evicting multiple entries."""
        metadata = {
            "files": {
                "a": {"namespace": "test", "size": 100, "last_access": 1000},
                "b": {"namespace": "test", "size": 100, "last_access": 2000},
                "c": {"namespace": "test", "size": 100, "last_access": 3000},
            },
            "total_bytes": 300,
            "version": cache._CACHE_VERSION,
        }

        # Create dummy files
        for name in ["a", "b", "c"]:
            (temp_cache_dir / f"{name}.json.xz").touch()

        # Evict to 150 bytes - should remove "a" and "b"
        evicted = cache._evict_lru(metadata, max_bytes=150)

        assert "a" not in evicted["files"]
        assert "b" not in evicted["files"]
        assert "c" in evicted["files"]
        assert evicted["total_bytes"] == 100

    def test_automatic_eviction_on_set(self, temp_cache_dir: Path) -> None:
        """Test that eviction happens automatically when limit exceeded."""
        # Create several cache entries to exceed 1MB limit
        for i in range(10):
            large_data = PrintingData(
                set_code=f"SET{i}",
                collector_number="1",
                price_usd=99.99,
            )
            cache.set_cached("printings", f"card_{i}", large_data)

        # Check that total size is under limit
        metadata = cache._load_metadata()
        max_bytes = cache._get_max_cache_mb() * 1024 * 1024
        assert metadata["total_bytes"] <= max_bytes


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_specific_entry(self, temp_cache_dir: Path) -> None:
        """Test invalidating a specific cache entry."""
        card = CardData(name="Test", mana_cost="{1}", colors=[])

        cache.set_cached("cards", "test", card)
        cache_path = cache._get_cache_path("cards", "test")
        assert cache_path.exists()

        cache.invalidate_cached("cards", "test")

        assert not cache_path.exists()
        retrieved = cache.get_cached("cards", "test", CardData)
        assert retrieved is None

    def test_invalidate_nonexistent(self, temp_cache_dir: Path) -> None:
        """Test invalidating non-existent entry doesn't error."""
        cache.invalidate_cached("cards", "nonexistent")  # Should not raise

    def test_invalidate_namespace(self, temp_cache_dir: Path) -> None:
        """Test invalidating all entries in a namespace."""
        # Create entries in different namespaces
        card1 = CardData(name="Test1", mana_cost="{1}", colors=[])
        card2 = CardData(name="Test2", mana_cost="{2}", colors=[])
        printing = PrintingData(set_code="TST", collector_number="1", price_usd=1.0)

        cache.set_cached("cards", "test1", card1)
        cache.set_cached("cards", "test2", card2)
        cache.set_cached("printings", "test3", printing)

        # Invalidate cards namespace
        cache.invalidate_namespace("cards")

        # Cards should be gone
        assert cache.get_cached("cards", "test1", CardData) is None
        assert cache.get_cached("cards", "test2", CardData) is None

        # Printing should remain
        assert cache.get_cached("printings", "test3", PrintingData) is not None

    def test_clear_all_cache(self, temp_cache_dir: Path) -> None:
        """Test clearing all cache entries."""
        card = CardData(name="Test", mana_cost="{1}", colors=[])
        cache.set_cached("cards", "test", card)

        cache.clear_data_cache()

        assert cache.get_cached("cards", "test", CardData) is None
        assert not list(temp_cache_dir.glob("*.json.xz"))
        assert not cache._get_metadata_path().exists()


class TestCacheAccessTracking:
    """Tests for cache access time tracking."""

    def test_access_time_updated(self, temp_cache_dir: Path) -> None:
        """Test that access time is updated on cache hit."""
        card = CardData(name="Test", mana_cost="{1}", colors=[])

        cache.set_cached("cards", "test", card)
        metadata = cache._load_metadata()
        cache_key = cache._get_cache_key("cards", "test")
        initial_access = metadata["files"][cache_key]["last_access"]

        # Wait a bit
        time.sleep(0.1)

        # Access cache
        cache.get_cached("cards", "test", CardData)

        # Check access time updated
        metadata = cache._load_metadata()
        new_access = metadata["files"][cache_key]["last_access"]
        assert new_access > initial_access


class TestCacheStats:
    """Tests for cache statistics."""

    def test_get_cache_stats_empty(self, temp_cache_dir: Path) -> None:
        """Test cache stats when empty."""
        stats = cache.get_data_cache_stats()

        assert stats["total_files"] == 0
        assert stats["total_bytes"] == 0
        assert stats["total_mb"] == 0
        assert stats["by_namespace"] == {}

    def test_get_cache_stats_populated(self, temp_cache_dir: Path) -> None:
        """Test cache stats with entries."""
        card = CardData(name="Test", mana_cost="{1}", colors=[])
        printing = PrintingData(set_code="TST", collector_number="1", price_usd=1.0)

        cache.set_cached("cards", "test1", card)
        cache.set_cached("cards", "test2", card)
        cache.set_cached("printings", "test3", printing)

        stats = cache.get_data_cache_stats()

        assert stats["total_files"] == 3
        assert stats["total_bytes"] > 0
        assert stats["total_mb"] >= 0  # Small files may round to 0.0
        assert stats["by_namespace"]["cards"] == 2
        assert stats["by_namespace"]["printings"] == 1


class TestCacheCorruption:
    """Tests for handling corrupted cache files."""

    def test_corrupted_file_returns_none(self, temp_cache_dir: Path) -> None:
        """Test that corrupted cache file returns None."""
        card = CardData(name="Test", mana_cost="{1}", colors=[])

        cache.set_cached("cards", "test", card)
        cache_path = cache._get_cache_path("cards", "test")

        # Corrupt the file
        cache_path.write_bytes(b"corrupted data")

        # Should return None and clean up
        retrieved = cache.get_cached("cards", "test", CardData)
        assert retrieved is None

    def test_orphaned_file_cleanup(self, temp_cache_dir: Path) -> None:
        """Test cleanup of orphaned cache files (no metadata)."""
        # Create a cache entry first
        card = CardData(name="Test", mana_cost="{1}", colors=[])
        cache.set_cached("test", "orphan", card)

        cache_path = cache._get_cache_path("test", "orphan")
        assert cache_path.exists()

        # Remove from metadata but leave file (simulate orphan)
        metadata = cache._load_metadata()
        cache_key = cache._get_cache_key("test", "orphan")
        del metadata["files"][cache_key]
        cache._save_metadata(metadata)

        # Try to get orphaned file - should return None and clean up
        retrieved = cache.get_cached("test", "orphan", CardData)
        assert retrieved is None
        assert not cache_path.exists()


# ============================================================================
# Mana Utility Module Tests
# ============================================================================


class TestParseManaCost:
    """Tests for parse_mana_cost function."""

    def test_parse_empty_cost(self) -> None:
        """Test parsing empty/None mana cost."""
        result = mana.parse_mana_cost(None)
        assert result.raw == ""
        assert result.cmc == 0
        assert result.colors == []
        assert result.generic == 0

    def test_parse_simple_generic(self) -> None:
        """Test parsing simple generic mana cost."""
        result = mana.parse_mana_cost("{3}")
        assert result.cmc == 3
        assert result.generic == 3
        assert result.colors == []
        assert result.colored == {}

    def test_parse_single_color(self) -> None:
        """Test parsing single colored mana."""
        result = mana.parse_mana_cost("{R}")
        assert result.cmc == 1
        assert result.generic == 0
        assert result.colors == ["R"]
        assert result.colored == {"R": 1}

    def test_parse_multiple_colors(self) -> None:
        """Test parsing multiple colored mana."""
        result = mana.parse_mana_cost("{2}{W}{U}")
        assert result.cmc == 4
        assert result.generic == 2
        assert result.colors == ["W", "U"]  # WUBRG order
        assert result.colored == {"W": 1, "U": 1}

    def test_parse_multiple_same_color(self) -> None:
        """Test parsing multiple of same color."""
        result = mana.parse_mana_cost("{W}{W}{W}")
        assert result.cmc == 3
        assert result.colors == ["W"]
        assert result.colored == {"W": 3}

    def test_parse_wubrg_order(self) -> None:
        """Test that colors are sorted in WUBRG order."""
        result = mana.parse_mana_cost("{G}{R}{B}{U}{W}")
        assert result.colors == ["W", "U", "B", "R", "G"]

    def test_parse_x_cost(self) -> None:
        """Test parsing X mana cost."""
        result = mana.parse_mana_cost("{X}{R}{R}")
        assert result.cmc == 2  # X doesn't count toward CMC
        assert result.x_count == 1
        assert result.colors == ["R"]

    def test_parse_multiple_x(self) -> None:
        """Test parsing multiple X."""
        result = mana.parse_mana_cost("{X}{X}{U}")
        assert result.cmc == 1
        assert result.x_count == 2

    def test_parse_colorless_c(self) -> None:
        """Test parsing colorless mana symbol."""
        result = mana.parse_mana_cost("{C}{C}")
        assert result.cmc == 2
        assert result.colors == []  # Colorless has no color

    def test_parse_hybrid_mana(self) -> None:
        """Test parsing hybrid mana."""
        result = mana.parse_mana_cost("{W/U}")
        assert result.cmc == 1
        assert result.colors == ["W", "U"]
        assert result.hybrid == ["W/U"]
        assert result.color_identity == ["W", "U"]

    def test_parse_hybrid_generic(self) -> None:
        """Test parsing hybrid generic/color mana."""
        result = mana.parse_mana_cost("{2/W}")
        assert result.cmc == 2
        assert result.hybrid == ["2/W"]
        assert result.color_identity == ["W"]

    def test_parse_phyrexian_mana(self) -> None:
        """Test parsing phyrexian mana."""
        result = mana.parse_mana_cost("{W/P}{U/P}")
        assert result.cmc == 2
        assert result.colors == ["W", "U"]
        assert result.phyrexian == ["W/P", "U/P"]

    def test_parse_complex_cost(self) -> None:
        """Test parsing complex mana cost."""
        result = mana.parse_mana_cost("{3}{U}{U}{B}")
        assert result.raw == "{3}{U}{U}{B}"
        assert result.cmc == 6
        assert result.generic == 3
        assert result.colors == ["U", "B"]
        assert result.colored == {"U": 2, "B": 1}

    def test_parse_case_insensitive(self) -> None:
        """Test that parsing is case-insensitive."""
        result1 = mana.parse_mana_cost("{w}{u}{b}{r}{g}")
        result2 = mana.parse_mana_cost("{W}{U}{B}{R}{G}")
        assert result1.colors == result2.colors


class TestCalculateColorIdentity:
    """Tests for calculate_color_identity function."""

    def test_color_identity_from_mana_cost(self) -> None:
        """Test color identity from mana cost only."""
        identity = mana.calculate_color_identity("{2}{W}{U}", None)
        assert identity == ["W", "U"]

    def test_color_identity_from_text(self) -> None:
        """Test color identity from card text."""
        identity = mana.calculate_color_identity(
            "{2}",
            "Add {R}{G} to your mana pool.",
        )
        assert identity == ["R", "G"]

    def test_color_identity_combined(self) -> None:
        """Test color identity from cost and text."""
        identity = mana.calculate_color_identity(
            "{W}{W}",
            "Add {U} to your mana pool.",
        )
        assert identity == ["W", "U"]

    def test_color_identity_hybrid_in_text(self) -> None:
        """Test color identity with hybrid symbols in text."""
        identity = mana.calculate_color_identity(
            "{2}",
            "Pay {W/U}: Draw a card.",
        )
        assert identity == ["W", "U"]

    def test_color_identity_from_indicator(self) -> None:
        """Test color identity from color indicator."""
        identity = mana.calculate_color_identity(None, None, ["Blue", "Black"])
        assert identity == ["U", "B"]

    def test_color_identity_indicator_abbreviations(self) -> None:
        """Test color indicator with abbreviations."""
        identity = mana.calculate_color_identity(None, None, ["W", "U"])
        assert identity == ["W", "U"]

    def test_color_identity_all_sources(self) -> None:
        """Test color identity from all sources combined."""
        identity = mana.calculate_color_identity(
            "{W}",
            "Add {U} to your mana pool.",
            ["Black"],
        )
        assert identity == ["W", "U", "B"]

    def test_color_identity_empty(self) -> None:
        """Test colorless color identity."""
        identity = mana.calculate_color_identity(None, None)
        assert identity == []

    def test_color_identity_wubrg_order(self) -> None:
        """Test that color identity is in WUBRG order."""
        identity = mana.calculate_color_identity(
            "{G}{R}",
            "Add {B}{U}{W}.",
        )
        assert identity == ["W", "U", "B", "R", "G"]


class TestFormatManaCost:
    """Tests for format_mana_cost function."""

    def test_format_empty(self) -> None:
        """Test formatting empty mana cost."""
        result = mana.format_mana_cost(None)
        assert result == ""

    def test_format_simple_cost(self) -> None:
        """Test formatting simple mana cost."""
        result = mana.format_mana_cost("{2}{W}{W}")
        assert result == "2WW"

    def test_format_complex_cost(self) -> None:
        """Test formatting complex mana cost."""
        result = mana.format_mana_cost("{3}{U}{U}{B}")
        assert result == "3UUB"

    def test_format_hybrid(self) -> None:
        """Test formatting hybrid mana."""
        result = mana.format_mana_cost("{W/U}{W/U}")
        assert result == "W/UW/U"

    def test_format_x_cost(self) -> None:
        """Test formatting X cost."""
        result = mana.format_mana_cost("{X}{R}{R}")
        assert result == "XRR"


class TestManaEmoji:
    """Tests for mana_cost_to_emoji function."""

    def test_emoji_basic_colors(self) -> None:
        """Test emoji conversion for basic colors."""
        result = mana.mana_cost_to_emoji("{W}{U}{B}{R}{G}")
        assert "⚪" in result  # White
        assert "🔵" in result  # Blue
        assert "⚫" in result  # Black
        assert "🔴" in result  # Red
        assert "🟢" in result  # Green

    def test_emoji_generic(self) -> None:
        """Test emoji conversion for generic mana."""
        result = mana.mana_cost_to_emoji("{3}")
        assert result == "(3)"

    def test_emoji_x_cost(self) -> None:
        """Test emoji conversion for X."""
        result = mana.mana_cost_to_emoji("{X}")
        assert result == "(X)"

    def test_emoji_colorless(self) -> None:
        """Test emoji conversion for colorless."""
        result = mana.mana_cost_to_emoji("{C}")
        assert "◇" in result

    def test_emoji_complex(self) -> None:
        """Test emoji conversion for complex cost."""
        result = mana.mana_cost_to_emoji("{2}{W}{U}")
        assert "(2)" in result
        assert "⚪" in result
        assert "🔵" in result

    def test_emoji_empty(self) -> None:
        """Test emoji conversion for empty cost."""
        result = mana.mana_cost_to_emoji(None)
        assert result == ""


class TestManaConstants:
    """Tests for mana module constants."""

    def test_colors_mapping(self) -> None:
        """Test COLORS constant mapping."""
        assert mana.COLORS["W"] == "White"
        assert mana.COLORS["U"] == "Blue"
        assert mana.COLORS["B"] == "Black"
        assert mana.COLORS["R"] == "Red"
        assert mana.COLORS["G"] == "Green"

    def test_color_order(self) -> None:
        """Test COLOR_ORDER constant."""
        assert mana.COLOR_ORDER == ["W", "U", "B", "R", "G"]

    def test_mana_symbol_pattern(self) -> None:
        """Test MANA_SYMBOL_PATTERN regex."""
        matches = mana.MANA_SYMBOL_PATTERN.findall("{2}{W}{U}")
        assert matches == ["2", "W", "U"]


class TestManaCostNamedTuple:
    """Tests for ManaCost named tuple structure."""

    def test_mana_cost_attributes(self) -> None:
        """Test ManaCost has all expected attributes."""
        result = mana.parse_mana_cost("{2}{W}{U}")
        assert hasattr(result, "raw")
        assert hasattr(result, "cmc")
        assert hasattr(result, "colors")
        assert hasattr(result, "color_identity")
        assert hasattr(result, "generic")
        assert hasattr(result, "colored")
        assert hasattr(result, "hybrid")
        assert hasattr(result, "phyrexian")
        assert hasattr(result, "x_count")

    def test_mana_cost_immutable(self) -> None:
        """Test ManaCost is immutable (NamedTuple)."""
        result = mana.parse_mana_cost("{2}{W}")
        with pytest.raises(AttributeError):
            result.cmc = 5


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_parse_unknown_symbols(self) -> None:
        """Test parsing with unknown symbols (ignored)."""
        result = mana.parse_mana_cost("{Z}{UNKNOWN}")
        # Unknown symbols should be ignored
        assert result.cmc == 0

    def test_parse_empty_braces(self) -> None:
        """Test parsing empty braces."""
        result = mana.parse_mana_cost("{}")
        assert result.cmc == 0

    def test_format_no_braces(self) -> None:
        """Test formatting string without braces."""
        result = mana.format_mana_cost("invalid")
        assert result == ""

    def test_cache_thread_safety(self, temp_cache_dir: Path) -> None:
        """Test that cache lock exists for thread safety."""
        assert hasattr(cache, "_cache_lock")
        assert isinstance(cache._cache_lock, type(cache._cache_lock))
