"""
Tests for Core Cache Service

Run with: pytest apps/core/services/cache/tests/ -v
"""

import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from ..backends import FileCacheBackend, MemoryCacheBackend, create_backend
from ..base import cached
from ..exceptions import (
    CacheBackendNotAvailableError,
    CacheException,
    CacheKeyNotFoundError,
    CacheSerializationError,
)

# Import test subjects
from ..models import CacheBackend, CacheConfig, CacheEntry, CacheStats, generate_cache_key

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def memory_cache():
    """Create a memory cache for testing."""
    return MemoryCacheBackend(
        CacheConfig(
            default_ttl=60,
            key_prefix="test",
            enable_stats=True,
        )
    )


@pytest.fixture
def file_cache(tmp_path):
    """Create a file cache for testing."""
    return FileCacheBackend(
        CacheConfig(
            default_ttl=60,
            key_prefix="test",
            cache_dir=str(tmp_path),
            cache_file="test_cache.json",
            enable_stats=True,
        )
    )


# =============================================================================
# Model Tests
# =============================================================================


class TestCacheConfig:
    def test_default_values(self):
        config = CacheConfig()
        assert config.backend == CacheBackend.DJANGO
        assert config.default_ttl == 300
        assert config.key_prefix == "core"
        assert config.enable_stats is True

    def test_custom_values(self):
        config = CacheConfig(
            backend=CacheBackend.REDIS,
            default_ttl=600,
            key_prefix="myapp",
        )
        assert config.backend == CacheBackend.REDIS
        assert config.default_ttl == 600
        assert config.key_prefix == "myapp"


class TestCacheEntry:
    def test_entry_creation(self):
        entry = CacheEntry(key="test", value="data")
        assert entry.key == "test"
        assert entry.value == "data"
        assert entry.hits == 0
        assert entry.is_expired is False

    def test_entry_expiration(self):
        entry = CacheEntry(
            key="test", value="data", expires_at=datetime.now() - timedelta(seconds=10)
        )
        assert entry.is_expired is True

    def test_entry_not_expired(self):
        entry = CacheEntry(
            key="test", value="data", expires_at=datetime.now() + timedelta(seconds=60)
        )
        assert entry.is_expired is False

    def test_entry_serialization(self):
        entry = CacheEntry(key="test", value={"data": 123})
        data = entry.to_dict()

        assert data["key"] == "test"
        assert data["value"] == {"data": 123}

        restored = CacheEntry.from_dict(data)
        assert restored.key == entry.key
        assert restored.value == entry.value


class TestCacheStats:
    def test_initial_stats(self):
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self):
        stats = CacheStats(hits=75, misses=25)
        assert stats.hit_rate == 0.75
        assert stats.hit_rate_percent == "75.0%"

    def test_recording(self):
        stats = CacheStats()
        stats.record_hit()
        stats.record_hit()
        stats.record_miss()

        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.hit_rate == pytest.approx(0.666, rel=0.01)


class TestGenerateCacheKey:
    def test_simple_key(self):
        key = generate_cache_key("user", 123)
        assert key == "user:123"

    def test_with_prefix(self):
        key = generate_cache_key("user", 123, prefix="myapp")
        assert key == "myapp:user:123"

    def test_dict_params(self):
        key = generate_cache_key("query", {"a": 1, "b": 2})
        assert "a=1" in key
        assert "b=2" in key

    def test_long_key_hashing(self):
        long_value = "x" * 300
        key = generate_cache_key(long_value, hash_long_keys=True)
        assert len(key) < 250


# =============================================================================
# Memory Backend Tests
# =============================================================================


