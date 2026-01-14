"""
Enhanced query service with caching and incremental loading.

This module provides the main business logic for querying data with
caching, incremental loading, and type conversion.
"""

import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from oracle_duckdb_sync.application.query_cache_manager import (
    QueryCacheManager,
    CachedQueryMetadata
)
from oracle_duckdb_sync.config.query_constants import QUERY_CONSTANTS
from oracle_duckdb_sync.data.incremental_loader import IncrementalLoader
from oracle_duckdb_sync.data.query_executor import QueryExecutor
from oracle_duckdb_sync.data.type_converter_service import TypeConverterService
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger


# Set up logger
service_logger = setup_logger('EnhancedQueryService')


@dataclass
class QueryServiceResult:
    """
    Result of a query service operation.

    Attributes:
        success: Whether the operation succeeded
        df_converted: DataFrame with converted types (if successful)
        df_original: Original DataFrame before conversion (optional)
        conversions: Dictionary mapping column names to (old_type, new_type) tuples
        suggestions: Dictionary of columns that can be converted
        is_incremental: Whether this was an incremental load
        row_count: Number of rows in the result
        error: Error message if failed
    """
    success: bool
    df_converted: Optional[pd.DataFrame]
    df_original: Optional[pd.DataFrame]
    conversions: dict[str, tuple[str, str]]
    suggestions: dict[str, str]
    is_incremental: bool
    row_count: int
    error: Optional[str] = None


