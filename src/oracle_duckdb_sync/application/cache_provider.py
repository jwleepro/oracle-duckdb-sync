"""
Cache Provider Interface - Framework-independent caching abstraction.

This module defines abstract interfaces for caching that allow the application
to use caching without depending on any specific UI framework.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Dict
from functools import wraps


class CacheProvider(ABC):
    """
    Abstract interface for cache management.
    
    This allows the application to be cache-implementation agnostic.
    Implementations can be created for Streamlit, Redis, in-memory, etc.
    """
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if exists, None otherwise
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set cache value.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete cached value by key.
        
        Args:
            key: Cache key to delete
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        pass
    
    @abstractmethod
    def has(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    def cached_function(self, func: Callable, key_prefix: Optional[str] = None) -> Callable:
        """
        Decorator to cache function results.
        
        Args:
            func: Function to cache
            key_prefix: Optional prefix for cache keys
            
        Returns:
            Wrapped function with caching
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = self._generate_cache_key(func, args, kwargs, key_prefix)
            
            # Check if result is cached
            cached_result = self.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            self.set(cache_key, result)
            return result
        
        return wrapper
    
    def _generate_cache_key(self, func: Callable, args: tuple, kwargs: dict, 
                           prefix: Optional[str] = None) -> str:
        """
        Generate cache key from function and arguments.
        
        Args:
            func: Function being cached
            args: Positional arguments
            kwargs: Keyword arguments
            prefix: Optional prefix
            
        Returns:
            Cache key string
        """
        func_name = f"{func.__module__}.{func.__name__}"
        
        # Convert args and kwargs to string representation
        args_str = "_".join(str(arg) for arg in args)
        kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        
        parts = [prefix or "", func_name, args_str, kwargs_str]
        key = "_".join(filter(None, parts))
        
        # Hash if key is too long
        if len(key) > 200:
            import hashlib
            key = f"{prefix or func_name}_{hashlib.md5(key.encode()).hexdigest()}"
        
        return key


class InMemoryCacheProvider(CacheProvider):
    """
    Simple in-memory cache implementation.
    
    This is useful for testing or when no UI framework is available.
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        # Note: TTL is not implemented in this simple version
        self._cache[key] = value
    
    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        self._cache.clear()
    
    def has(self, key: str) -> bool:
        return key in self._cache


class NoCacheProvider(CacheProvider):
    """
    No-op cache provider that doesn't cache anything.
    
    Useful for testing or when caching should be disabled.
    """
    
    def get(self, key: str) -> Optional[Any]:
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass
    
    def delete(self, key: str) -> None:
        pass
    
    def clear(self) -> None:
        pass
    
    def has(self, key: str) -> bool:
        return False
