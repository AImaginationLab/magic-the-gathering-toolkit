"""Tests for set tools."""

from __future__ import annotations

import pytest

from mtg_mcp.data.database import MTGDatabase
from mtg_mcp.tools import sets


class TestGetSets:
    """Tests for get_sets tool."""

    async def test_get_all_sets(self, db: MTGDatabase) -> None:
        """Test getting all sets."""
        result = await sets.get_sets(db)

        assert result.count > 0
        assert len(result.sets) > 0

    async def test_get_sets_by_name(self, db: MTGDatabase) -> None:
        """Test filtering sets by name."""
        result = await sets.get_sets(db, name="Dominaria")

        assert result.count > 0
        for s in result.sets:
            assert "Dominaria" in s.name

    async def test_get_sets_by_type(self, db: MTGDatabase) -> None:
        """Test filtering sets by type."""
        result = await sets.get_sets(db, set_type="expansion")

        assert result.count > 0
        for s in result.sets:
            assert s.type == "expansion"

    async def test_get_sets_exclude_online_only(self, db: MTGDatabase) -> None:
        """Test excluding online-only sets."""
        all_sets = await sets.get_sets(db, include_online_only=True)
        paper_sets = await sets.get_sets(db, include_online_only=False)

        # Should have fewer sets when excluding online-only
        assert paper_sets.count <= all_sets.count


class TestGetSet:
    """Tests for get_set tool."""

    async def test_get_set_by_code(self, db: MTGDatabase) -> None:
        """Test getting a set by code."""
        result = await sets.get_set(db, "DOM")

        assert result.code.upper() == "DOM"
        assert "Dominaria" in result.name
        assert result.type is not None

    async def test_get_set_with_details(self, db: MTGDatabase) -> None:
        """Test that set details are populated."""
        result = await sets.get_set(db, "LEA")  # Alpha

        assert result.code.upper() == "LEA"
        assert result.release_date is not None
        assert result.total_set_size is not None
        assert result.total_set_size > 0

    async def test_get_set_not_found(self, db: MTGDatabase) -> None:
        """Test getting a nonexistent set."""
        from mtg_mcp.exceptions import SetNotFoundError

        with pytest.raises(SetNotFoundError):
            await sets.get_set(db, "XYZNOTASET")

    async def test_get_set_case_insensitive(self, db: MTGDatabase) -> None:
        """Test that set lookup is case-insensitive."""
        result_upper = await sets.get_set(db, "DOM")
        result_lower = await sets.get_set(db, "dom")

        assert result_upper.name == result_lower.name


class TestDatabaseStats:
    """Tests for database stats (via MTGDatabase directly)."""

    async def test_get_database_stats(self, db: MTGDatabase) -> None:
        """Test getting database statistics."""
        stats = await db.get_database_stats()

        assert "unique_cards" in stats
        assert "total_cards" in stats
        assert "total_sets" in stats
        assert stats["unique_cards"] > 0
        assert stats["total_sets"] > 0

    async def test_stats_have_version(self, db: MTGDatabase) -> None:
        """Test that stats include data version."""
        stats = await db.get_database_stats()

        # data_version may or may not be present depending on database
        # but if it is, it should be a string
        if "data_version" in stats and stats["data_version"]:
            assert isinstance(stats["data_version"], str)
