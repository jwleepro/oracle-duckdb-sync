"""
Incremental data loading for DuckDB queries.

This module handles incremental loading of data based on timestamps,
including fetching new data and merging with existing data.
"""

import pandas as pd
from dataclasses import dataclass
from typing import Any, Optional

from oracle_duckdb_sync.data.query_builder import QueryBuilder
from oracle_duckdb_sync.data.query_executor import QueryExecutor, QueryExecutionError
from oracle_duckdb_sync.log.logger import setup_logger


# Set up logger
incremental_logger = setup_logger('IncrementalLoader')


@dataclass
class IncrementalLoadResult:
    """
    Result of an incremental load operation.

    Attributes:
        data: Loaded DataFrame
        max_timestamp: Maximum timestamp value in the loaded data
        row_count: Number of rows loaded
        is_initial_load: True if this was the first load (no previous timestamp)
    """
    data: pd.DataFrame
    max_timestamp: Optional[Any]
    row_count: int
    is_initial_load: bool


class IncrementalLoader:
    """
    Handles incremental data loading based on timestamps.

    This class provides:
    - Time-based incremental data fetching
    - DataFrame merging with deduplication
    - Timestamp tracking for subsequent loads
    """

    def __init__(self, query_executor: QueryExecutor):
        """
        Initialize IncrementalLoader with a QueryExecutor.

        Args:
            query_executor: QueryExecutor instance for running queries
        """
        self.executor = query_executor
        self.logger = incremental_logger

    def fetch_incremental(
        self,
        table_name: str,
        time_column: str,
        last_timestamp: Optional[Any] = None,
        limit: Optional[int] = None
    ) -> IncrementalLoadResult:
        """
        Fetch incremental data since the last timestamp.

        Args:
            table_name: Name of the table to query
            time_column: Name of the timestamp column for ordering
            last_timestamp: Last timestamp from previous query.
                           If None, performs initial load
            limit: Optional maximum number of rows to fetch

        Returns:
            IncrementalLoadResult containing loaded data and metadata

        Raises:
            QueryExecutionError: If query execution fails

        Example:
            >>> loader = IncrementalLoader(executor)
            >>> # Initial load
            >>> result = loader.fetch_incremental("logs", "created_at", limit=1000)
            >>> print(f"Loaded {result.row_count} rows (initial: {result.is_initial_load})")
            Loaded 1000 rows (initial: True)

            >>> # Incremental load
            >>> result2 = loader.fetch_incremental(
            ...     "logs", "created_at",
            ...     last_timestamp=result.max_timestamp,
            ...     limit=1000
            ... )
            >>> print(f"Loaded {result2.row_count} new rows")
            Loaded 50 new rows
        """
        is_initial_load = last_timestamp is None

        # Build incremental query
        query = QueryBuilder.build_incremental_query(
            table_name=table_name,
            time_column=time_column,
            last_timestamp=last_timestamp,
            limit=limit
        )

        try:
            # Execute query
            df = self.executor.fetch_to_dataframe(query)

            # Extract max timestamp from loaded data
            max_timestamp = None
            if not df.empty and time_column in df.columns:
                max_timestamp = df[time_column].max()

            row_count = len(df)

            if is_initial_load:
                self.logger.info(
                    f"Initial load: {row_count} rows from '{table_name}'"
                )
            else:
                self.logger.info(
                    f"Incremental load: {row_count} new rows from '{table_name}' "
                    f"since {last_timestamp}"
                )

            return IncrementalLoadResult(
                data=df,
                max_timestamp=max_timestamp,
                row_count=row_count,
                is_initial_load=is_initial_load
            )

        except QueryExecutionError as e:
            self.logger.error(f"Incremental load failed: {e}")
            raise

    def merge_with_existing(
        self,
        existing_df: Optional[pd.DataFrame],
        new_df: pd.DataFrame,
        time_column: str
    ) -> pd.DataFrame:
        """
        Merge existing DataFrame with newly loaded data.

        The merge operation:
        1. Concatenates the two DataFrames
        2. Sorts by timestamp column
        3. Resets the index

        Args:
            existing_df: Existing cached DataFrame (can be None or empty)
            new_df: Newly loaded DataFrame
            time_column: Name of the timestamp column for sorting

        Returns:
            Merged DataFrame sorted by time_column

        Example:
            >>> loader = IncrementalLoader(executor)
            >>> existing = pd.DataFrame({'id': [1, 2], 'ts': ['2024-01-01', '2024-01-02']})
            >>> new = pd.DataFrame({'id': [3], 'ts': ['2024-01-03']})
            >>> merged = loader.merge_with_existing(existing, new, 'ts')
            >>> print(len(merged))
            3
        """
        # Handle empty cases
        if existing_df is None or existing_df.empty:
            self.logger.info(f"No existing data, returning {len(new_df)} new rows")
            return new_df

        if new_df is None or new_df.empty:
            self.logger.info(f"No new data, returning {len(existing_df)} existing rows")
            return existing_df

        # Concatenate DataFrames
        merged_df = pd.concat([existing_df, new_df], ignore_index=True)

        # Sort by timestamp if column exists
        if time_column in merged_df.columns:
            merged_df = merged_df.sort_values(by=time_column).reset_index(drop=True)
            self.logger.info(
                f"Merged and sorted by '{time_column}': "
                f"{len(existing_df)} + {len(new_df)} = {len(merged_df)} rows"
            )
        else:
            self.logger.warning(
                f"Time column '{time_column}' not found in merged DataFrame. "
                f"Data will not be sorted."
            )

        return merged_df

    def deduplicate(
        self,
        df: pd.DataFrame,
        unique_columns: list[str],
        keep: str = 'last'
    ) -> pd.DataFrame:
        """
        Remove duplicate rows based on unique columns.

        This is useful when incremental loads might fetch overlapping data.

        Args:
            df: DataFrame to deduplicate
            unique_columns: List of column names that define uniqueness
            keep: Which duplicate to keep ('first', 'last', or False to drop all)

        Returns:
            Deduplicated DataFrame

        Example:
            >>> loader = IncrementalLoader(executor)
            >>> df = pd.DataFrame({
            ...     'id': [1, 2, 2, 3],
            ...     'value': [10, 20, 21, 30],
            ...     'ts': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04']
            ... })
            >>> deduped = loader.deduplicate(df, unique_columns=['id'], keep='last')
            >>> print(len(deduped))
            3
            >>> print(deduped[deduped['id'] == 2]['value'].values)
            [21]
        """
        original_count = len(df)

        # Remove duplicates
        deduped_df = df.drop_duplicates(subset=unique_columns, keep=keep)

        duplicates_removed = original_count - len(deduped_df)

        if duplicates_removed > 0:
            self.logger.info(
                f"Removed {duplicates_removed} duplicate rows "
                f"(based on {unique_columns}). "
                f"Remaining: {len(deduped_df)} rows"
            )
        else:
            self.logger.info("No duplicates found")

        return deduped_df
