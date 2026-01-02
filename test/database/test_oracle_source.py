import pytest
import datetime
from unittest.mock import MagicMock, patch
from oracle_duckdb_sync.database.oracle_source import OracleSource, datetime_handler
from oracle_duckdb_sync.config import Config

@pytest.fixture
def mock_config():
    return Config(
        oracle_host="localhost",
        oracle_port=1521,
        oracle_service_name="xe",
        oracle_user="admin",
        oracle_password="password",
        duckdb_path=":memory:"
    )

def test_020_oracle_connection_creation(mock_config):
    """TEST-020: Oracle DB 연결 객체 생성 확인 (DSN 방식)"""
    with patch("oracledb.connect") as mock_connect:
        source = OracleSource(mock_config)
        source.connect()

        # Verify connect was called once
        mock_connect.assert_called_once()

        # Verify connection parameters are correct (DSN format)
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs["user"] == mock_config.oracle_user
        assert call_kwargs["password"] == mock_config.oracle_password

        # Verify DSN is correctly formatted: host:port/service_name
        expected_dsn = f"{mock_config.oracle_host}:{mock_config.oracle_port}/{mock_config.oracle_service_name}"
        assert call_kwargs["dsn"] == expected_dsn

def test_021_oracle_connection_failure(mock_config):
    """TEST-021: 연결 실패 시 예외 처리 확인"""
    with patch("oracledb.connect", side_effect=Exception("Connection Failed")):
        source = OracleSource(mock_config)
        with pytest.raises(Exception, match="Connection Failed"):
            source.connect()

def test_022_oracle_pool_initialization(mock_config):
    """TEST-022: 커넥션 풀 초기화 확인"""
    with patch("oracledb.create_pool") as mock_create_pool:
        source = OracleSource(mock_config)
        source.init_pool(min_conn=1, max_conn=5)
        
        # Verify create_pool was called once
        mock_create_pool.assert_called_once()
        
        # Verify pool parameters are correct
        call_kwargs = mock_create_pool.call_args[1]
        assert call_kwargs["min"] == 1, "min_conn should be 1"
        assert call_kwargs["max"] == 5, "max_conn should be 5"
        assert call_kwargs["user"] == mock_config.oracle_user
        assert call_kwargs["password"] == mock_config.oracle_password
        
        # Verify DSN is correctly formatted
        expected_dsn = f"{mock_config.oracle_host}:{mock_config.oracle_port}/{mock_config.oracle_service_name}"
        assert call_kwargs["dsn"] == expected_dsn

def test_030_fetch_all_data(mock_config):
    """TEST-030: 전체 조회(fetchall) 동작 확인"""
    with patch("oracledb.connect") as mock_connect:
        mock_conn = mock_connect.return_value
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [(1, "data1"), (2, "data2")]
        
        source = OracleSource(mock_config)
        source.connect()
        data = source.fetch_all("SELECT * FROM table")
        
        # Verify row count
        assert len(data) == 2
        
        # Verify actual data content
        assert data[0] == (1, "data1"), "First row should be (1, 'data1')"
        assert data[1] == (2, "data2"), "Second row should be (2, 'data2')"

def test_031_fetch_batch_data(mock_config):
    """TEST-031: 배치 단위 조회(fetchmany) 동작 확인"""
    with patch("oracledb.connect") as mock_connect:
        mock_conn = mock_connect.return_value
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor  # Direct cursor, no context manager
        mock_cursor.fetchmany.return_value = [(1, "data1")]

        source = OracleSource(mock_config)
        source.connect()
        data = source.fetch_batch("SELECT * FROM table", batch_size=1)
        
        # Verify row count
        assert len(data) == 1
        
        # Verify actual data content
        assert data[0] == (1, "data1"), "First row should be (1, 'data1')"
        
        # Verify cursor was created and execute was called
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT * FROM table")

def test_031b_fetch_batch_pagination(mock_config):
    """TEST-031b: 배치 조회 시 커서 상태 유지 및 페이지네이션 확인"""
    with patch("oracledb.connect") as mock_connect:
        mock_conn = mock_connect.return_value
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate multiple batches: first returns 2 rows, second returns 1 row, third returns empty
        mock_cursor.fetchmany.side_effect = [
            [(1, "batch1_row1"), (2, "batch1_row2")],  # First call
            [(3, "batch2_row1")],                        # Second call
            []                                            # Third call (no more data)
        ]

        source = OracleSource(mock_config)
        source.connect()

        query = "SELECT * FROM table"

        # First batch
        data1 = source.fetch_batch(query, batch_size=2)
        assert len(data1) == 2
        assert data1[0] == (1, "batch1_row1")

        # Second batch - should continue from same cursor, NOT re-execute query
        data2 = source.fetch_batch(query, batch_size=2)
        assert len(data2) == 1
        assert data2[0] == (3, "batch2_row1")

        # Third batch - empty, should reset cursor
        data3 = source.fetch_batch(query, batch_size=2)
        assert len(data3) == 0

        # Verify query was executed only ONCE (not 3 times)
        assert mock_cursor.execute.call_count == 1
        mock_cursor.execute.assert_called_with(query)

        # Verify fetchmany was called 3 times
        assert mock_cursor.fetchmany.call_count == 3

def test_032_incremental_query(mock_config):
    """TEST-032: 증분 조회 쿼리 생성 확인"""
    source = OracleSource(mock_config)
    last_sync = "2023-01-01 00:00:00"
    query = source.build_incremental_query("TEST_TABLE", "TIMESTAMP_COL", last_sync)
    assert "TIMESTAMP_COL > '2023-01-01 00:00:00'" in query

def test_033_date_conversion_handler(mock_config):
    """TEST-033: DATE 컬럼 ISO 문자열 변환 처리 확인"""
    dt = datetime.datetime(2023, 5, 20, 10, 30)
    result = datetime_handler(dt)
    assert result == "2023-05-20T10:30:00"