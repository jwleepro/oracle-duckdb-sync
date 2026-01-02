"""
Test cache provider implementations.

This module tests the framework-independent cache provider interface
and its implementations.
"""

import pytest
from oracle_duckdb_sync.application.cache_provider import (
    CacheProvider,
    InMemoryCacheProvider,
    NoCacheProvider
)


class TestInMemoryCacheProvider:
    """Test in-memory cache provider."""
    
    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = InMemoryCacheProvider()
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        cache = InMemoryCacheProvider()
        assert cache.get("nonexistent") is None
    
    def test_has_key(self):
        """Test checking if key exists."""
        cache = InMemoryCacheProvider()
        
        assert not cache.has("key1")
        cache.set("key1", "value1")
        assert cache.has("key1")
    
    def test_delete_key(self):
        """Test deleting a key."""
        cache = InMemoryCacheProvider()
        
        cache.set("key1", "value1")
        assert cache.has("key1")
        
        cache.delete("key1")
        assert not cache.has("key1")
        assert cache.get("key1") is None
    
    def test_clear_all(self):
        """Test clearing all cache."""
        cache = InMemoryCacheProvider()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        assert cache.has("key1")
        assert cache.has("key2")
        
        cache.clear()
        
        assert not cache.has("key1")
        assert not cache.has("key2")
        assert not cache.has("key3")
    
    def test_cached_function(self):
        """Test function caching decorator."""
        cache = InMemoryCacheProvider()
        
        call_count = 0
        
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        cached_func = cache.cached_function(expensive_function)
        
        # First call - should execute function
        result1 = cached_func(1, 2)
        assert result1 == 3
        assert call_count == 1
        
        # Second call with same args - should use cache
        result2 = cached_func(1, 2)
        assert result2 == 3
        assert call_count == 1  # Not incremented!
        
        # Call with different args - should execute function
        result3 = cached_func(2, 3)
        assert result3 == 5
        assert call_count == 2


class TestNoCacheProvider:
    """Test no-op cache provider."""
    
    def test_get_always_returns_none(self):
        """Test that get always returns None."""
        cache = NoCacheProvider()
        
        cache.set("key1", "value1")
        assert cache.get("key1") is None
    
    def test_has_always_returns_false(self):
        """Test that has always returns False."""
        cache = NoCacheProvider()
        
        cache.set("key1", "value1")
        assert not cache.has("key1")
    
    def test_operations_are_noops(self):
        """Test that all operations are no-ops."""
        cache = NoCacheProvider()
        
        # These should not raise errors
        cache.set("key", "value")
        cache.delete("key")
        cache.clear()
        
        assert cache.get("key") is None


class TestCacheProviderInterface:
    """Test cache provider interface compliance."""
    
    def test_in_memory_implements_interface(self):
        """Test that InMemoryCacheProvider implements CacheProvider."""
        cache = InMemoryCacheProvider()
        assert isinstance(cache, CacheProvider)
    
    def test_no_cache_implements_interface(self):
        """Test that NoCacheProvider implements CacheProvider."""
        cache = NoCacheProvider()
        assert isinstance(cache, CacheProvider)


class TestCacheKeyGeneration:
    """Test cache key generation."""
    
    def test_generate_cache_key_simple(self):
        """Test cache key generation with simple arguments."""
        cache = InMemoryCacheProvider()
        
        def my_func(a, b):
            return a + b
        
        key1 = cache._generate_cache_key(my_func, (1, 2), {})
        key2 = cache._generate_cache_key(my_func, (1, 2), {})
        key3 = cache._generate_cache_key(my_func, (2, 3), {})
        
        # Same args should generate same key
        assert key1 == key2
        
        # Different args should generate different key
        assert key1 != key3
    
    def test_generate_cache_key_with_kwargs(self):
        """Test cache key generation with keyword arguments."""
        cache = InMemoryCacheProvider()
        
        def my_func(a, b=10):
            return a + b
        
        key1 = cache._generate_cache_key(my_func, (1,), {'b': 10})
        key2 = cache._generate_cache_key(my_func, (1,), {'b': 10})
        key3 = cache._generate_cache_key(my_func, (1,), {'b': 20})
        
        assert key1 == key2
        assert key1 != key3
    
    def test_generate_cache_key_with_prefix(self):
        """Test cache key generation with prefix."""
        cache = InMemoryCacheProvider()
        
        def my_func(a):
            return a
        
        key1 = cache._generate_cache_key(my_func, (1,), {}, prefix="test")
        key2 = cache._generate_cache_key(my_func, (1,), {}, prefix="prod")
        
        assert "test" in key1
        assert "prod" in key2
        assert key1 != key2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
