"""Pytest configuration and shared fixtures for mtg-core tests."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Configure pytest-asyncio to use asyncio backend."""
    return "asyncio"
