"""
Tests for cached query functionality (simplified version).

This test module covers the caching behavior of query functions.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from oracle_duckdb_sync.data.query import (
    query_duckdb_table_cached,
    _cached_convert_dataframe,
    _fetch_raw_data
)


class TestFetchRawData:
    """Tests for _fetch_raw_data function."""

    def test_fetch_data_successfully(self):
        """Should fetch data and columns successfully."""
        mock_conn = Mock()

        # Mock execute for data fetch
        mock_execute_data = Mock()
        mock_execute_data.fetchall.return_value = [['val1', 'val2'], ['val3', 'val4']]

        # Mock execute for column names
        mock_execute_cols = Mock()
        mock_execute_cols.description = [('col1',), ('col2',)]

        mock_conn.execute.side_effect = [mock_execute_data, mock_execute_cols]

        result = _fetch_raw_data(mock_conn, "test_table", 100)

        assert result['success'] is True
        assert len(result['data']) == 2
        assert result['columns'] == ['col1', 'col2']

    def test_fetch_empty_table(self):
        """Should return error when table is empty."""
        mock_conn = Mock()
        mock_execute = Mock()
        mock_execute.fetchall.return_value = []
        mock_conn.execute.return_value = mock_execute

        result = _fetch_raw_data(mock_conn, "empty_table", 100)

        assert result['success'] is False
        assert result['error'] == 'No data returned'


class TestCachedConvertDataframe:
    """Tests for _cached_convert_dataframe function."""

    def test_convert_dataframe_successfully(self):
        """Should convert data to DataFrame with type conversion."""
        # Note: Caching removed from _cached_convert_dataframe
        # Caching is now handled by CacheProvider in application layer

        data = (('1', '2025-01-01'), ('2', '2025-01-02'))
        columns = ('number_str', 'date_str')

        result = _cached_convert_dataframe(data, columns, "test_table")

        assert result['success'] is True
        assert result['df_converted'] is not None
        assert len(result['df_converted']) == 2

    @pytest.mark.skip(reason="Caching removed from _cached_convert_dataframe - now handled by CacheProvider in application layer")
    def test_caching_works(self):
        """Should cache results and avoid redundant conversions."""
        # Note: This test is no longer relevant as caching has been moved
        # to the application layer (QueryService with CacheProvider)
        pass


@pytest.mark.skip(reason="query_duckdb_table_cached has Streamlit dependencies - use QueryService instead")
class TestQueryDuckDBTableCached:
    """Tests for query_duckdb_table_cached function."""

    @patch('oracle_duckdb_sync.data.query.st')
    @patch('oracle_duckdb_sync.data.query._cached_convert_dataframe')
    @patch('oracle_duckdb_sync.data.query._fetch_raw_data')
    def test_successful_query_and_conversion(self, mock_fetch, mock_convert, mock_st):
        """Should fetch data and convert types successfully."""
        mock_duckdb = Mock()

        # Mock fetch_raw_data
        mock_fetch.return_value = {
            'data': [['1', '2'], ['3', '4']],
            'columns': ['col1', 'col2'],
            'success': True,
            'error': None
        }

        # Mock _cached_convert_dataframe
        mock_convert.return_value = {
            'df_converted': pd.DataFrame({'col1': [1, 3], 'col2': [2, 4]}),
            'type_changes': {'col1': ('object', 'int64'), 'col2': ('object', 'int64')},
            'success': True,
            'error': None
        }

        result = query_duckdb_table_cached(mock_duckdb, "test_table", limit=100)

        assert result['success'] is True
        assert result['df_converted'] is not None
        assert len(result['df_converted']) == 2
        mock_st.success.assert_called()

    @patch('oracle_duckdb_sync.data.query.st')
    @patch('oracle_duckdb_sync.data.query._fetch_raw_data')
    def test_handles_fetch_failure(self, mock_fetch, mock_st):
        """Should handle fetch failure gracefully."""
        mock_duckdb = Mock()
        mock_duckdb.conn = Mock()
        mock_duckdb.conn.execute.return_value.fetchall.return_value = []

        mock_fetch.return_value = {
            'data': None,
            'columns': None,
            'success': False,
            'error': 'No data returned'
        }

        result = query_duckdb_table_cached(mock_duckdb, "empty_table", limit=100)

        assert result['success'] is False
        assert result['df_converted'] is None
        mock_st.warning.assert_called()

    @patch('oracle_duckdb_sync.data.query.st')
    @patch('oracle_duckdb_sync.data.query.detect_and_convert_types')
    @patch('oracle_duckdb_sync.data.query._fetch_raw_data')
    def test_handles_conversion_failure(self, mock_fetch, mock_convert, mock_st):
        """Should handle type conversion failure gracefully."""
        mock_duckdb = Mock()

        mock_fetch.return_value = {
            'data': [['1', '2']],
            'columns': ['col1', 'col2'],
            'success': True,
            'error': None
        }

        # Make detect_and_convert_types raise an exception
        mock_convert.side_effect = Exception('Conversion error')

        result = query_duckdb_table_cached(mock_duckdb, "test_table", limit=100)

        assert result['success'] is False
        assert result['df_converted'] is None
        mock_st.error.assert_called()
