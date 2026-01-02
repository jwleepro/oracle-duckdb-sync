"""Tests for state rollback and restart capabilities on failure"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock
from oracle_duckdb_sync.database.sync_engine import SyncEngine
from oracle_duckdb_sync.config import Config


@pytest.fixture
def mock_config():
    return Config(
        oracle_host="localhost", 
        oracle_port=1521, 
        oracle_service_name="XE",
        oracle_user="test_user", 
        oracle_password="test_password",
        duckdb_path=":memory:"
    )


def test_142_state_rollback_on_failure_and_restart(tmp_path, mock_config):
    """TEST-142: 실패 시 상태 롤백·재시작 가능
    
    This test verifies that:
    1. State can be checkpointed before sync operation
    2. On failure, state can be rolled back to last checkpoint
    3. After rollback, sync can be restarted from checkpoint
    4. Partial progress is tracked during sync
    5. State is only committed after successful completion
    """
    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource") as mock_duckdb_cls:
        
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value
        
        engine = SyncEngine(mock_config)
        state_file = tmp_path / "sync_state.json"
        
        # Setup: Create initial checkpoint state
        initial_timestamp = "2024-01-01 00:00:00"
        engine.save_state("ORDERS", initial_timestamp, file_path=str(state_file))
        
        # Test 1: Create checkpoint before risky operation
        checkpoint = engine.create_state_checkpoint(file_path=str(state_file))
        
        assert checkpoint is not None
        assert "ORDERS" in checkpoint
        assert checkpoint["ORDERS"] == initial_timestamp
        
        # Test 2: Simulate sync that fails
        # Set up mock - will retry twice, so need to provide data for both attempts
        mock_oracle.fetch_batch.side_effect = [
            [(1, "Data1"), (2, "Data2")],  # Attempt 1 - Batch 1
            [(1, "Data1"), (2, "Data2")],  # Attempt 2 - Batch 1 (retry)
        ]
        
        # Make insert_batch always fail
        mock_duckdb.insert_batch.side_effect = Exception("Network error during sync")
        mock_duckdb.table_exists.return_value = True
        
        # Attempt sync and expect it to fail after all retries
        new_timestamp = "2024-01-05 10:00:00"
        
        with pytest.raises(Exception, match="Network error"):
            engine.incremental_sync(
                oracle_table_name="ORDERS",
                duckdb_table="orders",
                column="ORDER_DATE",
                last_value=new_timestamp,
                retries=2  # Will try 2 times
            )
        
        # Test 3: State should NOT be updated after failure
        current_state = engine.load_state("ORDERS", file_path=str(state_file))
        assert current_state == initial_timestamp, "State should not change on failure"
        
        # Test 4: Rollback to checkpoint
        rolled_back = engine.rollback_state(checkpoint, file_path=str(state_file))
        
        assert rolled_back is True
        reloaded_state = engine.load_state("ORDERS", file_path=str(state_file))
        assert reloaded_state == initial_timestamp
        
        # Test 5: Restart sync from checkpoint
        # Mock successful sync this time - need to simulate full batches
        mock_oracle.fetch_batch.side_effect = [
            [(i, f"Data{i}") for i in range(1, 10001)],  # Full batch of 10000
            [(10001, "Data10001"), (10002, "Data10002")],  # Partial batch of 2
            []  # End of data
        ]
        
        # Reset mock and make insert_batch succeed
        mock_duckdb.insert_batch.reset_mock()
        mock_duckdb.insert_batch.side_effect = None  # Remove the exception
        mock_duckdb.insert_batch.return_value = None  # Success
        
        # Retry sync from checkpoint
        retry_timestamp = "2024-01-05 10:00:00"
        total_rows = engine.incremental_sync(
            oracle_table_name="ORDERS",
            duckdb_table="orders",
            column="ORDER_DATE",
            last_value=retry_timestamp,
            retries=1
        )
        
        assert total_rows == 10002  # 10000 + 2
        assert mock_duckdb.insert_batch.call_count == 2
        
        # Test 6: Commit state after successful completion
        success_timestamp = "2024-01-05 10:00:00"
        engine.save_state("ORDERS", success_timestamp, file_path=str(state_file))
        
        final_state = engine.load_state("ORDERS", file_path=str(state_file))
        assert final_state == success_timestamp
        
        # Test 7: Test checkpoint with multiple tables
        engine.save_state("CUSTOMERS", "2024-01-03 12:00:00", file_path=str(state_file))
        engine.save_state("PRODUCTS", "2024-01-04 08:00:00", file_path=str(state_file))
        
        multi_checkpoint = engine.create_state_checkpoint(file_path=str(state_file))
        
        assert len(multi_checkpoint) == 3
        assert "ORDERS" in multi_checkpoint
        assert "CUSTOMERS" in multi_checkpoint
        assert "PRODUCTS" in multi_checkpoint
        
        # Modify states
        engine.save_state("CUSTOMERS", "2024-01-10 00:00:00", file_path=str(state_file))
        
        # Rollback should restore all tables
        engine.rollback_state(multi_checkpoint, file_path=str(state_file))
        
        assert engine.load_state("CUSTOMERS", file_path=str(state_file)) == "2024-01-03 12:00:00"
        assert engine.load_state("ORDERS", file_path=str(state_file)) == success_timestamp
        assert engine.load_state("PRODUCTS", file_path=str(state_file)) == "2024-01-04 08:00:00"


def test_142_partial_progress_tracking(tmp_path, mock_config):
    """Additional test for tracking partial progress during sync"""
    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource") as mock_duckdb_cls:
        
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value
        
        engine = SyncEngine(mock_config)
        progress_file = tmp_path / "sync_progress.json"
        
        # Test saving partial progress
        engine.save_partial_progress(
            table_name="ORDERS",
            rows_processed=5000,
            last_row_id=5000,
            file_path=str(progress_file)
        )
        
        # Test loading partial progress
        progress = engine.load_partial_progress(
            table_name="ORDERS",
            file_path=str(progress_file)
        )
        
        assert progress is not None
        assert progress["rows_processed"] == 5000
        assert progress["last_row_id"] == 5000
        
        # Test clearing partial progress after success
        engine.clear_partial_progress(
            table_name="ORDERS",
            file_path=str(progress_file)
        )
        
        cleared = engine.load_partial_progress(
            table_name="ORDERS",
            file_path=str(progress_file)
        )
        
        assert cleared is None
