"""
Tests for data_query module.

This test module covers data query functionality including table counting
and full table querying.
"""

from unittest.mock import Mock

import pandas as pd

from oracle_duckdb_sync.data.query import get_table_row_count, query_duckdb_table_aggregated


class TestGetTableRowCount:
    """Tests for get_table_row_count function."""

    def test_get_row_count_for_existing_table(self):
        """Should return correct row count for existing table."""
        # Mock DuckDBSource
        mock_duckdb = Mock()
        mock_duckdb.execute.return_value = [[1000]]

        row_count = get_table_row_count(mock_duckdb, "test_table")

        assert row_count == 1000
        mock_duckdb.execute.assert_called_once_with("SELECT COUNT(*) FROM test_table")

    def test_get_row_count_for_empty_table(self):
        """Should return 0 for empty table."""
        mock_duckdb = Mock()
        mock_duckdb.execute.return_value = [[0]]

        row_count = get_table_row_count(mock_duckdb, "empty_table")

        assert row_count == 0

    def test_get_row_count_with_no_result(self):
        """Should return 0 when execute returns None or empty list."""
        mock_duckdb = Mock()
        mock_duckdb.execute.return_value = None

        row_count = get_table_row_count(mock_duckdb, "test_table")

        assert row_count == 0

    def test_get_row_count_with_exception(self):
        """Should return 0 and log error when exception occurs."""
        mock_duckdb = Mock()
        mock_duckdb.execute.side_effect = Exception("Table not found")

        row_count = get_table_row_count(mock_duckdb, "nonexistent_table")

        assert row_count == 0

    def test_get_row_count_for_large_table(self):
        """Should handle large row counts correctly."""
        mock_duckdb = Mock()
        mock_duckdb.execute.return_value = [[1000000]]

        row_count = get_table_row_count(mock_duckdb, "large_table")

        assert row_count == 1000000


class TestQueryDuckDBTableAggregated:
    """Tests for query_duckdb_table_aggregated function."""

    def test_aggregated_query_with_valid_timestamp_column(self):
        """Should successfully aggregate data with valid timestamp column and format."""
        # Mock DuckDBSource with proper behavior
        mock_duckdb = Mock()

        # Mock SELECT * FROM table LIMIT 0 to get column names
        mock_result = Mock()
        mock_result.description = [('time_col',), ('value_col',)]

        # Mock sample data fetch
        sample_df = pd.DataFrame({
            'time_col': ['20240101120000', '20240101120000', '20240101130000'],
            'value_col': [100, 200, 150]
        })

        # Mock aggregated result
        agg_df = pd.DataFrame({
            'time_bucket': pd.to_datetime(['2024-01-01 12:00:00', '2024-01-01 13:00:00']),
            'value_col_avg': [150.0, 150.0],
            'value_col_max': [200, 150],
            'value_col_min': [100, 150]
        })

        # Set up mock chain for execute calls
        mock_duckdb.conn.execute.side_effect = [
            mock_result,  # For SELECT * FROM table LIMIT 0
            Mock(fetchdf=Mock(return_value=sample_df)),  # For SELECT * FROM table LIMIT 1000
            Mock(fetchdf=Mock(return_value=agg_df))  # For aggregation query
        ]

        result = query_duckdb_table_aggregated(
            mock_duckdb,
            'test_table',
            'time_col',
            interval='10 minutes'
        )

        assert result['success'] is True
        assert result['error'] is None
        assert len(result['df_aggregated']) == 2
        assert result['interval'] == '10 minutes'

    def test_aggregated_query_with_no_numeric_columns(self):
        """Should return error when no numeric columns found for aggregation."""
        mock_duckdb = Mock()

        # Mock SELECT * FROM table LIMIT 0 to get column names
        mock_result = Mock()
        mock_result.description = [('time_col',), ('text_col',)]

        # Mock sample data with no numeric columns
        sample_df = pd.DataFrame({
            'time_col': ['20240101120000', '20240101120000'],
            'text_col': ['a', 'b']
        })

        mock_duckdb.conn.execute.side_effect = [
            mock_result,  # For SELECT * FROM table LIMIT 0
            Mock(fetchdf=Mock(return_value=sample_df))  # For SELECT * FROM table LIMIT 1000
        ]

        result = query_duckdb_table_aggregated(
            mock_duckdb,
            'test_table',
            'time_col',
            interval='10 minutes'
        )

        assert result['success'] is False
        assert 'No numeric columns found' in result['error']

    def test_aggregated_query_with_empty_result(self):
        """Should return error when aggregation returns no data."""
        mock_duckdb = Mock()

        # Mock SELECT * FROM table LIMIT 0
        mock_result = Mock()
        mock_result.description = [('time_col',), ('value_col',)]

        # Mock sample data
        sample_df = pd.DataFrame({
            'time_col': ['20240101120000'],
            'value_col': [100]
        })

        # Mock empty aggregation result
        agg_df = pd.DataFrame()

        mock_duckdb.conn.execute.side_effect = [
            mock_result,  # For SELECT * FROM table LIMIT 0
            Mock(fetchdf=Mock(return_value=sample_df)),  # For SELECT * FROM table LIMIT 1000
            Mock(fetchdf=Mock(return_value=agg_df))  # For aggregation query (empty)
        ]

        result = query_duckdb_table_aggregated(
            mock_duckdb,
            'test_table',
            'time_col',
            interval='10 minutes'
        )

        assert result['success'] is False
        assert 'No data returned' in result['error']

    def test_aggregated_query_exception_handling(self):
        """Should handle exceptions gracefully and return error."""
        mock_duckdb = Mock()

        # Mock SELECT * FROM table LIMIT 0
        mock_result = Mock()
        mock_result.description = [('time_col',), ('value_col',)]

        # Mock sample data
        sample_df = pd.DataFrame({
            'time_col': ['20240101120000'],
            'value_col': [100]
        })

        # Mock exception on aggregation query
        mock_duckdb.conn.execute.side_effect = [
            mock_result,  # For SELECT * FROM table LIMIT 0
            Mock(fetchdf=Mock(return_value=sample_df)),  # For SELECT * FROM table LIMIT 1000
            Exception("Binder Error: Something went wrong")  # For aggregation query
        ]

        result = query_duckdb_table_aggregated(
            mock_duckdb,
            'test_table',
            'time_col',
            interval='10 minutes'
        )

        assert result['success'] is False
        assert 'error' in result
        assert result['df_aggregated'] is None
