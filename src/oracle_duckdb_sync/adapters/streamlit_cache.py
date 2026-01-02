"""
Streamlit Cache Provider - Streamlit-specific cache implementation.

This adapter allows the application to use Streamlit's caching without
the core business logic depending on it.
"""

from typing import Any, Callable, Optional
import streamlit as st
from functools import wraps

from ..application.cache_provider import CacheProvider


class StreamlitCacheProvider(CacheProvider):
    """
    Streamlit-specific cache implementation.
    
    Uses Streamlit's session_state for simple key-value caching
    and st.cache_data decorator for function result caching.
    """
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Streamlit session state."""
        cache_key = f"cache_{key}"
        return st.session_state.get(cache_key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in Streamlit session state."""
        cache_key = f"cache_{key}"
        st.session_state[cache_key] = value
        # Note: Streamlit session_state doesn't support TTL
    
    def delete(self, key: str) -> None:
        """Delete value from Streamlit session state."""
        cache_key = f"cache_{key}"
        if cache_key in st.session_state:
            del st.session_state[cache_key]
    
    def clear(self) -> None:
        """Clear all cache entries from session state."""
        keys_to_delete = [k for k in st.session_state.keys() if k.startswith("cache_")]
        for key in keys_to_delete:
            del st.session_state[key]
        
        # Also clear Streamlit's cache_data
        st.cache_data.clear()
    
    def has(self, key: str) -> bool:
        """Check if key exists in session state."""
        cache_key = f"cache_{key}"
        return cache_key in st.session_state
    
    def cached_function(self, func: Callable, key_prefix: Optional[str] = None) -> Callable:
        """
        Use Streamlit's @st.cache_data decorator for function caching.
        
        This is more efficient than manual caching as Streamlit handles
        cache invalidation and memory management.
        """
        # Use Streamlit's built-in caching
        cached_func = st.cache_data(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return cached_func(*args, **kwargs)
        
        return wrapper


class StreamlitDataCacheDecorator:
    """
    Helper class to use Streamlit's @st.cache_data as a drop-in replacement.
    
    This allows existing code using @st.cache_data to work with the
    cache provider pattern.
    """
    
    def __init__(self, cache_provider: Optional[CacheProvider] = None):
        self.cache_provider = cache_provider or StreamlitCacheProvider()
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator that uses the cache provider."""
        return self.cache_provider.cached_function(func)
    
    @staticmethod
    def clear():
        """Clear Streamlit's cache_data."""
        st.cache_data.clear()
