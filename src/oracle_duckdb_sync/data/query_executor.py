"""
Query executor for DuckDB operations.

This module handles the execution of SQL queries and conversion of results
to DataFrames. It separates query execution from query building.
"""

import pandas as pd
from typing import Optional

from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger


# Set up logger
executor_logger = setup_logger('QueryExecutor')


class QueryExecutionError(Exception):
    """Exception raised when query execution fails."""
    pass


class QueryExecutor:
    """
    Executes SQL queries against DuckDB and returns results.

    This class handles:
    - Query execution
    - Result conversion to DataFrames
    - Column metadata extraction
    - Error handling and logging
    """

    def __init__(self, duckdb_source: DuckDBSource):
        """
        Initialize QueryExecutor with a DuckDB source.

        Args:
            duckdb_source: DuckDBSource instance for database connection
        """
        self.duckdb = duckdb_source
        self.logger = executor_logger

    def fetch_to_dataframe(self, query: str) -> pd.DataFrame:
        """
        Execute a query and return results as a pandas DataFrame.

        Args:
            query: SQL query string to execute

        Returns:
            pandas DataFrame with query results

        Raises:
            QueryExecutionError: If query execution fails or returns no data

        Example:
            >>> executor = QueryExecutor(duckdb_source)
            >>> df = executor.fetch_to_dataframe("SELECT * FROM users LIMIT 10")
            >>> print(df.shape)
            (10, 5)
        """
        try:
            self.logger.info(f"Executing query: {query}")

            # Execute query using DuckDB connection
            data = self.duckdb.conn.execute(query).fetchall()

            if not data or len(data) == 0:
                self.logger.warning(f"Query returned no data: {query}")
                # Return empty DataFrame with correct columns
                columns = self._extract_column_names_from_query(query)
                return pd.DataFrame(columns=columns)

            # Get column names
            columns = self._extract_column_names_from_query(query)

            # Convert to DataFrame
            df = pd.DataFrame(data, columns=columns)
            self.logger.info(f"Query successful: {len(df)} rows, {len(df.columns)} columns")

            return df

        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            import traceback
            self.logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise QueryExecutionError(f"Failed to execute query: {e}") from e

    def get_column_names(self, table_name: str) -> list[str]:
        """
        Get column names for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of column names

        Raises:
            QueryExecutionError: If column extraction fails

        Example:
            >>> executor = QueryExecutor(duckdb_source)
            >>> columns = executor.get_column_names("users")
            >>> print(columns)
            ['id', 'username', 'email', 'created_at']
        """
        try:
            # Execute LIMIT 0 query to get column metadata only
            query = f"SELECT * FROM {table_name} LIMIT 0"
            result = self.duckdb.conn.execute(query)

            # Extract column names from description
            columns = [desc[0] for desc in result.description]

            self.logger.info(f"Extracted {len(columns)} columns from table '{table_name}'")
            return columns

        except Exception as e:
            self.logger.error(f"Failed to get column names for table '{table_name}': {e}")
            raise QueryExecutionError(f"Failed to get column names: {e}") from e

    def execute_raw(self, query: str) -> tuple[list[tuple], list[str]]:
        """
        Execute a query and return raw data without DataFrame conversion.

        This is useful for scenarios where DataFrame conversion is not needed,
        or when you want to handle the data manually.

        Args:
            query: SQL query string to execute

        Returns:
            Tuple of (data rows, column names)
            - data rows: List of tuples, each representing a row
            - column names: List of column name strings

        Raises:
            QueryExecutionError: If query execution fails

        Example:
            >>> executor = QueryExecutor(duckdb_source)
            >>> rows, columns = executor.execute_raw("SELECT id, name FROM users LIMIT 5")
            >>> print(rows)
            [(1, 'Alice'), (2, 'Bob'), ...]
            >>> print(columns)
            ['id', 'name']
        """
        try:
            self.logger.info(f"Executing raw query: {query}")

            # Execute query
            result = self.duckdb.conn.execute(query)
            data = result.fetchall()

            # Extract column names
            columns = [desc[0] for desc in result.description]

            self.logger.info(f"Raw query successful: {len(data)} rows")
            return data, columns

        except Exception as e:
            self.logger.error(f"Raw query execution failed: {e}")
            raise QueryExecutionError(f"Failed to execute raw query: {e}") from e

    def get_row_count(self, table_name: str) -> int:
        """
        Get total row count for a table.

        Args:
            table_name: Name of the table to count

        Returns:
            Total number of rows in the table

        Raises:
            QueryExecutionError: If count query fails

        Example:
            >>> executor = QueryExecutor(duckdb_source)
            >>> count = executor.get_row_count("users")
            >>> print(f"Total users: {count}")
            Total users: 1234
        """
        try:
            query = f"SELECT COUNT(*) FROM {table_name}"
            result = self.duckdb.execute(query)

            if result and len(result) > 0:
                count = result[0][0]
                self.logger.info(f"Table '{table_name}' has {count} rows")
                return count
            else:
                return 0

        except Exception as e:
            self.logger.error(f"Failed to count rows in table '{table_name}': {e}")
            raise QueryExecutionError(f"Failed to count rows: {e}") from e

    def _extract_column_names_from_query(self, query: str) -> list[str]:
        """
        Extract column names by executing a LIMIT 0 version of the query.

        This is an internal helper method that modifies the query to fetch
        only column metadata.

        Args:
            query: Original SQL query

        Returns:
            List of column names

        Raises:
            QueryExecutionError: If extraction fails
        """
        try:
            # Remove existing LIMIT clause if present, then add LIMIT 0
            # This is a simple approach; more robust parsing could be added
            if "LIMIT" in query.upper():
                # Replace existing LIMIT with LIMIT 0
                import re
                query_no_limit = re.sub(r'\s+LIMIT\s+\d+', '', query, flags=re.IGNORECASE)
                metadata_query = f"{query_no_limit} LIMIT 0"
            else:
                metadata_query = f"{query} LIMIT 0"

            result = self.duckdb.conn.execute(metadata_query)
            return [desc[0] for desc in result.description]

        except Exception as e:
            self.logger.error(f"Failed to extract column names from query: {e}")
            raise QueryExecutionError(f"Failed to extract column names: {e}") from e
