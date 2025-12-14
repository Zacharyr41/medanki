"""Tests for the cache service."""

from __future__ import annotations

import asyncio
import hashlib
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


class TestMemoryCache:
    """Tests for MemoryCache implementation."""

    @pytest.mark.asyncio
    async def test_memory_cache_set_get(self) -> None:
        """Set value, get returns it."""
        from medanki.services.cache import MemoryCache

        cache = MemoryCache()
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_memory_cache_miss_returns_none(self) -> None:
        """Missing key returns None."""
        from medanki.services.cache import MemoryCache

        cache = MemoryCache()
        result = await cache.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_memory_cache_ttl_expires(self) -> None:
        """Expired items return None."""
        from medanki.services.cache import MemoryCache

        cache = MemoryCache(default_ttl=0.1)
        await cache.set("key1", "value1")
        result_before = await cache.get("key1")
        assert result_before == "value1"

        await asyncio.sleep(0.15)
        result_after = await cache.get("key1")
        assert result_after is None


class TestDiskCache:
    """Tests for DiskCache implementation."""

    @pytest.mark.asyncio
    async def test_disk_cache_persists(self) -> None:
        """Write to disk, read back works."""
        from medanki.services.cache import DiskCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            cache1 = DiskCache(cache_dir=cache_dir)
            await cache1.set("persistent_key", {"data": "test_value", "number": 42})

            cache2 = DiskCache(cache_dir=cache_dir)
            result = await cache2.get("persistent_key")
            assert result == {"data": "test_value", "number": 42}


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_cache_key_generation(self) -> None:
        """Deterministic keys from content."""
        from medanki.services.cache import generate_cache_key

        content1 = "some test content"
        content2 = "some test content"
        content3 = "different content"

        key1 = generate_cache_key(content1)
        key2 = generate_cache_key(content2)
        key3 = generate_cache_key(content3)

        assert key1 == key2
        assert key1 != key3

        expected_key = hashlib.sha256(content1.encode()).hexdigest()[:16]
        assert key1 == expected_key


class TestCacheClear:
    """Tests for cache clearing functionality."""

    @pytest.mark.asyncio
    async def test_cache_clear(self) -> None:
        """Clearing cache via delete removes entries."""
        from medanki.services.cache import MemoryCache

        cache = MemoryCache()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        result1_before = await cache.get("key1")
        assert result1_before == "value1"

        await cache.delete("key1")
        await cache.delete("key2")
        await cache.delete("key3")

        result1_after = await cache.get("key1")
        result2_after = await cache.get("key2")
        result3_after = await cache.get("key3")

        assert result1_after is None
        assert result2_after is None
        assert result3_after is None
