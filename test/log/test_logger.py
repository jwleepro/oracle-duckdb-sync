import pytest
import logging
import os
from oracle_duckdb_sync.log.logger import setup_logger

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
    from oracle_duckdb_sync.database.sync_engine import SyncEngine
    from oracle_duckdb_sync.config import Config    

    log_file = tmp_path / "stats.log"

    mock_config = Config(
        oracle_host="lh", oracle_port=1521, oracle_service_name="xe",
        oracle_user="u", oracle_password="p",
        duckdb_path=":memory:"
    )

    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource") as mock_duckdb_cls:
        mock_oracle = mock_oracle_cls.return_value
        # Mock fetch_generator to yield one batch of 100 rows
        mock_oracle.fetch_generator.return_value = iter([[(i,) for i in range(100)]])

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


def test_103_batch_index_statistics(tmp_path):
    """TEST-103: 인덱스별 통계 수집 및 표시

    Verify that the sync engine collects and displays statistics for each batch:
    1. Batch number/index is logged
    2. Per-batch row counts are tracked
    3. Per-batch timing information is recorded
    4. Statistics are displayed in a clear, readable format
    """
    from unittest.mock import patch
    from oracle_duckdb_sync.database.sync_engine import SyncEngine
    from oracle_duckdb_sync.config import Config
    import re
    import logging

    log_file = tmp_path / "batch_stats.log"

    mock_config = Config(
        oracle_host="lh", oracle_port=1521, oracle_service_name="xe",
        oracle_user="u", oracle_password="p",
        duckdb_path=":memory:"
    )

    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource") as mock_duckdb_cls:

        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value

        # Simulate 3 batches of data
        mock_oracle.fetch_generator.return_value = iter([
            [(i, f"Data{i}") for i in range(50)],   # Batch 1: 50 rows
            [(i, f"Data{i}") for i in range(50)],   # Batch 2: 50 rows
            [(i, f"Data{i}") for i in range(30)]    # Batch 3: 30 rows
        ])

        engine = SyncEngine(mock_config)
        engine.logger = setup_logger("batch_stats", str(log_file))

        # Execute sync with small batch size to ensure multiple batches
        total = engine.sync_in_batches("ORACLE_TABLE", "DUCK_TABLE", batch_size=50)

        # Properly cleanup handlers to ensure logs are flushed
        for handler in engine.logger.handlers[:]:  # Copy list to avoid modification during iteration
            handler.flush()
            handler.close()
            engine.logger.removeHandler(handler)

        # Verify total count (3 batches: 50 + 50 + 30 = 130)
        assert total == 130

        # Verify log file exists and contains batch statistics
        assert log_file.exists()
        log_content = log_file.read_text(encoding='utf-8')

        # Verify batch-related logging with more specific patterns
        # Look for batch indicators or row counts in context
        assert re.search(r'(batch|rows?|processed)', log_content, re.IGNORECASE), \
            "Log should contain batch indicators or row processing keywords"

        # Verify per-batch row count statistics with contextual patterns
        # Should contain individual batch counts or cumulative totals in proper context
        # Use patterns that match row counts near relevant keywords, not standalone numbers
        assert re.search(r'(rows?|processed|batch|total).*?\b50\b', log_content, re.IGNORECASE) or \
               re.search(r'\b50\b.*?(rows?|processed|batch)', log_content, re.IGNORECASE), \
            "Log should contain '50' in context of batch processing (first batch count)"
        assert re.search(r'(rows?|processed|batch|total).*?\b100\b', log_content, re.IGNORECASE) or \
               re.search(r'\b100\b.*?(rows?|processed|batch)', log_content, re.IGNORECASE), \
            "Log should contain '100' in context of batch processing (cumulative after 2 batches)"
        assert re.search(r'(rows?|processed|batch|total).*?\b130\b', log_content, re.IGNORECASE) or \
               re.search(r'\b130\b.*?(rows?|processed|batch)', log_content, re.IGNORECASE), \
            "Log should contain '130' in context of batch processing (final total)"

        # Verify progress information is logged
        assert re.search(r'(progress|rows?|processed|total)', log_content, re.IGNORECASE), \
            "Log should contain progress-related keywords"

        # Verify timing information is present
        assert re.search(r'(time|seconds?|duration|elapsed)', log_content, re.IGNORECASE), \
            "Log should contain timing-related keywords"