class TestMemoryCacheBackend:
    def test_set_and_get(self, memory_cache):
        memory_cache.set("key1", "value1")
        assert memory_cache.get("key1") == "value1"

    def test_get_missing_key(self, memory_cache):
        assert memory_cache.get("nonexistent") is None
        assert memory_cache.get("nonexistent", default="default") == "default"

    def test_delete(self, memory_cache):
        memory_cache.set("key1", "value1")
        assert memory_cache.delete("key1") is True
        assert memory_cache.get("key1") is None

    def test_delete_nonexistent(self, memory_cache):
        assert memory_cache.delete("nonexistent") is False

    def test_exists(self, memory_cache):
        memory_cache.set("key1", "value1")
        assert memory_cache.exists("key1") is True
        assert memory_cache.exists("nonexistent") is False

    def test_clear(self, memory_cache):
        memory_cache.set("key1", "value1")
        memory_cache.set("key2", "value2")

        memory_cache.clear()

        assert memory_cache.get("key1") is None
        assert memory_cache.get("key2") is None

    def test_ttl_expiration(self, memory_cache):
        memory_cache.set("key1", "value1", ttl=1)
        assert memory_cache.get("key1") == "value1"

        time.sleep(1.5)
        assert memory_cache.get("key1") is None

    def test_get_or_set(self, memory_cache):
        # First call - sets the value
        value = memory_cache.get_or_set("key1", "default_value")
        assert value == "default_value"

        # Second call - returns cached value
        value = memory_cache.get_or_set("key1", "new_value")
        assert value == "default_value"

    def test_get_or_set_callable(self, memory_cache):
        call_count = [0]

        def expensive_operation():
            call_count[0] += 1
            return "computed"

        value1 = memory_cache.get_or_set("key1", expensive_operation)
        value2 = memory_cache.get_or_set("key1", expensive_operation)

        assert value1 == "computed"
        assert value2 == "computed"
        assert call_count[0] == 1  # Only called once

    def test_add(self, memory_cache):
        assert memory_cache.add("key1", "value1") is True
        assert memory_cache.add("key1", "value2") is False
        assert memory_cache.get("key1") == "value1"

    def test_incr_decr(self, memory_cache):
        memory_cache.set("counter", 10)

        assert memory_cache.incr("counter") == 11
        assert memory_cache.incr("counter", 5) == 16
        assert memory_cache.decr("counter") == 15
        assert memory_cache.decr("counter", 5) == 10

    def test_get_many(self, memory_cache):
        memory_cache.set("key1", "value1")
        memory_cache.set("key2", "value2")

        result = memory_cache.get_many(["key1", "key2", "key3"])

        assert result["key1"] == "value1"
        assert result["key2"] == "value2"
        assert "key3" not in result

    def test_set_many(self, memory_cache):
        memory_cache.set_many(
            {
                "key1": "value1",
                "key2": "value2",
            }
        )

        assert memory_cache.get("key1") == "value1"
        assert memory_cache.get("key2") == "value2"

    def test_delete_many(self, memory_cache):
        memory_cache.set("key1", "value1")
        memory_cache.set("key2", "value2")

        count = memory_cache.delete_many(["key1", "key2"])

        assert count == 2
        assert memory_cache.get("key1") is None
        assert memory_cache.get("key2") is None

    def test_keys_pattern(self, memory_cache):
        memory_cache.set("user:1", "data1")
        memory_cache.set("user:2", "data2")
        memory_cache.set("order:1", "order1")

        keys = memory_cache.keys("user:*")
        assert len(keys) == 2

    def test_stats_tracking(self, memory_cache):
        memory_cache.set("key1", "value1")
        memory_cache.get("key1")  # hit
        memory_cache.get("key1")  # hit
        memory_cache.get("nonexistent")  # miss

        stats = memory_cache.get_stats_dict()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["sets"] == 1

    def test_lru_eviction(self):
        cache = MemoryCacheBackend(CacheConfig(max_entries=3, key_prefix="test"))

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

    def test_thread_safety(self, memory_cache):
        errors = []

        def worker(n):
            try:
                for i in range(100):
                    memory_cache.set(f"key_{n}_{i}", f"value_{n}_{i}")
                    memory_cache.get(f"key_{n}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# =============================================================================
# File Backend Tests
# =============================================================================


class TestFileCacheBackend:
    def test_set_and_get(self, file_cache):
        file_cache.set("key1", "value1")
        assert file_cache.get("key1") == "value1"

    def test_persistence(self, file_cache, tmp_path):
        file_cache.set("key1", "value1")

        # Create new instance
        cache2 = FileCacheBackend(
            CacheConfig(cache_dir=str(tmp_path), cache_file="test_cache.json", key_prefix="test")
        )

        assert cache2.get("key1") == "value1"

    def test_complex_values(self, file_cache):
        data = {"name": "test", "items": [1, 2, 3], "nested": {"a": 1, "b": 2}}
        file_cache.set("complex", data)

        result = file_cache.get("complex")
        assert result == data

    def test_file_stats(self, file_cache):
        file_cache.set("key1", "value1")
        stats = file_cache.get_file_stats()

        assert "cache_file" in stats
        assert stats["total_entries"] == 1


# =============================================================================
# Lock Tests
# =============================================================================


class TestCacheLock:
    def test_lock_acquisition(self, memory_cache):
        with memory_cache.lock("test_lock") as acquired:
            assert acquired is True

    def test_lock_blocking(self, memory_cache):
        results = []

        def worker1():
            with memory_cache.lock("shared", timeout=5) as acquired:
                results.append(("worker1", acquired))
                time.sleep(0.5)

        def worker2():
            time.sleep(0.1)  # Start slightly later
            with memory_cache.lock("shared", blocking_timeout=0.1) as acquired:
                results.append(("worker2", acquired))

        t1 = threading.Thread(target=worker1)
        t2 = threading.Thread(target=worker2)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert ("worker1", True) in results
        assert ("worker2", False) in results


# =============================================================================
# Decorator Tests
# =============================================================================


class TestCachedDecorator:
    def test_basic_caching(self, memory_cache):
        call_count = [0]

        @cached(ttl=60, cache_backend=memory_cache)
        def expensive_function(x):
            call_count[0] += 1
            return x * 2

        assert expensive_function(5) == 10
        assert expensive_function(5) == 10
        assert call_count[0] == 1

    def test_different_args(self, memory_cache):
        call_count = [0]

        @cached(ttl=60, cache_backend=memory_cache)
        def add(a, b):
            call_count[0] += 1
            return a + b

        assert add(1, 2) == 3
        assert add(1, 2) == 3
        assert add(2, 3) == 5
        assert call_count[0] == 2


# =============================================================================
# Backend Factory Tests
# =============================================================================


class TestCreateBackend:
    def test_create_memory(self):
        cache = create_backend(CacheBackend.MEMORY)
        assert isinstance(cache, MemoryCacheBackend)

    def test_create_file(self, tmp_path):
        cache = create_backend(CacheBackend.FILE, CacheConfig(cache_dir=str(tmp_path)))
        assert isinstance(cache, FileCacheBackend)

    def test_invalid_backend(self):
        with pytest.raises(ValueError):
            create_backend("invalid")


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthCheck:
    def test_memory_health(self, memory_cache):
        assert memory_cache.health_check() is True

    def test_file_health(self, file_cache):
        assert file_cache.health_check() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
