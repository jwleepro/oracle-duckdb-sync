"""
SQL query builder for DuckDB queries.

This module provides a clean interface for building SQL query strings
without executing them. Separation of query construction from execution
improves testability and maintainability.
"""

from typing import Optional


class QueryBuilder:
    """
    Builds SQL query strings for DuckDB operations.

    This class is stateless and all methods are static. It focuses solely
    on constructing syntactically correct SQL query strings.
    """

    @staticmethod
    def build_select_query(
        table_name: str,
        limit: Optional[int] = None,
        columns: Optional[list[str]] = None
    ) -> str:
        """
        Build a basic SELECT query.

        Args:
            table_name: Name of the table to query
            limit: Optional row limit
            columns: Optional list of column names. If None, selects all columns (*)

        Returns:
            SQL query string

        Example:
            >>> QueryBuilder.build_select_query("users", limit=100)
            'SELECT * FROM users LIMIT 100'

            >>> QueryBuilder.build_select_query("users", columns=["id", "name"])
            'SELECT id, name FROM users'
        """
        # Build column list
        column_str = "*" if columns is None else ", ".join(columns)

        # Build base query
        query = f"SELECT {column_str} FROM {table_name}"

        # Add LIMIT if specified
        if limit is not None:
            query += f" LIMIT {limit}"

        return query

    @staticmethod
    def build_incremental_query(
        table_name: str,
        time_column: str,
        last_timestamp: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """
        Build a query for incremental data loading based on timestamp.

        Args:
            table_name: Name of the table to query
            time_column: Name of the timestamp column for ordering
            last_timestamp: Last timestamp from previous query.
                           If None, fetches from beginning
            limit: Optional row limit

        Returns:
            SQL query string with WHERE clause (if last_timestamp provided)
            and ORDER BY clause

        Example:
            >>> QueryBuilder.build_incremental_query("logs", "created_at")
            'SELECT * FROM logs ORDER BY created_at'

            >>> QueryBuilder.build_incremental_query(
            ...     "logs", "created_at",
            ...     last_timestamp="2024-01-01 00:00:00",
            ...     limit=1000
            ... )
            "SELECT * FROM logs WHERE created_at > '2024-01-01 00:00:00' ORDER BY created_at LIMIT 1000"
        """
        # Build base query
        query = f"SELECT * FROM {table_name}"

        # Add WHERE clause if last_timestamp is provided
        if last_timestamp is not None:
            query += f" WHERE {time_column} > '{last_timestamp}'"

        # Always add ORDER BY for incremental loading
        query += f" ORDER BY {time_column}"

        # Add LIMIT if specified
        if limit is not None:
            query += f" LIMIT {limit}"

        return query

    @staticmethod
    def build_aggregation_query(
        table_name: str,
        time_column: str,
        numeric_columns: list[str],
        interval: str = '10 minutes'
    ) -> str:
        """
        Build a time-bucket aggregation query for fast data overview.

        Args:
            table_name: Name of the table to query
            time_column: Name of the timestamp column for bucketing
            numeric_columns: List of numeric column names to aggregate
            interval: Time interval for bucketing (e.g., '10 minutes', '1 hour')

        Returns:
            SQL query string with time_bucket and aggregation functions

        Example:
            >>> QueryBuilder.build_aggregation_query(
            ...     "metrics", "timestamp",
            ...     ["cpu_usage", "memory_usage"],
            ...     interval="5 minutes"
            ... )
            "SELECT time_bucket(INTERVAL '5 minutes', timestamp) as time_bucket, AVG(cpu_usage) as cpu_usage_avg, AVG(memory_usage) as memory_usage_avg FROM metrics GROUP BY time_bucket ORDER BY time_bucket"
        """
        # Build aggregation columns
        agg_columns = [
            f"AVG({col}) as {col}_avg"
            for col in numeric_columns
        ]

        # Combine time bucket with aggregations
        select_columns = [
            f"time_bucket(INTERVAL '{interval}', {time_column}) as time_bucket"
        ] + agg_columns

        # Build complete query
        query = (
            f"SELECT {', '.join(select_columns)} "
            f"FROM {table_name} "
            f"GROUP BY time_bucket "
            f"ORDER BY time_bucket"
        )

        return query

    @staticmethod
    def build_count_query(table_name: str) -> str:
        """
        Build a simple COUNT(*) query.

        Args:
            table_name: Name of the table to count

        Returns:
            SQL query string

        Example:
            >>> QueryBuilder.build_count_query("users")
            'SELECT COUNT(*) FROM users'
        """
        return f"SELECT COUNT(*) FROM {table_name}"

    @staticmethod
    def build_column_names_query(table_name: str) -> str:
        """
        Build a query to retrieve column names (returns 0 rows).

        Args:
            table_name: Name of the table

        Returns:
            SQL query string that returns column metadata only

        Example:
            >>> QueryBuilder.build_column_names_query("users")
            'SELECT * FROM users LIMIT 0'
        """
        return f"SELECT * FROM {table_name} LIMIT 0"
