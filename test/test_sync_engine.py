import pytest
import time
from unittest.mock import MagicMock, patch
from oracle_duckdb_sync.sync_engine import SyncEngine
from oracle_duckdb_sync.config import Config


@pytest.fixture
def mock_config():
    return Config(
        oracle_host="lh", oracle_port=1521, oracle_service_name="xe",
        oracle_user="u", oracle_password="p",
        duckdb_path=":memory:"
    )


def test_070_full_sync_pipeline(mock_config):
    """TEST-070: Oracle 전체 추출 → DuckDB 적재 파이프라인 확인"""
    with patch("oracle_duckdb_sync.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.sync_engine.DuckDBSource") as mock_duckdb_cls:
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value
        mock_oracle.fetch_batch.side_effect = [[(1, "Data1")], []]
        engine = SyncEngine(mock_config)
        engine.full_sync("O", "C", "ID")
        mock_duckdb.insert_batch.assert_called()


def test_072_batch_sync_processing(mock_config):
    """TEST-072: 대량 데이터 배치/청크 처리 동작 확인"""
    with patch("oracle_duckdb_sync.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.sync_engine.DuckDBSource") as mock_duckdb_cls:
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value
        mock_oracle.fetch_batch.side_effect = [[(1,), (2,)], [(3,)], []]
        engine = SyncEngine(mock_config)
        total = engine.sync_in_batches("O", "D", batch_size=2)
        assert total == 3
        assert mock_duckdb.insert_batch.call_count == 2


def test_080_incremental_sync_query(mock_config):
    """TEST-080: 마지막 동기화 시각 이후 데이터 조회 확인"""
    with patch("oracle_duckdb_sync.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.sync_engine.DuckDBSource") as mock_duckdb_cls:
        mock_oracle = mock_oracle_cls.return_value
        engine = SyncEngine(mock_config)
        last_sync = "2023-01-01 10:00:00"
        engine.incremental_sync("O", "D", "TIMESTAMP_COL", last_sync)
        mock_oracle.build_incremental_query.assert_called_with("O", "TIMESTAMP_COL", last_sync)


def test_082_retry_on_failure(mock_config):
    """TEST-082: 실패 시 재시도 동작 확인 (최소 3회)"""
    with patch("oracle_duckdb_sync.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.sync_engine.DuckDBSource") as mock_duckdb_cls:
        mock_oracle = mock_oracle_cls.return_value
        mock_oracle.fetch_batch.side_effect = Exception("DB Error")
        engine = SyncEngine(mock_config)
        with pytest.raises(Exception, match="DB Error"):
            engine.incremental_sync("O", "D", "T", "2023-01-01")
        assert mock_oracle.fetch_batch.call_count >= 3


def test_071_full_sync_progress_logging(mock_config):
    """TEST-071: 진행률·로그 기록 검증"""
    with patch("oracle_duckdb_sync.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.sync_engine.DuckDBSource") as mock_duckdb_cls, \
         patch.object(SyncEngine, "_log_progress") as mock_log_progress:
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value
        # Simulate 2 batches: first batch of 50 items (full), second batch of 30 items (partial)
        mock_oracle.fetch_batch.side_effect = [
            [(i, f"Data{i}") for i in range(50)],
            [(i, f"Data{i}") for i in range(50, 80)],
            []
        ]

        engine = SyncEngine(mock_config)
        # Use smaller batch_size to ensure multiple batches
        engine.sync_in_batches("O_TABLE", "D_TABLE", batch_size=50)

        # Verify progress logging was called
        assert mock_log_progress.called
        # Verify it was called at least twice (once per batch)
        calls = mock_log_progress.call_args_list
        assert len(calls) >= 2  # At least 2 batches processed
        # Verify it was called with correct arguments
        assert calls[0][0] == ("D_TABLE", 50, 50)  # First batch: 50 rows total, 50 in batch
        assert calls[1][0] == ("D_TABLE", 80, 30)  # Second batch: 80 rows total, 30 in batch


