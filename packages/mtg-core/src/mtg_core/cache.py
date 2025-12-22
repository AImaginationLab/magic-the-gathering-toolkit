"""Generic compressed data cache for Pydantic models.

Provides disk-based caching with LZMA compression for any Pydantic model.
Includes LRU eviction, TTL support, and schema versioning.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import lzma
import threading
import time
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .config import get_settings

T = TypeVar("T", bound=BaseModel)

# Cache schema version - increment when model structures change
_CACHE_VERSION = 1

# Lock for thread-safe file operations (LZMAFile is not thread-safe)
_cache_lock = threading.Lock()


def _get_cache_dir() -> Path:
    """Get data cache directory from config."""
    return get_settings().data_cache_dir


def _get_max_cache_mb() -> int:
    """Get max cache size from config."""
    return get_settings().data_cache_max_mb


def _get_cache_key(namespace: str, key: str) -> str:
    """Generate a safe cache filename from namespace and key."""
    # Hash the key to avoid filesystem issues with special characters
    key_hash = hashlib.sha256(key.lower().encode()).hexdigest()[:12]
    return f"{namespace}_{key_hash}"


def _get_cache_path(namespace: str, key: str) -> Path:
    """Get full path to cached file."""
    return _get_cache_dir() / f"{_get_cache_key(namespace, key)}.json.xz"


def _get_metadata_path() -> Path:
    """Get path to cache metadata file."""
    return _get_cache_dir() / "data_cache_metadata.json"


def _load_metadata() -> dict[str, Any]:
    """Load cache metadata."""
    meta_path = _get_metadata_path()
    if meta_path.exists():
        try:
            data: dict[str, Any] = json.loads(meta_path.read_text())
            return data
        except Exception:
            pass
    return {"files": {}, "total_bytes": 0, "version": _CACHE_VERSION}


def _save_metadata(metadata: dict[str, Any]) -> None:
    """Save cache metadata."""
    try:
        cache_dir = _get_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        _get_metadata_path().write_text(json.dumps(metadata, indent=2))
    except Exception:
        pass


def _evict_lru(metadata: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    """Evict oldest entries until under size limit."""
    files = metadata.get("files", {})
    total = metadata.get("total_bytes", 0)
    cache_dir = _get_cache_dir()

    # Sort by last_access (oldest first)
    sorted_files = sorted(files.items(), key=lambda x: x[1].get("last_access", 0))

    for cache_key, info in sorted_files:
        if total <= max_bytes:
            break
        file_path = cache_dir / f"{cache_key}.json.xz"
        if file_path.exists():
            with contextlib.suppress(Exception):
                file_path.unlink()
        total -= info.get("size", 0)
        del files[cache_key]

    metadata["files"] = files
    metadata["total_bytes"] = max(0, total)
    return metadata


def get_cached(
    namespace: str,
    key: str,
    model_class: type[T],
    ttl_days: int = 7,
) -> T | None:
    """Retrieve cached data if valid.

    Args:
        namespace: Cache namespace (e.g., "printings", "synergies")
        key: Cache key (e.g., card name)
        model_class: Pydantic model class to deserialize into
        ttl_days: Time-to-live in days

    Returns:
        Cached model instance or None if not found/expired
    """
    cache_path = _get_cache_path(namespace, key)
    if not cache_path.exists():
        return None

    with _cache_lock:
        try:
            # Check metadata for TTL
            metadata = _load_metadata()
            cache_key = _get_cache_key(namespace, key)
            file_info = metadata.get("files", {}).get(cache_key)

            if not file_info:
                # No metadata entry - treat as cache miss and clean up orphaned file
                cache_path.unlink(missing_ok=True)
                return None

            # Check version
            if file_info.get("version") != _CACHE_VERSION:
                cache_path.unlink(missing_ok=True)
                # Clean up stale metadata entry
                metadata["total_bytes"] -= file_info.get("size", 0)
                del metadata["files"][cache_key]
                _save_metadata(metadata)
                return None

            # Check TTL
            created = file_info.get("created", 0)
            if time.time() - created > ttl_days * 86400:
                cache_path.unlink(missing_ok=True)
                # Clean up expired metadata entry
                metadata["total_bytes"] -= file_info.get("size", 0)
                del metadata["files"][cache_key]
                _save_metadata(metadata)
                return None

            # Decompress and deserialize (LZMAFile is not thread-safe)
            with lzma.open(cache_path, "rt", encoding="utf-8") as f:
                data = json.load(f)

            # Update access time
            if cache_key in metadata.get("files", {}):
                metadata["files"][cache_key]["last_access"] = time.time()
                _save_metadata(metadata)

            return model_class.model_validate(data)

        except Exception:
            # Corrupted cache, remove it
            cache_path.unlink(missing_ok=True)
            return None


def set_cached(
    namespace: str,
    key: str,
    data: BaseModel,
) -> None:
    """Cache data with compression.

    Args:
        namespace: Cache namespace
        key: Cache key
        data: Pydantic model to cache
    """
    # Serialize outside the lock (CPU-bound, doesn't need protection)
    json_str = data.model_dump_json()

    with _cache_lock:
        try:
            cache_dir = _get_cache_dir()
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = _get_cache_path(namespace, key)
            cache_key = _get_cache_key(namespace, key)

            # Compress and write (LZMAFile is not thread-safe)
            with lzma.open(cache_path, "wt", encoding="utf-8", preset=6) as f:
                f.write(json_str)

            # Update metadata
            file_size = cache_path.stat().st_size
            metadata = _load_metadata()

            # Remove old entry size if exists
            old_info = metadata.get("files", {}).get(cache_key)
            if old_info:
                metadata["total_bytes"] -= old_info.get("size", 0)

            metadata.setdefault("files", {})[cache_key] = {
                "namespace": namespace,
                "key": key,
                "size": file_size,
                "created": time.time(),
                "last_access": time.time(),
                "version": _CACHE_VERSION,
            }
            metadata["total_bytes"] = metadata.get("total_bytes", 0) + file_size

            # Evict if over limit
            max_bytes = _get_max_cache_mb() * 1024 * 1024
            if metadata["total_bytes"] > max_bytes:
                metadata = _evict_lru(metadata, max_bytes)

            _save_metadata(metadata)

        except Exception:
            pass  # Cache is best-effort


def invalidate_cached(namespace: str, key: str) -> None:
    """Invalidate a specific cache entry."""
    cache_path = _get_cache_path(namespace, key)
    cache_key = _get_cache_key(namespace, key)

    with _cache_lock:
        if cache_path.exists():
            with contextlib.suppress(Exception):
                cache_path.unlink()

        metadata = _load_metadata()
        if cache_key in metadata.get("files", {}):
            metadata["total_bytes"] -= metadata["files"][cache_key].get("size", 0)
            del metadata["files"][cache_key]
            _save_metadata(metadata)


def invalidate_namespace(namespace: str) -> None:
    """Invalidate all entries in a namespace."""
    with _cache_lock:
        metadata = _load_metadata()
        cache_dir = _get_cache_dir()
        files = metadata.get("files", {})

        to_remove = [k for k, v in files.items() if v.get("namespace") == namespace]
        for cache_key in to_remove:
            file_path = cache_dir / f"{cache_key}.json.xz"
            if file_path.exists():
                with contextlib.suppress(Exception):
                    file_path.unlink()
            metadata["total_bytes"] -= files[cache_key].get("size", 0)
            del files[cache_key]

        _save_metadata(metadata)


def clear_data_cache() -> None:
    """Clear all cached data."""
    with _cache_lock:
        cache_dir = _get_cache_dir()
        if cache_dir.exists():
            for f in cache_dir.glob("*.json.xz"):
                f.unlink(missing_ok=True)
            meta_path = _get_metadata_path()
            if meta_path.exists():
                meta_path.unlink(missing_ok=True)


def get_data_cache_stats() -> dict[str, Any]:
    """Get cache statistics."""
    metadata = _load_metadata()
    files = metadata.get("files", {})

    # Count by namespace
    namespaces: dict[str, int] = {}
    for info in files.values():
        ns = info.get("namespace", "unknown")
        namespaces[ns] = namespaces.get(ns, 0) + 1

    return {
        "total_files": len(files),
        "total_bytes": metadata.get("total_bytes", 0),
        "total_mb": round(metadata.get("total_bytes", 0) / 1024 / 1024, 2),
        "by_namespace": namespaces,
        "version": metadata.get("version", _CACHE_VERSION),
    }
