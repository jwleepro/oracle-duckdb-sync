from unittest.mock import MagicMock, patch

import pytest

from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource


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
    """TEST-042: DuckDB는 Oracle 타입 매핑을 가지지 않음 (SyncEngine으로 이동됨)"""
    # This test is now obsolete - map_oracle_type has been moved to SyncEngine
    # DuckDB should not have Oracle-specific knowledge
    # Type mapping is only needed during data synchronization
    pass


def test_050_batch_insert(mock_config):
    """TEST-050: 배치 INSERT 성공 및 행 수 검증"""
    with patch("oracle_duckdb_sync.database.duckdb_source.duckdb") as mock_duckdb:
        mock_conn = mock_duckdb.connect.return_value
        source = DuckDBSource(mock_config)

        data = [(1, "A"), (2, "B")]
        table = "sync_table"
        column_names = ["id", "name"]
        result = source.insert_batch(table, data, column_names=column_names)

        # Verify that execute was called with INSERT INTO ... SELECT * FROM df
        mock_conn.execute.assert_called()
        call_args = mock_conn.execute.call_args
        assert f"INSERT INTO {table}" in call_args[0][0]
        assert "SELECT * FROM df" in call_args[0][0]
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



def test_051_upsert_on_conflict_integration(mock_config):
    """TEST-051: 증분 시 중복 키에 대한 upsert 처리 (실제 DuckDB 통합 테스트)

    이 테스트는 실제 DuckDB 인스턴스를 사용하여 UPSERT 동작을 검증합니다:
    1. PRIMARY KEY가 있는 테이블 생성
    2. 초기 데이터 삽입
    3. 동일한 PRIMARY KEY로 다시 삽입 (UPSERT 발생)
    4. 중복 없이 데이터가 업데이트되었는지 확인
    """
    # Use real DuckDB in-memory database
    source = DuckDBSource(mock_config)

    # Create table with PRIMARY KEY
    source.conn.execute("""
        CREATE TABLE test_upsert (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            value INTEGER
        )
    """)

    # First insert: 3 rows
    data1 = [(1, "Alice", 100), (2, "Bob", 200), (3, "Charlie", 300)]
    column_names = ["id", "name", "value"]

    result1 = source.insert_batch("test_upsert", data1, column_names=column_names, primary_key="id")
    assert result1 == 3

    # Verify initial data
    rows = source.conn.execute("SELECT * FROM test_upsert ORDER BY id").fetchall()
    assert len(rows) == 3
    assert rows[0] == (1, "Alice", 100)
    assert rows[1] == (2, "Bob", 200)
    assert rows[2] == (3, "Charlie", 300)

    # Second insert: Duplicate keys (1, 2) with updated values + new key (4)
    data2 = [(1, "Alice Updated", 150), (2, "Bob Updated", 250), (4, "David", 400)]

    result2 = source.insert_batch("test_upsert", data2, column_names=column_names, primary_key="id")
    assert result2 == 3

    # Verify UPSERT behavior: should have 4 rows total (not 6)
    rows = source.conn.execute("SELECT * FROM test_upsert ORDER BY id").fetchall()
    assert len(rows) == 4, f"Expected 4 rows (UPSERT), but got {len(rows)}"

    # Verify updated values for existing keys
    assert rows[0] == (1, "Alice Updated", 150), "Row 1 should be updated"
    assert rows[1] == (2, "Bob Updated", 250), "Row 2 should be updated"

    # Verify unchanged row
    assert rows[2] == (3, "Charlie", 300), "Row 3 should remain unchanged"

    # Verify new row
    assert rows[3] == (4, "David", 400), "Row 4 should be inserted"

    source.disconnect()
