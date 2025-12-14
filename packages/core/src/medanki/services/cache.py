"""Cache service with memory and disk implementations."""

from __future__ import annotations

import hashlib
import pickle
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import aiofiles


@runtime_checkable
class CacheProtocol(Protocol):
    """Protocol for cache implementations."""

    async def get(self, key: str) -> Any | None:
        """Get a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value or None if not found/expired.
        """
        ...

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Time-to-live in seconds (optional).
        """
        ...

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: The cache key.

        Returns:
            True if the key was deleted, False if not found.
        """
        ...


@dataclass
class CacheEntry:
    """A cache entry with value and expiration."""

    value: Any
    expires_at: float | None


class MemoryCache:
    """In-memory cache with TTL support.

    Args:
        default_ttl: Default time-to-live in seconds. None means no expiration.
    """

    def __init__(self, default_ttl: float | None = None) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        """Get a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value or None if not found/expired.
        """
        entry = self._cache.get(key)
        if entry is None:
            return None

        if entry.expires_at is not None and time.monotonic() > entry.expires_at:
            del self._cache[key]
            return None

        return entry.value

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Time-to-live in seconds. Uses default_ttl if not provided.
        """
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.monotonic() + effective_ttl if effective_ttl is not None else None
        self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: The cache key.

        Returns:
            True if the key was deleted, False if not found.
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False


class DiskCache:
    """Disk-based cache using pickle serialization.

    Args:
        cache_dir: Directory to store cache files.
        default_ttl: Default time-to-live in seconds. None means no expiration.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        default_ttl: float | None = None,
    ) -> None:
        self._cache_dir = cache_dir or Path.home() / ".medanki" / "cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._default_ttl = default_ttl

    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        safe_key = hashlib.sha256(key.encode()).hexdigest()
        return self._cache_dir / f"{safe_key}.cache"

    async def get(self, key: str) -> Any | None:
        """Get a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value or None if not found/expired.
        """
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            async with aiofiles.open(cache_path, "rb") as f:
                data = await f.read()
            entry: CacheEntry = pickle.loads(data)

            if entry.expires_at is not None and time.time() > entry.expires_at:
                cache_path.unlink(missing_ok=True)
                return None

            return entry.value
        except (pickle.PickleError, OSError):
            return None

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Time-to-live in seconds. Uses default_ttl if not provided.
        """
        cache_path = self._get_cache_path(key)
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl is not None else None
        entry = CacheEntry(value=value, expires_at=expires_at)

        data = pickle.dumps(entry)
        async with aiofiles.open(cache_path, "wb") as f:
            await f.write(data)

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: The cache key.

        Returns:
            True if the key was deleted, False if not found.
        """
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
            return True
        return False


def generate_cache_key(content: str) -> str:
    """Generate a deterministic cache key from content.

    Args:
        content: The content to hash.

    Returns:
        A 16-character hex string cache key.
    """
    return hashlib.sha256(content.encode()).hexdigest()[:16]
