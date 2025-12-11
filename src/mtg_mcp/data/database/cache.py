"""Async-safe LRU cache for cards."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Card


@dataclass
class CardCache:
    """Simple async-safe LRU cache for cards using OrderedDict for O(1) operations."""

    _cache: OrderedDict[str, Card] = field(default_factory=OrderedDict)
    max_size: int = 1000
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get(self, key: str) -> Card | None:
        """Get a card from cache."""
        async with self._lock:
            if key in self._cache:
                # Move to end (most recently used) - O(1) operation
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    async def set(self, key: str, card: Card) -> None:
        """Add a card to cache."""
        async with self._lock:
            if key in self._cache:
                # Move existing key to end - O(1)
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.max_size:
                # Remove least recently used (first item) - O(1)
                self._cache.popitem(last=False)
            self._cache[key] = card

    async def clear(self) -> None:
        """Clear the cache."""
        async with self._lock:
            self._cache.clear()
