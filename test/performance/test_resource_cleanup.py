import time
from unittest.mock import MagicMock, patch

import pytest

from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.sync_engine import SyncEngine


@pytest.fixture
def mock_config():
    return Config(
        oracle_host="lh", oracle_port=1521, oracle_service_name="xe",
        oracle_user="u", oracle_password="p",
        duckdb_path=":memory:"
    )


def test_sync_engine_max_iterations():
    """Verify sync terminates after max iterations to prevent infinite loops"""
    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource"):
        mock_oracle = mock_oracle_cls.return_value

        # Simulate infinite loop: always yield a batch
        def infinite_generator(*args, **kwargs):
            while True:
                yield [(i, f"data{i}") for i in range(10)]

        mock_oracle.fetch_generator.side_effect = infinite_generator

        config = Config(
            oracle_host="lh", oracle_port=1521, oracle_service_name="xe",
            oracle_user="u", oracle_password="p",
            duckdb_path=":memory:"
        )

        engine = SyncEngine(config)

        # Should raise RuntimeError after max iterations
        with pytest.raises(RuntimeError, match="Exceeded maximum iterations"):
            engine.sync_in_batches("O_TABLE", "D_TABLE", batch_size=1000)


def test_sync_engine_timeout():
    """Verify sync terminates after max duration"""
    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource"):
        mock_oracle = mock_oracle_cls.return_value

        # Simulate slow operation that exceeds timeout
        def slow_generator(*args, **kwargs):
            while True:
                time.sleep(0.2)
                yield [(i, f"data{i}") for i in range(10)]

        mock_oracle.fetch_generator.side_effect = slow_generator

        config = Config(
            oracle_host="lh", oracle_port=1521, oracle_service_name="xe",
            oracle_user="u", oracle_password="p",
            duckdb_path=":memory:"
        )

        engine = SyncEngine(config)

        # Should raise TimeoutError after max duration
        # Set very short timeout for testing (1 second)
        with pytest.raises(TimeoutError, match="Sync exceeded maximum duration"):
            engine.sync_in_batches("O_TABLE", "D_TABLE", batch_size=1000, max_duration=1)


def test_duckdb_connection_cleanup():
    """Verify DuckDB connection is closed properly"""
    from oracle_duckdb_sync.config import Config
    from oracle_duckdb_sync.database.duckdb_source import DuckDBSource

    with patch("oracle_duckdb_sync.database.duckdb_source.duckdb") as mock_duckdb:
        mock_conn = mock_duckdb.connect.return_value

        config = Config(
            oracle_host="lh", oracle_port=1521, oracle_service_name="xe",
            oracle_user="u", oracle_password="p",
            duckdb_path=":memory:"
        )

        # Test context manager
        with DuckDBSource(config) as source:
            source.ping()

        # Verify close was called
        mock_conn.close.assert_called_once()


def test_oracle_cursor_cleanup_on_exception():
    """Verify cursor is closed even when execute() fails"""
    from oracle_duckdb_sync.config import Config
    from oracle_duckdb_sync.database.oracle_source import OracleSource

    with patch("oracledb.connect") as mock_connect:
        mock_conn = mock_connect.return_value
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Make execute() raise an exception
        mock_cursor.execute.side_effect = Exception("SQL Error")

        config = Config(
            oracle_host="lh", oracle_port=1521, oracle_service_name="xe",
            oracle_user="u", oracle_password="p",
            duckdb_path=":memory:"
        )

        source = OracleSource(config)
        source.connect()

        # Try to fetch batch with a query that will fail
        with pytest.raises(Exception, match="SQL Error"):
            source.fetch_batch("SELECT * FROM bad_table")

        # Verify cursor was closed even though execute() failed
        mock_cursor.close.assert_called()


def test_logger_handler_cleanup():
    """Verify file handlers are closed and not accumulated"""
    import os
    import tempfile

    from oracle_duckdb_sync.log.logger import cleanup_logger, setup_logger

    # Use temporary file for test
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as tmp:
        log_file = tmp.name

    try:
        # Create logger multiple times
        logger1 = setup_logger("test_logger", log_file=log_file)
        initial_handler_count = len(logger1.handlers)

        # Create same logger again - should not accumulate handlers
        logger2 = setup_logger("test_logger", log_file=log_file)
        second_handler_count = len(logger2.handlers)

        # Handler count should be same, not doubled
        assert second_handler_count == initial_handler_count, \
            f"Handlers accumulated: {initial_handler_count} -> {second_handler_count}"

        # Clean up logger
        cleanup_logger(logger2)

        # After cleanup, no handlers should remain
        assert len(logger2.handlers) == 0, "Handlers not cleaned up"

    finally:
        # Clean up temp file
        if os.path.exists(log_file):
            os.remove(log_file)
