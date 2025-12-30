import pytest
from unittest.mock import MagicMock, patch
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.config import Config


@pytest.fixture
def mock_config():
    return Config(
        oracle_host="lh", oracle_port=1521, oracle_service_name="xe",
        oracle_user="u", oracle_password="p",
        duckdb_path=":memory:"
    )


def test_040_duckdb_ping(mock_config):
    """TEST-040: DuckDB health check/ping 확인"""
    with patch("oracle_duckdb_sync.database.duckdb_source.duckdb") as mock_duckdb:
        mock_conn = mock_duckdb.connect.return_value
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1,)]
        mock_conn.execute.return_value = mock_result

        source = DuckDBSource(mock_config)
        result = source.ping()

        # Verify execute was called with correct query
        mock_conn.execute.assert_called_with("SELECT 1")
        
        # Verify fetchall was called
        mock_result.fetchall.assert_called_once()
        
        # Verify ping returns expected result
        assert result == [(1,)], "Ping should return [(1,)]"


def test_041_ensure_database(mock_config):
    """TEST-041: ensure_database는 DuckDB에서 no-op"""
    with patch("oracle_duckdb_sync.database.duckdb_source.duckdb") as mock_duckdb:
        mock_conn = mock_duckdb.connect.return_value
        source = DuckDBSource(mock_config)

        # Track the initial call count (from connection/initialization)
        initial_execute_count = mock_conn.execute.call_count
        
        # ensure_database는 DuckDB에서 아무 작업도 하지 않음
        result = source.ensure_database()
        
        # Verify no additional execute calls were made
        assert mock_conn.execute.call_count == initial_execute_count, \
            "ensure_database should not call execute() - it's a no-op for DuckDB"
        
        # Verify the method completes without error and returns None
        assert result is None


def test_042_column_type_mapping(mock_config):
    """TEST-042: 컬럼 타입 매핑 검증"""
    with patch("oracle_duckdb_sync.database.duckdb_source.duckdb"):
        source = DuckDBSource(mock_config)
        assert source.map_oracle_type("NUMBER") == "DOUBLE"
        assert source.map_oracle_type("DATE") == "TIMESTAMP"
        assert source.map_oracle_type("VARCHAR2") == "VARCHAR"


def test_050_batch_insert(mock_config):
    """TEST-050: 배치 INSERT 성공 및 행 수 검증"""
    with patch("oracle_duckdb_sync.database.duckdb_source.duckdb") as mock_duckdb:
        mock_conn = mock_duckdb.connect.return_value
        source = DuckDBSource(mock_config)

        data = [(1, "A"), (2, "B")]
        table = "sync_table"
        result = source.insert_batch(table, data)

        mock_conn.executemany.assert_called()
        call_args = mock_conn.executemany.call_args
        assert f"INSERT INTO {table}" in call_args[0][0]
        assert call_args[0][1] == data
        assert result == 2


def test_051_create_table_query(mock_config):
    """TEST-051: CREATE TABLE 쿼리 생성 (DuckDB PRIMARY KEY 방식)"""
    with patch("oracle_duckdb_sync.database.duckdb_source.duckdb"):
        source = DuckDBSource(mock_config)
        ddl = source.build_create_table_query(
            "test_table",
            [("ID", "BIGINT"), ("VAL", "VARCHAR")],
            primary_key="ID"
        )
        assert "CREATE TABLE IF NOT EXISTS test_table" in ddl
        assert "PRIMARY KEY (ID)" in ddl


def test_041b_disconnect_cleanup(mock_config):
    """TEST-041b: disconnect가 connection을 정리하는지 확인"""
    with patch("oracle_duckdb_sync.database.duckdb_source.duckdb") as mock_duckdb:
        mock_conn = mock_duckdb.connect.return_value

        source = DuckDBSource(mock_config)
        source.disconnect()

        mock_conn.close.assert_called_once()
        assert source.conn is None
