"""
Tests for data_query module.

This test module covers data query functionality including table counting
and full table querying.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from oracle_duckdb_sync.data_query import (
    get_table_row_count,
    query_duckdb_table
)


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
