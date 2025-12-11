"""Async-safe LRU cache for cards."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Card


@dataclass
class CardCache:
    """Simple async-safe LRU cache for cards."""

    _cache: dict[str, Card] = field(default_factory=dict)
    _access_order: list[str] = field(default_factory=list)
    max_size: int = 1000
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get(self, key: str) -> Card | None:
        """Get a card from cache."""
        async with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
            return None

    async def set(self, key: str, card: Card) -> None:
        """Add a card to cache."""
        async with self._lock:
            if key in self._cache:
                self._access_order.remove(key)
            elif len(self._cache) >= self.max_size:
                # Remove least recently used
                oldest = self._access_order.pop(0)
                del self._cache[oldest]
            self._cache[key] = card
            self._access_order.append(key)

    async def clear(self) -> None:
        """Clear the cache."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