class EnhancedQueryService:
    """
    Enhanced query service with caching and incremental loading support.

    This service orchestrates:
    - Query execution via QueryExecutor
    - Incremental loading via IncrementalLoader
    - Type conversion via TypeConverterService
    - Caching via QueryCacheManager

    It provides a clean, framework-independent API for data queries.
    """

    def __init__(
        self,
        duckdb_source: DuckDBSource,
        cache_manager: QueryCacheManager,
        incremental_loader: IncrementalLoader,
        type_converter: TypeConverterService
    ):
        """
        Initialize EnhancedQueryService with dependencies.

        Args:
            duckdb_source: DuckDB data source
            cache_manager: Cache manager for query results
            incremental_loader: Incremental data loader
            type_converter: Type conversion service
        """
        self.duckdb = duckdb_source
        self.cache = cache_manager
        self.incremental = incremental_loader
        self.converter = type_converter
        self.logger = service_logger

    def query_with_caching(
        self,
        table_name: str,
        limit: int = QUERY_CONSTANTS.DEFAULT_QUERY_LIMIT,
        time_column: Optional[str] = None,
        selected_conversions: Optional[dict[str, str]] = None
    ) -> QueryServiceResult:
        """
        Query table with caching and incremental loading support.

        Workflow:
        1. Check cache for existing data
        2. If cache exists and time_column provided, perform incremental load
        3. Otherwise, perform initial load
        4. Apply type conversions
        5. Merge with cached data (if incremental)
        6. Update cache

        Args:
            table_name: Name of the table to query
            limit: Maximum rows for initial load (ignored for incremental)
            time_column: Timestamp column for incremental loading (optional)
            selected_conversions: User-selected type conversions (optional)

        Returns:
            QueryServiceResult with data and metadata

        Example:
            >>> service = EnhancedQueryService(duckdb, cache, loader, converter)
            >>> # Initial query
            >>> result = service.query_with_caching("users", limit=1000, time_column="created_at")
            >>> print(f"Loaded {result.row_count} rows (incremental: {result.is_incremental})")

            >>> # Subsequent query (incremental)
            >>> result2 = service.query_with_caching("users", time_column="created_at")
            >>> print(f"Loaded {result2.row_count} rows (incremental: {result2.is_incremental})")
        """
        self.logger.info(f"Query request: table='{table_name}', limit={limit}, time_column={time_column}")

        # Check if we have cached data
        has_cache = self.cache.has_cache(table_name)
        metadata = self.cache.get_metadata(table_name) if has_cache else None

        # Determine if incremental mode is possible
        use_incremental = (
            time_column is not None
            and has_cache
            and metadata is not None
            and metadata.last_timestamp is not None
        )

        if use_incremental:
            self.logger.info(f"Using incremental mode (last_timestamp: {metadata.last_timestamp})")
            return self._perform_incremental_load(
                table_name, time_column, metadata, selected_conversions
            )
        else:
            self.logger.info("Using initial load mode")
            return self._perform_initial_load(
                table_name, limit, time_column, selected_conversions
            )

    def query_with_conversion_options(
        self,
        table_name: str,
        limit: int = QUERY_CONSTANTS.DEFAULT_QUERY_LIMIT,
        time_column: Optional[str] = None
    ) -> QueryServiceResult:
        """
        Query table and detect conversion options without applying them.

        This is useful for presenting conversion options to users
        before applying them.

        Args:
            table_name: Name of the table to query
            limit: Maximum rows to return
            time_column: Timestamp column for incremental loading (optional)

        Returns:
            QueryServiceResult with original data and conversion suggestions

        Example:
            >>> service = EnhancedQueryService(duckdb, cache, loader, converter)
            >>> result = service.query_with_conversion_options("users", limit=100)
            >>> print(f"Suggested conversions: {result.suggestions}")
        """
        self.logger.info(f"Query with conversion options: table='{table_name}'")

        # Perform query without automatic conversion
        result = self.query_with_caching(
            table_name, limit, time_column,
            selected_conversions={}  # Empty dict prevents automatic conversion
        )

        if not result.success:
            return result

        # Detect conversion suggestions
        suggestions = self.converter.detect_convertible_columns(result.df_converted)

        return QueryServiceResult(
            success=True,
            df_converted=result.df_converted,
            df_original=result.df_original,
            conversions={},
            suggestions=suggestions,
            is_incremental=result.is_incremental,
            row_count=result.row_count,
            error=None
        )

    def _perform_initial_load(
        self,
        table_name: str,
        limit: int,
        time_column: Optional[str],
        selected_conversions: Optional[dict[str, str]]
    ) -> QueryServiceResult:
        """
        Perform initial data load.

        Args:
            table_name: Name of the table
            limit: Maximum rows to load
            time_column: Timestamp column (optional)
            selected_conversions: User-selected conversions (optional)

        Returns:
            QueryServiceResult with loaded data
        """
        try:
            # Fetch data
            if time_column:
                # Use incremental loader with no last_timestamp (initial load)
                load_result = self.incremental.fetch_incremental(
                    table_name, time_column, last_timestamp=None, limit=limit
                )
                df = load_result.data
                max_timestamp = load_result.max_timestamp
            else:
                # Use executor for simple query
                from oracle_duckdb_sync.data.query_builder import QueryBuilder
                query = QueryBuilder.build_select_query(table_name, limit)
                df = self.incremental.executor.fetch_to_dataframe(query)
                max_timestamp = None

            if df.empty:
                self.logger.warning(f"No data returned for table '{table_name}'")
                return QueryServiceResult(
                    success=False,
                    df_converted=None,
                    df_original=None,
                    conversions={},
                    suggestions={},
                    is_incremental=False,
                    row_count=0,
                    error="No data returned"
                )

            # Apply type conversion
            if selected_conversions is None:
                # Automatic conversion
                conversion_result = self.converter.convert_automatic(df, preserve_original=True)
            elif selected_conversions:
                # Selective conversion
                conversion_result = self.converter.convert_selected(
                    df, selected_conversions, preserve_original=True
                )
            else:
                # No conversion (empty dict provided)
                conversion_result = self.converter.convert_automatic(df, preserve_original=True)
                conversion_result.conversions = {}  # Clear conversions
                conversion_result.df_converted = df  # Use original

            # Cache the result
            metadata = CachedQueryMetadata(
                last_timestamp=max_timestamp,
                row_count=len(conversion_result.df_converted),
                last_update=datetime.now(),
                selected_conversions=selected_conversions
            )
            self.cache.set_cached_data(table_name, conversion_result.df_converted, metadata)

            self.logger.info(
                f"Initial load complete: {len(conversion_result.df_converted)} rows, "
                f"{len(conversion_result.conversions)} conversions"
            )

            return QueryServiceResult(
                success=True,
                df_converted=conversion_result.df_converted,
                df_original=conversion_result.df_original,
                conversions=conversion_result.conversions,
                suggestions=conversion_result.suggestions,
                is_incremental=False,
                row_count=len(conversion_result.df_converted),
                error=None
            )

        except Exception as e:
            self.logger.error(f"Initial load failed: {e}")
            import traceback
            self.logger.error(f"Traceback:\n{traceback.format_exc()}")

            return QueryServiceResult(
                success=False,
                df_converted=None,
                df_original=None,
                conversions={},
                suggestions={},
                is_incremental=False,
                row_count=0,
                error=str(e)
            )

    def _perform_incremental_load(
        self,
        table_name: str,
        time_column: str,
        metadata: CachedQueryMetadata,
        selected_conversions: Optional[dict[str, str]]
    ) -> QueryServiceResult:
        """
        Perform incremental data load.

        Args:
            table_name: Name of the table
            time_column: Timestamp column
            metadata: Cached metadata with last_timestamp
            selected_conversions: User-selected conversions (optional)

        Returns:
            QueryServiceResult with merged data
        """
        try:
            # Fetch incremental data
            load_result = self.incremental.fetch_incremental(
                table_name,
                time_column,
                last_timestamp=metadata.last_timestamp,
                limit=None  # No limit for incremental
            )

            # If no new data, return cached data
            if load_result.row_count == 0:
                self.logger.info("No new data, returning cached result")
                cached_df = self.cache.get_cached_data(table_name)

                return QueryServiceResult(
                    success=True,
                    df_converted=cached_df,
                    df_original=None,
                    conversions={},
                    suggestions={},
                    is_incremental=True,
                    row_count=len(cached_df) if cached_df is not None else 0,
                    error=None
                )

            # Apply type conversion to new data
            df_new = load_result.data

            if selected_conversions is None and metadata.selected_conversions:
                # Reapply previously selected conversions
                selected_conversions = metadata.selected_conversions

            if selected_conversions is None:
                # Automatic conversion
                conversion_result = self.converter.convert_automatic(df_new, preserve_original=True)
            elif selected_conversions:
                # Selective conversion
                conversion_result = self.converter.convert_selected(
                    df_new, selected_conversions, preserve_original=True
                )
            else:
                # No conversion
                conversion_result = self.converter.convert_automatic(df_new, preserve_original=True)
                conversion_result.conversions = {}
                conversion_result.df_converted = df_new

            # Merge with cached data
            cached_df = self.cache.get_cached_data(table_name)
            df_merged = self.incremental.merge_with_existing(
                cached_df, conversion_result.df_converted, time_column
            )

            # Update cache
            new_metadata = CachedQueryMetadata(
                last_timestamp=load_result.max_timestamp,
                row_count=len(df_merged),
                last_update=datetime.now(),
                selected_conversions=selected_conversions
            )
            self.cache.set_cached_data(table_name, df_merged, new_metadata)

            self.logger.info(
                f"Incremental load complete: +{load_result.row_count} new rows, "
                f"total {len(df_merged)} rows"
            )

            return QueryServiceResult(
                success=True,
                df_converted=df_merged,
                df_original=conversion_result.df_original,
                conversions=conversion_result.conversions,
                suggestions=conversion_result.suggestions,
                is_incremental=True,
                row_count=len(df_merged),
                error=None
            )

        except Exception as e:
            self.logger.error(f"Incremental load failed: {e}")
            import traceback
            self.logger.error(f"Traceback:\n{traceback.format_exc()}")

            # On error, try to return cached data if available
            cached_df = self.cache.get_cached_data(table_name)

            return QueryServiceResult(
                success=False,
                df_converted=cached_df,
                df_original=None,
                conversions={},
                suggestions={},
                is_incremental=True,
                row_count=len(cached_df) if cached_df is not None else 0,
                error=str(e)
            )

    def clear_cache(self, table_name: Optional[str] = None) -> None:
        """
        Clear cache for a table or all tables.

        Args:
            table_name: Optional table name. If None, clears all caches

        Example:
            >>> service.clear_cache("users")  # Clear specific table
            >>> service.clear_cache()  # Clear all caches
        """
        self.cache.clear_cache(table_name)
        self.logger.info(f"Cache cleared: {table_name or 'all tables'}")

    def get_cache_info(self, table_name: str) -> Optional[CachedQueryMetadata]:
        """
        Get cache metadata for a table.

        Args:
            table_name: Name of the table

        Returns:
            CachedQueryMetadata if cached, None otherwise

        Example:
            >>> info = service.get_cache_info("users")
            >>> if info:
            ...     print(f"Last update: {info.last_update}")
            ...     print(f"Row count: {info.row_count}")
        """
        return self.cache.get_metadata(table_name)
