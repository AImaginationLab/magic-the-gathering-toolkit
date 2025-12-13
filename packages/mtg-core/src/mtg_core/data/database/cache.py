"""Async-safe LRU cache with TTL support for cards."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Card


@dataclass
class CacheEntry:
    """Cache entry with timestamp for TTL tracking."""

    card: Card
    timestamp: float


@dataclass
class CardCache:
    """Async-safe LRU cache with TTL expiration for cards.

    Uses OrderedDict for O(1) LRU operations and tracks entry timestamps
    for TTL-based expiration.
    """

    _cache: OrderedDict[str, CacheEntry] = field(default_factory=OrderedDict)
    max_size: int = 1000
    ttl_seconds: int = 3600
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get(self, key: str) -> Card | None:
        """Get a card from cache, returning None if expired or missing."""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Check TTL expiration
            if self._is_expired(entry):
                del self._cache[key]
                return None

            # Move to end (most recently used) - O(1)
            self._cache.move_to_end(key)
            return entry.card

    async def set(self, key: str, card: Card) -> None:
        """Add a card to cache with current timestamp."""
        async with self._lock:
            now = time.monotonic()

            if key in self._cache:
                # Update existing entry
                self._cache[key] = CacheEntry(card=card, timestamp=now)
                self._cache.move_to_end(key)
            else:
                # Evict expired entries first (lazy cleanup)
                self._evict_expired()

                # Evict LRU if at capacity
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)

                self._cache[key] = CacheEntry(card=card, timestamp=now)

    async def clear(self) -> None:
        """Clear the cache."""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        async with self._lock:
            return self._evict_expired()

    async def stats(self) -> dict[str, int]:
        """Get cache statistics."""
        async with self._lock:
            now = time.monotonic()
            expired_count = sum(1 for entry in self._cache.values() if self._is_expired(entry, now))
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "expired_pending": expired_count,
            }

    def _is_expired(self, entry: CacheEntry, now: float | None = None) -> bool:
        """Check if a cache entry has expired."""
        if now is None:
            now = time.monotonic()
        return (now - entry.timestamp) > self.ttl_seconds

    def _evict_expired(self) -> int:
        """Remove expired entries. Must be called with lock held."""
        now = time.monotonic()
        expired_keys = [key for key, entry in self._cache.items() if self._is_expired(entry, now)]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)