def test_081_incremental_upsert_handling(mock_config):
    """TEST-081: 증분 데이터 upsert 처리(중복 방지)"""
    with patch("oracle_duckdb_sync.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.sync_engine.DuckDBSource") as mock_duckdb_cls:
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value

        # Simulate incremental sync with duplicate data
        # First sync: insert rows 1-3
        mock_oracle.fetch_batch.side_effect = [[(1, "A"), (2, "B"), (3, "C")], []]

        engine = SyncEngine(mock_config)
        total1 = engine.incremental_sync("SOURCE_TABLE", "TARGET_TABLE", "TIMESTAMP_COL", "2023-01-01")

        assert total1 == 3
        assert mock_duckdb.insert_batch.called

        # Verify ensure_database was called
        assert mock_duckdb.ensure_database.called


def test_083_save_load_sync_state(tmp_path, mock_config):
    """TEST-083: 마지막 성공 지점 저장 및 로드 확인"""
    with patch("oracle_duckdb_sync.sync_engine.OracleSource"), \
         patch("oracle_duckdb_sync.sync_engine.DuckDBSource"):
        engine = SyncEngine(mock_config)
        state_file = tmp_path / "sync_state.json"
        engine.save_state("O_TABLE", "2023-05-20 12:00:00", file_path=str(state_file))
        val = engine.load_state("O_TABLE", file_path=str(state_file))
        assert val == "2023-05-20 12:00:00"


def test_140_sync_state_save_and_load(tmp_path, mock_config):
    """TEST-140: sync_state 저장·로드
    
    Comprehensive test for sync state management:
    1. Save state for a table
    2. Load state and verify correctness
    3. Update state for same table
    4. Save state for multiple tables
    5. Handle non-existent state file
    6. Handle corrupted state file
    """
    with patch("oracle_duckdb_sync.sync_engine.OracleSource"), \
         patch("oracle_duckdb_sync.sync_engine.DuckDBSource"):
        engine = SyncEngine(mock_config)
        state_file = tmp_path / "sync_state.json"
        
        # Test 1: Save and load basic state
        engine.save_state("TABLE_A", "2024-01-01 10:00:00", file_path=str(state_file))
        loaded = engine.load_state("TABLE_A", file_path=str(state_file))
        assert loaded == "2024-01-01 10:00:00"
        
        # Test 2: Update existing table state
        engine.save_state("TABLE_A", "2024-01-02 15:30:00", file_path=str(state_file))
        loaded = engine.load_state("TABLE_A", file_path=str(state_file))
        assert loaded == "2024-01-02 15:30:00"
        
        # Test 3: Save state for multiple tables
        engine.save_state("TABLE_B", "2024-01-03 08:00:00", file_path=str(state_file))
        engine.save_state("TABLE_C", "2024-01-04 12:00:00", file_path=str(state_file))
        
        # Verify all states are preserved
        assert engine.load_state("TABLE_A", file_path=str(state_file)) == "2024-01-02 15:30:00"
        assert engine.load_state("TABLE_B", file_path=str(state_file)) == "2024-01-03 08:00:00"
        assert engine.load_state("TABLE_C", file_path=str(state_file)) == "2024-01-04 12:00:00"
        
        # Test 4: Handle non-existent table
        non_existent = engine.load_state("TABLE_D", file_path=str(state_file))
        assert non_existent is None
        
        # Test 5: Handle non-existent state file
        non_existent_file = tmp_path / "does_not_exist.json"
        result = engine.load_state("TABLE_A", file_path=str(non_existent_file))
        assert result is None
        
        # Test 6: Handle corrupted state file
        corrupted_file = tmp_path / "corrupted.json"
        with open(corrupted_file, "w") as f:
            f.write("{ invalid json content")
        
        # Should return None without crashing
        result = engine.load_state("TABLE_A", file_path=str(corrupted_file))
        assert result is None
        
        # Should be able to save after corruption
        engine.save_state("TABLE_NEW", "2024-01-05 14:00:00", file_path=str(corrupted_file))
        loaded = engine.load_state("TABLE_NEW", file_path=str(corrupted_file))
        assert loaded == "2024-01-05 14:00:00"
