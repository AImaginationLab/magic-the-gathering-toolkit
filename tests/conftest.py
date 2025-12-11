"""Pytest fixtures for MTG MCP tests."""

from __future__ import annotations

import pytest

from mtg_mcp.config import get_settings
from mtg_mcp.data.database import DatabaseManager, MTGDatabase, ScryfallDatabase


@pytest.fixture
async def db_manager() -> DatabaseManager:
    """Create and start a database manager for testing."""
    settings = get_settings()
    manager = DatabaseManager(settings)
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
async def db(db_manager: DatabaseManager) -> MTGDatabase:
    """Get the MTG database instance."""
    return db_manager.db


@pytest.fixture
async def scryfall(db_manager: DatabaseManager) -> ScryfallDatabase | None:
    """Get the Scryfall database instance (may be None)."""
    return db_manager.scryfall
