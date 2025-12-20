"""Shared image loading utilities for art navigator."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import threading
import time
from collections import OrderedDict
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, UnidentifiedImageError

from mtg_core.config import get_settings

# Memory cache: fast LRU for recently accessed images
_memory_cache: OrderedDict[str, Image.Image] = OrderedDict()
_memory_cache_lock = asyncio.Lock()

# Disk cache lock: protects metadata read/write operations across threads
_disk_cache_lock = threading.Lock()

# Shared httpx client for connection pooling (reused across all image loads)
_http_client: httpx.AsyncClient | None = None
_http_client_lock = asyncio.Lock()


async def _get_http_client() -> httpx.AsyncClient:
    """Get or create the shared HTTP client with connection pooling."""
    global _http_client
    if _http_client is None:
        async with _http_client_lock:
            # Double-check after acquiring lock
            if _http_client is None:
                _http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0, connect=10.0),
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                )
    return _http_client


async def close_http_client() -> None:
    """Close the shared HTTP client (call on app shutdown)."""
    global _http_client
    try:
        async with _http_client_lock:
            if _http_client is not None:
                await _http_client.aclose()
                _http_client = None
    except RuntimeError:
        # Event loop already closed during test teardown - safe to ignore
        _http_client = None


def _get_cache_dir() -> Path:
    """Get cache directory from config."""
    return get_settings().image_cache_dir


def _get_metadata_file() -> Path:
    """Get metadata file path."""
    return _get_cache_dir() / "cache_metadata.json"


def _get_cache_settings() -> tuple[int, int]:
    """Get cache settings from config."""
    settings = get_settings()
    return settings.image_cache_max_mb, settings.image_memory_cache_count


def _get_cache_path(url: str, extension: str = ".webp") -> Path:
    """Get disk cache path for a URL."""
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    return _get_cache_dir() / f"{url_hash}{extension}"


def _load_metadata() -> dict[str, Any]:
    """Load cache metadata from disk."""
    metadata_file = _get_metadata_file()
    if metadata_file.exists():
        try:
            data: dict[str, Any] = json.loads(metadata_file.read_text())
            return data
        except (json.JSONDecodeError, OSError):
            pass  # Corrupted or inaccessible metadata, use defaults
    return {"files": {}, "total_bytes": 0}


def _save_metadata(metadata: dict[str, Any]) -> None:
    """Save cache metadata to disk."""
    try:
        cache_dir = _get_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        _get_metadata_file().write_text(json.dumps(metadata, indent=2))
    except OSError:
        pass  # Disk cache is best-effort


def _evict_lru_files(metadata: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    """Evict oldest files until under the size limit."""
    files = metadata.get("files", {})
    total = metadata.get("total_bytes", 0)
    cache_dir = _get_cache_dir()

    # Sort by last_access time (oldest first)
    sorted_files = sorted(files.items(), key=lambda x: x[1].get("last_access", 0))

    for url_hash, info in sorted_files:
        if total <= max_bytes:
            break
        # Remove the file (try both extensions for backwards compatibility)
        for ext in (".webp", ".png"):
            file_path = cache_dir / f"{url_hash}{ext}"
            if file_path.exists():
                with contextlib.suppress(OSError):
                    file_path.unlink()
                break
        total -= info.get("size", 0)
        del files[url_hash]

    metadata["files"] = files
    metadata["total_bytes"] = max(0, total)
    return metadata


def _load_from_disk(url: str) -> Image.Image | None:
    """Load image from disk cache and update access time."""
    with _disk_cache_lock:
        # Try WebP first (new format), then PNG (legacy)
        for ext in (".webp", ".png"):
            cache_path = _get_cache_path(url, ext)
            if cache_path.exists():
                try:
                    img = Image.open(cache_path)
                    # Update access time in metadata
                    url_hash = cache_path.stem
                    metadata = _load_metadata()
                    if url_hash in metadata.get("files", {}):
                        metadata["files"][url_hash]["last_access"] = time.time()
                        _save_metadata(metadata)
                    return img
                except (OSError, UnidentifiedImageError):
                    cache_path.unlink(missing_ok=True)  # Corrupted cache file
        return None


def _save_to_disk(url: str, img: Image.Image) -> None:
    """Save image to disk cache with LRU management.

    Uses WebP format at quality 95 for ~79% size reduction vs PNG
    with near-lossless quality.
    """
    with _disk_cache_lock:
        try:
            cache_dir = _get_cache_dir()
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = _get_cache_path(url, ".webp")
            img.save(cache_path, "WEBP", quality=95)

            # Update metadata
            file_size = cache_path.stat().st_size
            url_hash = cache_path.stem
            metadata = _load_metadata()

            # Add new file entry
            metadata["files"][url_hash] = {
                "url": url,
                "size": file_size,
                "last_access": time.time(),
            }
            metadata["total_bytes"] = metadata.get("total_bytes", 0) + file_size

            # Check if we need to evict
            max_mb, _ = _get_cache_settings()
            max_bytes = max_mb * 1024 * 1024
            if metadata["total_bytes"] > max_bytes:
                metadata = _evict_lru_files(metadata, max_bytes)

            _save_metadata(metadata)
        except OSError:
            pass  # Disk cache is best-effort


async def _add_to_memory_cache(url: str, img: Image.Image) -> None:
    """Add to memory cache with LRU eviction (thread-safe)."""
    _, max_count = _get_cache_settings()

    async with _memory_cache_lock:
        if url in _memory_cache:
            _memory_cache.move_to_end(url)
        else:
            while len(_memory_cache) >= max_count:
                _memory_cache.popitem(last=False)
            _memory_cache[url] = img


def _clear_disk_cache() -> None:
    """Clear disk cache files and metadata (called from thread)."""
    with _disk_cache_lock:
        cache_dir = _get_cache_dir()
        metadata_file = _get_metadata_file()
        if cache_dir.exists():
            # Clear both WebP (new) and PNG (legacy) files
            for pattern in ("*.webp", "*.png"):
                for f in cache_dir.glob(pattern):
                    f.unlink(missing_ok=True)
            if metadata_file.exists():
                metadata_file.unlink(missing_ok=True)


async def clear_image_cache() -> None:
    """Clear all cached images (call when data is refreshed)."""
    async with _memory_cache_lock:
        _memory_cache.clear()
    # Run disk operations in thread with lock protection
    await asyncio.to_thread(_clear_disk_cache)


def get_cache_stats() -> dict[str, Any]:
    """Get cache statistics for debugging/display."""
    metadata = _load_metadata()
    max_mb, max_memory = _get_cache_settings()
    return {
        "disk_files": len(metadata.get("files", {})),
        "disk_bytes": metadata.get("total_bytes", 0),
        "disk_mb": round(metadata.get("total_bytes", 0) / 1024 / 1024, 2),
        "disk_limit_mb": max_mb,
        "memory_count": len(_memory_cache),
        "memory_limit": max_memory,
    }


async def load_image_from_url(
    url: str,
    target_widget: Any,
    *,
    use_large: bool = True,
    timeout: float = 15.0,
    max_width: int = 672,
    max_height: int = 936,
) -> bool:
    """Load image from URL into a Textual Image widget.

    Pre-processes the image with high-quality LANCZOS resampling to prevent
    banding artifacts that occur when textual_image uses NEAREST neighbor
    interpolation internally.

    Args:
        url: The image URL to fetch.
        target_widget: The Textual Image widget to update.
        use_large: If True, replace "normal" with "large" in URL.
        timeout: Request timeout in seconds.
        max_width: Maximum width for pre-processing (default: Scryfall large card width).
        max_height: Maximum height for pre-processing (default: Scryfall large card height).

    Returns:
        True if successful, False otherwise.
    """
    try:
        # Show loading state if widget supports it
        if hasattr(target_widget, "loading"):
            target_widget.loading = True

        if use_large and "normal" in url:
            url = url.replace("normal", "large")

        # Check memory cache first (fastest, thread-safe)
        async with _memory_cache_lock:
            if url in _memory_cache:
                _memory_cache.move_to_end(url)  # LRU update
                target_widget.image = _memory_cache[url]
                if hasattr(target_widget, "loading"):
                    target_widget.loading = False
                return True

        # Check disk cache (persistent across sessions) - run in thread to avoid blocking
        disk_image = await asyncio.to_thread(_load_from_disk, url)
        if disk_image is not None:
            await _add_to_memory_cache(url, disk_image)  # Promote to memory
            target_widget.image = disk_image
            if hasattr(target_widget, "loading"):
                target_widget.loading = False
            return True

        # Fetch from network using shared client
        client = await _get_http_client()
        response = await client.get(url, timeout=timeout)
        response.raise_for_status()
        image_data = response.content

        pil_image: Image.Image = Image.open(BytesIO(image_data))

        # Convert to RGB for consistent color handling
        if pil_image.mode not in ("RGB", "L"):
            pil_image = pil_image.convert("RGB")

        # Pre-resize with LANCZOS for high-quality downscaling
        # This prevents banding artifacts from textual_image's NEAREST neighbor resize
        pil_image = _prepare_image_for_display(pil_image, max_width, max_height)

        # Cache in memory (LRU) and on disk (persistent)
        await _add_to_memory_cache(url, pil_image)
        # Run disk save in thread to avoid blocking event loop during WebP encoding
        await asyncio.to_thread(_save_to_disk, url, pil_image)

        target_widget.image = pil_image

        if hasattr(target_widget, "loading"):
            target_widget.loading = False

        return True

    except (httpx.HTTPError, UnidentifiedImageError, OSError):
        if hasattr(target_widget, "loading"):
            target_widget.loading = False
        return False


def _prepare_image_for_display(
    img: Image.Image,
    max_width: int,
    max_height: int,
) -> Image.Image:
    """Prepare image for terminal display with high-quality resampling.

    Resizes the image while maintaining aspect ratio using LANCZOS resampling,
    which produces much better results than the NEAREST neighbor algorithm
    used internally by textual_image.

    Args:
        img: PIL Image to prepare.
        max_width: Maximum width constraint.
        max_height: Maximum height constraint.

    Returns:
        Processed PIL Image ready for display.
    """
    original_width, original_height = img.size

    # Calculate scale to fit within bounds while preserving aspect ratio
    width_ratio = max_width / original_width
    height_ratio = max_height / original_height
    scale = min(width_ratio, height_ratio, 1.0)  # Never upscale

    if scale < 1.0:
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    return img
