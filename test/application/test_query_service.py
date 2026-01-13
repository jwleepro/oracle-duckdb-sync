"""
Test QueryService implementation.

This module tests the UI-independent QueryService layer.
"""

from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from oracle_duckdb_sync.application.query_service import QueryResult, QueryService


class TestQueryResult:
    """Test QueryResult class."""

    def test_query_result_success(self):
        """Test successful query result."""
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = QueryResult(
            success=True,
            data=df,
            metadata={'row_count': 3}
        )

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 3
        assert result.metadata['row_count'] == 3

    def test_query_result_failure(self):
        """Test failed query result."""
        result = QueryResult(
            success=False,
            error="Table not found"
        )

        assert result.success is False
        assert result.data is None
        assert result.error == "Table not found"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = QueryResult(
            success=True,
            data=df,
            metadata={'row_count': 3, 'table_name': 'test'}
        )

        result_dict = result.to_dict()

        assert result_dict['success'] is True
        assert result_dict['df_converted'] is not None
        assert result_dict['row_count'] == 3
        assert result_dict['table_name'] == 'test'


class TestQueryService:
    """Test QueryService class."""

    @pytest.fixture
    def mock_duckdb(self):
        """Create mock DuckDB source."""
        mock = Mock()
        mock_conn = MagicMock()
        mock.get_connection.return_value = mock_conn
        return mock, mock_conn

    def test_get_available_tables(self, mock_duckdb):
        """Test getting available tables."""
        mock_source, mock_conn = mock_duckdb

        # Mock SHOW TABLES result
        mock_conn.execute.return_value.fetchall.return_value = [
            ('table1',),
            ('table2',),
            ('table3',)
        ]

        service = QueryService(mock_source)
        tables = service.get_available_tables()

        assert len(tables) == 3
        assert 'table1' in tables
        assert 'table2' in tables
        assert 'table3' in tables

    def test_get_table_row_count(self, mock_duckdb):
        """Test getting table row count."""
        mock_source, mock_conn = mock_duckdb

        # Mock COUNT(*) result
        mock_conn.execute.return_value.fetchone.return_value = (100,)

        service = QueryService(mock_source)
        count = service.get_table_row_count('test_table')

        assert count == 100

    @patch('oracle_duckdb_sync.application.query_service.detect_and_convert_types')
    def test_query_table_success(self, mock_convert, mock_duckdb):
        """Test successful table query."""
        mock_source, mock_conn = mock_duckdb

        # Mock query result
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie']
        })
        mock_conn.execute.return_value.df.return_value = df

        # Mock type conversion to return same data
        mock_convert.return_value = (df, {})

        service = QueryService(mock_source)
        result = service.query_table('test_table', limit=100)

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 3
        assert result.metadata['row_count'] == 3
        assert result.metadata['table_name'] == 'test_table'

    def test_query_table_empty(self, mock_duckdb):
        """Test query with no results."""
        mock_source, mock_conn = mock_duckdb

        # Mock empty result
        mock_conn.execute.return_value.df.return_value = pd.DataFrame()

        service = QueryService(mock_source)
        result = service.query_table('empty_table')

        assert result.success is False
        assert result.error is not None
        assert "No data found" in result.error

    def test_query_table_error(self, mock_duckdb):
        """Test query with error."""
        mock_source, mock_conn = mock_duckdb

        # Mock error
        mock_conn.execute.side_effect = Exception("Connection failed")

        service = QueryService(mock_source)
        result = service.query_table('test_table')

        assert result.success is False
        assert result.error == "Connection failed"

    @patch('oracle_duckdb_sync.application.query_service.detect_and_convert_types')
    def test_query_table_with_conversion(self, mock_convert, mock_duckdb):
        """Test query with type conversion."""
        mock_source, mock_conn = mock_duckdb

        # Mock raw data
        df_raw = pd.DataFrame({
            'id': ['1', '2', '3'],
            'value': ['10.5', '20.3', '30.1']
        })
        mock_conn.execute.return_value.df.return_value = df_raw

        # Mock conversion
        df_converted = pd.DataFrame({
            'id': [1, 2, 3],
            'value': [10.5, 20.3, 30.1]
        })
        mock_convert.return_value = (df_converted, {'id': 'int', 'value': 'float'})

        service = QueryService(mock_source)
        result = service.query_table('test_table', convert_types=True)

        assert result.success is True
        assert result.metadata['conversions'] == {'id': 'int', 'value': 'float'}
        mock_convert.assert_called_once()


class TestQueryServiceAggregation:
    """Test QueryService aggregation methods."""

    @pytest.fixture
    def mock_duckdb(self):
        """Create mock DuckDB source."""
        mock = Mock()
        mock_conn = MagicMock()
        mock.get_connection.return_value = mock_conn
        return mock, mock_conn

    def test_query_table_aggregated_legacy_success(self, mock_duckdb):
        """Test successful aggregated query with legacy interface."""
        mock_source, mock_conn = mock_duckdb

        # Mock sample data for column detection
        sample_df = pd.DataFrame({
            'time': ['20260101120000', '20260101120100'],
            'value1': [10.5, 20.3],
            'value2': [100, 200]
        })

        # Mock aggregated result
        agg_df = pd.DataFrame({
            'time_bucket': pd.date_range('2026-01-01', periods=5, freq='10min'),
            'value1_avg': [15.0, 18.0, 22.0, 25.0, 30.0],
            'value1_max': [20.0, 25.0, 30.0, 35.0, 40.0],
            'value1_min': [10.0, 12.0, 15.0, 18.0, 20.0]
        })

        # Setup mock to return different results for different queries
        def execute_side_effect(query):
            mock_result = MagicMock()
            if 'LIMIT 0' in query:
                mock_result.description = [('time',), ('value1',), ('value2',)]
                return mock_result
            elif 'LIMIT 1000' in query or 'LIMIT 100' in query:
                mock_result.fetchdf.return_value = sample_df
                return mock_result
            else:  # Aggregation query
                mock_result.fetchdf.return_value = agg_df
                return mock_result

        mock_conn.execute.side_effect = execute_side_effect

        service = QueryService(mock_source)
        result = service.query_table_aggregated_legacy(
            table_name='test_table',
            time_column='time',
            interval='10 minutes'
        )

        assert result['success'] is True
        assert result['df_aggregated'] is not None
        assert len(result['df_aggregated']) == 5
        assert result['interval'] == '10 minutes'
        assert 'numeric_cols' in result

    def test_query_table_aggregated_legacy_no_numeric_cols(self, mock_duckdb):
        """Test aggregated query with no numeric columns."""
        mock_source, mock_conn = mock_duckdb

        # Mock sample data with no numeric columns
        sample_df = pd.DataFrame({
            'time': ['20260101120000', '20260101120100'],
            'name': ['Alice', 'Bob']
        })

        def execute_side_effect(query):
            mock_result = MagicMock()
            if 'LIMIT 0' in query:
                mock_result.description = [('time',), ('name',)]
                return mock_result
            else:
                mock_result.fetchdf.return_value = sample_df
                return mock_result

        mock_conn.execute.side_effect = execute_side_effect

        service = QueryService(mock_source)
        result = service.query_table_aggregated_legacy(
            table_name='test_table',
            time_column='time'
        )

        assert result['success'] is False
        assert 'No numeric columns' in result['error']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
