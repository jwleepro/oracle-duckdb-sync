import pytest
import logging
import os
from oracle_duckdb_sync.logger import setup_logger

def test_100_logger_initialization():
    """TEST-100: 로거 초기화 및 파일 기록 확인"""
    log_file = "test_sync.log"
    if os.path.exists(log_file):
        os.remove(log_file)
        
    logger = setup_logger("test_logger", log_file)
    logger.info("Test message")
    
    # 핸들러 닫기 (파일 읽기를 위해)
    for handler in logger.handlers:
        handler.close()
        
    assert os.path.exists(log_file)
    with open(log_file, "r") as f:
        content = f.read()
        assert "Test message" in content
    
    os.remove(log_file)

def test_101_stats_logging(tmp_path):
    """TEST-101: 처리 건수·지연 시간 통계 기록"""
    from unittest.mock import patch, MagicMock
    from oracle_duckdb_sync.sync_engine import SyncEngine
    from oracle_duckdb_sync.config import Config    

    log_file = tmp_path / "stats.log"

    mock_config = Config(
        oracle_host="lh", oracle_port=1521, oracle_service_name="xe",
        oracle_user="u", oracle_password="p",
        duckdb_path=":memory:"
    )

    with patch("oracle_duckdb_sync.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.sync_engine.DuckDBSource") as mock_duckdb_cls:
        mock_oracle = mock_oracle_cls.return_value
        mock_oracle.fetch_batch.side_effect = [[(i,) for i in range(100)], []]

        engine = SyncEngine(mock_config)
        engine.logger = setup_logger("sync_stats", str(log_file))

        # Execute sync
        total = engine.sync_in_batches("O_TABLE", "D_TABLE", batch_size=1000)

        # Close handlers to flush logs
        for handler in engine.logger.handlers:
            handler.close()

        # Verify log contains statistics
        assert log_file.exists()
        log_content = log_file.read_text()
        assert "100" in log_content  # Row count
        assert "rows" in log_content.lower() or "processed" in log_content.lower()
        # Should contain timing information
        assert any(word in log_content.lower() for word in ["time", "elapsed", "duration", "seconds"])

def test_102_logger_levels():
    """TEST-102: 로그 레벨 설정 확인"""
    logger = setup_logger("level_test", level=logging.ERROR)
    assert logger.level == logging.ERROR
