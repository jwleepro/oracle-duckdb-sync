"""
Query-specific cache manager.

This module provides specialized caching for query results and metadata,
building on top of the generic CacheProvider interface.
"""

import pandas as pd
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Optional

from oracle_duckdb_sync.application.cache_provider import CacheProvider
from oracle_duckdb_sync.log.logger import setup_logger


# Set up logger
cache_logger = setup_logger('QueryCacheManager')


@dataclass
class CachedQueryMetadata:
    """
    Metadata associated with cached query results.

    This tracks information needed for incremental loading and cache validation.

    Attributes:
        last_timestamp: Last timestamp value from the data (for incremental loading)
        row_count: Number of rows in the cached data
        last_update: Timestamp when the cache was last updated
        selected_conversions: User-selected type conversions to reapply
        query_params: Original query parameters (for cache validation)
    """
    last_timestamp: Optional[Any]
    row_count: int
    last_update: datetime
    selected_conversions: Optional[dict[str, str]] = None
    query_params: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'CachedQueryMetadata':
        """Create from dictionary."""
        return cls(**data)


class QueryCacheManager:
    """
    Manages caching for query results and metadata.

    This class provides:
    - DataFrame caching with automatic key generation
    - Metadata caching for incremental loading
    - Cache invalidation strategies
    - Cache hit/miss tracking
    """

    # Cache key prefixes
    DATA_PREFIX = "query_data"
    METADATA_PREFIX = "query_metadata"

    def __init__(self, cache_provider: CacheProvider):
        """
        Initialize QueryCacheManager with a cache provider.

        Args:
            cache_provider: CacheProvider implementation for actual storage
        """
        self.cache = cache_provider
        self.logger = cache_logger
        self._hit_count = 0
        self._miss_count = 0

    def get_cached_data(self, table_name: str, cache_key: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Retrieve cached DataFrame for a table.

        Args:
            table_name: Name of the table
            cache_key: Optional custom cache key. If None, uses table name

        Returns:
            Cached DataFrame if exists, None otherwise

        Example:
            >>> manager = QueryCacheManager(cache_provider)
            >>> df = manager.get_cached_data("users")
            >>> if df is not None:
            ...     print(f"Cache hit: {len(df)} rows")
        """
        key = self._generate_data_key(table_name, cache_key)
        df = self.cache.get(key)

        if df is not None:
            self._hit_count += 1
            self.logger.info(f"Cache hit for '{table_name}': {len(df)} rows")
        else:
            self._miss_count += 1
            self.logger.info(f"Cache miss for '{table_name}'")

        return df

    def set_cached_data(
        self,
        table_name: str,
        df: pd.DataFrame,
        metadata: CachedQueryMetadata,
        cache_key: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache DataFrame and its metadata.

        Args:
            table_name: Name of the table
            df: DataFrame to cache
            metadata: Metadata associated with the DataFrame
            cache_key: Optional custom cache key. If None, uses table name
            ttl: Optional time-to-live in seconds

        Example:
            >>> manager = QueryCacheManager(cache_provider)
            >>> df = pd.DataFrame({'id': [1, 2, 3]})
            >>> metadata = CachedQueryMetadata(
            ...     last_timestamp=None,
            ...     row_count=3,
            ...     last_update=datetime.now()
            ... )
            >>> manager.set_cached_data("users", df, metadata)
        """
        data_key = self._generate_data_key(table_name, cache_key)
        metadata_key = self._generate_metadata_key(table_name, cache_key)

        # Cache DataFrame
        self.cache.set(data_key, df, ttl)

        # Cache metadata
        self.cache.set(metadata_key, metadata, ttl)

        self.logger.info(
            f"Cached '{table_name}': {len(df)} rows, "
            f"last_timestamp={metadata.last_timestamp}"
        )

    def get_metadata(
        self,
        table_name: str,
        cache_key: Optional[str] = None
    ) -> Optional[CachedQueryMetadata]:
        """
        Retrieve cached metadata for a table.

        Args:
            table_name: Name of the table
            cache_key: Optional custom cache key. If None, uses table name

        Returns:
            CachedQueryMetadata if exists, None otherwise

        Example:
            >>> manager = QueryCacheManager(cache_provider)
            >>> metadata = manager.get_metadata("users")
            >>> if metadata:
            ...     print(f"Last timestamp: {metadata.last_timestamp}")
            ...     print(f"Row count: {metadata.row_count}")
        """
        key = self._generate_metadata_key(table_name, cache_key)
        metadata = self.cache.get(key)

        if metadata:
            self.logger.info(f"Retrieved metadata for '{table_name}'")
        else:
            self.logger.info(f"No metadata found for '{table_name}'")

        return metadata

    def has_cache(self, table_name: str, cache_key: Optional[str] = None) -> bool:
        """
        Check if cache exists for a table.

        Args:
            table_name: Name of the table
            cache_key: Optional custom cache key. If None, uses table name

        Returns:
            True if both data and metadata are cached, False otherwise

        Example:
            >>> manager = QueryCacheManager(cache_provider)
            >>> if manager.has_cache("users"):
            ...     print("Cache exists")
            ... else:
            ...     print("No cache")
        """
        data_key = self._generate_data_key(table_name, cache_key)
        metadata_key = self._generate_metadata_key(table_name, cache_key)

        has_data = self.cache.has(data_key)
        has_metadata = self.cache.has(metadata_key)

        return has_data and has_metadata

    def clear_cache(
        self,
        table_name: Optional[str] = None,
        cache_key: Optional[str] = None
    ) -> None:
        """
        Clear cached data and metadata.

        Args:
            table_name: Optional table name. If None, clears all query caches
            cache_key: Optional custom cache key

        Example:
            >>> manager = QueryCacheManager(cache_provider)
            >>> # Clear specific table cache
            >>> manager.clear_cache("users")
            >>> # Clear all query caches
            >>> manager.clear_cache()
        """
        if table_name:
            # Clear specific table cache
            data_key = self._generate_data_key(table_name, cache_key)
            metadata_key = self._generate_metadata_key(table_name, cache_key)

            self.cache.delete(data_key)
            self.cache.delete(metadata_key)

            self.logger.info(f"Cleared cache for '{table_name}'")
        else:
            # Clear all caches
            self.cache.clear()
            self.logger.info("Cleared all query caches")

        # Reset statistics
        self._hit_count = 0
        self._miss_count = 0

    def update_metadata(
        self,
        table_name: str,
        updates: dict[str, Any],
        cache_key: Optional[str] = None
    ) -> None:
        """
        Update specific fields in cached metadata without replacing entire metadata.

        Args:
            table_name: Name of the table
            updates: Dictionary of fields to update
            cache_key: Optional custom cache key

        Example:
            >>> manager = QueryCacheManager(cache_provider)
            >>> # Update only last_timestamp
            >>> manager.update_metadata("users", {
            ...     "last_timestamp": "2024-01-01 12:00:00",
            ...     "row_count": 1500
            ... })
        """
        metadata = self.get_metadata(table_name, cache_key)

        if metadata is None:
            self.logger.warning(f"No metadata found for '{table_name}', cannot update")
            return

        # Update fields
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)

        # Save updated metadata
        metadata_key = self._generate_metadata_key(table_name, cache_key)
        self.cache.set(metadata_key, metadata)

        self.logger.info(f"Updated metadata for '{table_name}': {list(updates.keys())}")

    def get_cache_statistics(self) -> dict[str, Any]:
        """
        Get cache hit/miss statistics.

        Returns:
            Dictionary with cache statistics

        Example:
            >>> manager = QueryCacheManager(cache_provider)
            >>> stats = manager.get_cache_statistics()
            >>> print(f"Hit rate: {stats['hit_rate']:.2%}")
        """
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0.0

        return {
            'hit_count': self._hit_count,
            'miss_count': self._miss_count,
            'total_requests': total,
            'hit_rate': hit_rate
        }

    def _generate_data_key(self, table_name: str, custom_key: Optional[str] = None) -> str:
        """
        Generate cache key for DataFrame data.

        Args:
            table_name: Name of the table
            custom_key: Optional custom key suffix

        Returns:
            Cache key string
        """
        if custom_key:
            return f"{self.DATA_PREFIX}_{table_name}_{custom_key}"
        return f"{self.DATA_PREFIX}_{table_name}"

    def _generate_metadata_key(self, table_name: str, custom_key: Optional[str] = None) -> str:
        """
        Generate cache key for metadata.

        Args:
            table_name: Name of the table
            custom_key: Optional custom key suffix

        Returns:
            Cache key string
        """
        if custom_key:
            return f"{self.METADATA_PREFIX}_{table_name}_{custom_key}"
        return f"{self.METADATA_PREFIX}_{table_name}"

    def invalidate_if_stale(
        self,
        table_name: str,
        max_age_seconds: int,
        cache_key: Optional[str] = None
    ) -> bool:
        """
        Invalidate cache if it's older than max_age_seconds.

        Args:
            table_name: Name of the table
            max_age_seconds: Maximum age in seconds before cache is considered stale
            cache_key: Optional custom cache key

        Returns:
            True if cache was invalidated, False otherwise

        Example:
            >>> manager = QueryCacheManager(cache_provider)
            >>> # Invalidate cache older than 5 minutes
            >>> if manager.invalidate_if_stale("users", max_age_seconds=300):
            ...     print("Cache was stale and invalidated")
        """
        metadata = self.get_metadata(table_name, cache_key)

        if metadata is None:
            return False

        # Check age
        age = (datetime.now() - metadata.last_update).total_seconds()

        if age > max_age_seconds:
            self.clear_cache(table_name, cache_key)
            self.logger.info(
                f"Cache for '{table_name}' invalidated (age: {age:.0f}s > {max_age_seconds}s)"
            )
            return True

        return False
