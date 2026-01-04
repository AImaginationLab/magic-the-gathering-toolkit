"""Pytest configuration and shared fixtures for mtg-core tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def get_test_db_path() -> Path | None:
    """Get path to test database if it exists."""
    env_path = os.environ.get("MTG_DB_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    candidate = Path.home() / ".mtg-spellbook" / "mtg.sqlite"
    if candidate.exists():
        return candidate.resolve()

    return None


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Configure pytest-asyncio to use asyncio backend."""
    return "asyncio"
