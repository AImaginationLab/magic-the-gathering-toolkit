"""Pytest fixtures for MTG MCP tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from mtg_core.config import get_settings
from mtg_core.data.database import DatabaseManager, UnifiedDatabase


@pytest.fixture
async def db_manager() -> AsyncGenerator[DatabaseManager, None]:
    """Create and start a database manager for testing."""
    settings = get_settings()
    manager = DatabaseManager(settings)
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
async def db(db_manager: DatabaseManager) -> UnifiedDatabase:
    """Get the unified MTG database instance."""
    return db_manager.db
