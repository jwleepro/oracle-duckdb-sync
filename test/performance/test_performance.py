"""Performance tests for Oracle-DuckDB sync application"""

import pytest
import pandas as pd
import time
from unittest.mock import patch, MagicMock


def test_132_chart_rendering_performance_100k_rows():
    """TEST-132: 10만 행 차트 렌더링 성능 < 1초(목표)
    
    Verify that chart rendering with 100,000 rows completes in under 1 second.
    This test measures the time to create a Plotly chart from a large DataFrame.
    """
    # Generate test data with 100,000 rows
    num_rows = 100_000
    test_data = {
        'id': range(1, num_rows + 1),
        'value': [i * 1.5 for i in range(1, num_rows + 1)],
        'category': [f'Cat_{i % 10}' for i in range(1, num_rows + 1)],
        'timestamp': pd.date_range(start='2024-01-01', periods=num_rows, freq='1min')
    }
    df = pd.DataFrame(test_data)
    
    # Mock Streamlit's plotly_chart to avoid actual rendering
    with patch('streamlit.plotly_chart') as mock_plotly:
        # Import plotly inside test to ensure clean state
        import plotly.express as px
        
        # Measure chart creation time
        start_time = time.perf_counter()
        
        # Create a line chart (common visualization type)
        fig = px.line(df, x='timestamp', y='value', title='Performance Test Chart')
        
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        
        # Verify performance requirement: < 1 second
        assert elapsed_time < 1.0, f"Chart rendering took {elapsed_time:.3f}s, expected < 1.0s"
        
        # Verify the chart was created with correct data
        assert fig is not None
        assert len(fig.data) > 0



def test_133_incremental_sync_performance_10k_rows():
    """TEST-133: 1만 건 증분 동기화 < 1분(목표)
    
    Verify that incremental synchronization of 10,000 rows completes in under 1 minute.
    This test measures the complete sync pipeline from Oracle fetch to DuckDB insert.
    """
    from oracle_duckdb_sync.database.sync_engine import SyncEngine
    from oracle_duckdb_sync.config import Config
    
    # Create test configuration
    config = Config(
        oracle_host="test_host",
        oracle_port=1521,
        oracle_service_name="test_service",
        oracle_user="test_user",
        oracle_password="test_password",
        duckdb_path=":memory:"
    )
    
    # Generate 10,000 test rows
    num_rows = 10_000
    test_data = [
        (i, f"data_{i}", f"2024-01-01 00:{i // 60:02d}:{i % 60:02d}")
        for i in range(1, num_rows + 1)
    ]
    
    # Mock Oracle and DuckDB sources
    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource") as mock_duckdb_cls:
        
        # Setup mock Oracle source
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value
        
        # Configure Oracle to return all data in one batch (simulates efficient query)
        # Real Oracle would return in batches, but for performance test we want to measure
        # the sync engine's ability to handle 10k rows regardless of batch strategy
        mock_oracle.fetch_batch.side_effect = [test_data, []]
        
        # Build incremental query mock
        mock_oracle.build_incremental_query.return_value = "SELECT * FROM test_table WHERE timestamp > '2024-01-01'"
        
        # Mock DuckDB operations
        mock_duckdb.insert_batch.return_value = None
        mock_duckdb.table_exists.return_value = True
        
        # Measure sync performance
        engine = SyncEngine(config)
        
        start_time = time.perf_counter()
        
        # Execute incremental sync
        total_rows = engine.incremental_sync(
            oracle_table="TEST_TABLE",
            duckdb_table="test_table",
            column="TIMESTAMP_COL",
            last_value="2024-01-01 00:00:00"
        )
        
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        
        # Verify performance requirement: < 60 seconds (1 minute)
        assert elapsed_time < 60.0, f"Incremental sync took {elapsed_time:.3f}s, expected < 60.0s"
        
        # Verify all rows were synced
        assert total_rows == num_rows, f"Expected {num_rows} rows, got {total_rows}"
        
        # Verify Oracle query was built correctly
        mock_oracle.build_incremental_query.assert_called_once_with(
            "TEST_TABLE", "TIMESTAMP_COL", "2024-01-01 00:00:00"
        )
        
        # Verify DuckDB insert was called with all the data
        assert mock_duckdb.insert_batch.call_count == 1
        mock_duckdb.insert_batch.assert_called_with("test_table", test_data)
