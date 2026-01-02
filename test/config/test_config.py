import os
import pytest
from oracle_duckdb_sync.config import load_config


@pytest.fixture
def setup_env(monkeypatch):
    """모든 필수 환경 변수를 기본값으로 설정하는 피스처"""
    # Mock load_dotenv to prevent loading .env file during tests
    import oracle_duckdb_sync.config.config as config_module
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)
    
    # Clear all potentially interfering env vars
    env_to_clear = [
        "ORACLE_HOST", "ORACLE_PORT", "ORACLE_SERVICE_NAME", "ORACLE_USER", "ORACLE_PASSWORD",
        "DUCKDB_PATH", "DUCKDB_DATABASE", "DUCKDB_LOCK_FILE",
        "SYNC_ORACLE_SCHEMA", "SYNC_ORACLE_TABLE", "SYNC_DUCKDB_TABLE",
        "SYNC_PRIMARY_KEY", "SYNC_TIME_COLUMN",
        "SYNC_BATCH_SIZE", "ORACLE_FETCH_BATCH_SIZE", "SYNC_MAX_DURATION_SECONDS",
        "TEST_SYNC_DEFAULT_ROW_LIMIT", "PROGRESS_REFRESH_INTERVAL_SECONDS",
        "TYPE_DETECTION_THRESHOLD", "SYNC_RETRY_ATTEMPTS", "SYNC_RETRY_DELAY_SECONDS",
        "STATE_DIRECTORY", "SYNC_STATE_FILE", "SCHEMA_MAPPING_FILE", "SYNC_PROGRESS_FILE"
    ]
    for var in env_to_clear:
        monkeypatch.delenv(var, raising=False)
    
    # Then set the minimal required values
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_SERVICE_NAME": "xe",
        "ORACLE_USER": "admin",
        "ORACLE_PASSWORD": "password",
        "DUCKDB_PATH": ":memory:",
        "SYNC_DUCKDB_TABLE": "test_table",
    }
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)
    return env_vars


def test_010_load_oracle_config(setup_env, monkeypatch):
    """TEST-010: Oracle 연결 정보 로드 확인"""
    monkeypatch.setenv("ORACLE_HOST", "custom-host")
    monkeypatch.setenv("ORACLE_PORT", "1522")

    config = load_config()

    assert config.oracle_host == "custom-host"
    assert config.oracle_port == 1522
    assert config.oracle_service_name == "xe"


def test_011_load_duckdb_config(setup_env, monkeypatch):
    """TEST-011: DuckDB 연결 정보 로드 확인"""
    monkeypatch.setenv("DUCKDB_PATH", "./data/test.duckdb")
    monkeypatch.setenv("DUCKDB_DATABASE", "sync_db")

    config = load_config()

    assert config.duckdb_path == "./data/test.duckdb"
    assert config.duckdb_database == "sync_db"


def test_012_missing_config_raises_error(setup_env, monkeypatch):
    """TEST-012: 필수 설정 누락 시 오류 발생 확인"""
    monkeypatch.delenv("ORACLE_HOST", raising=False)

    with pytest.raises(ValueError, match="Missing required configuration: ORACLE_HOST"):
        load_config()


def test_013_default_values(setup_env, monkeypatch):
    """TEST-013: 기본 포트/옵션 적용 검증"""
    # 포트들을 설정하지 않음
    monkeypatch.delenv("ORACLE_PORT", raising=False)
    monkeypatch.delenv("DUCKDB_DATABASE", raising=False)

    config = load_config()

    assert config.oracle_port == 1521  # Default
    assert config.duckdb_database == "main"  # Default


def test_014_sync_table_config(setup_env, monkeypatch):
    """TEST-014: 동기화 테이블 설정 로드 확인"""
    monkeypatch.setenv("SYNC_ORACLE_TABLE", "MY_TABLE")
    monkeypatch.setenv("SYNC_DUCKDB_TABLE", "my_custom_table")
    monkeypatch.setenv("SYNC_PRIMARY_KEY", "USER_ID")
    monkeypatch.setenv("SYNC_TIME_COLUMN", "CREATED_AT")

    config = load_config()

    assert config.sync_oracle_table == "MY_TABLE"
    assert config.sync_duckdb_table == "my_custom_table"
    assert config.sync_primary_key == "USER_ID"
    assert config.sync_time_column == "CREATED_AT"


def test_015_sync_table_default_duckdb_name(setup_env, monkeypatch):
    """TEST-015: DuckDB 테이블명 미지정 시 Oracle 테이블명을 소문자로 사용"""
    monkeypatch.setenv("SYNC_ORACLE_TABLE", "MY_ORACLE_TABLE")
    monkeypatch.delenv("SYNC_DUCKDB_TABLE", raising=False)

    config = load_config()

    assert config.sync_oracle_table == "MY_ORACLE_TABLE"
    assert config.sync_duckdb_table == "my_oracle_table"  # Lowercase conversion


def test_016_sync_table_default_values(setup_env, monkeypatch):
    """TEST-016: 동기화 설정 기본값 확인"""
    # 동기화 설정을 모두 제거
    monkeypatch.delenv("SYNC_ORACLE_TABLE", raising=False)
    monkeypatch.delenv("SYNC_DUCKDB_TABLE", raising=False)
    monkeypatch.delenv("SYNC_PRIMARY_KEY", raising=False)
    monkeypatch.delenv("SYNC_TIME_COLUMN", raising=False)

    config = load_config()

    assert config.sync_oracle_table == ""
    assert config.sync_duckdb_table == ""
    assert config.sync_primary_key == "ID"  # Default
    assert config.sync_time_column == "TIMESTAMP_COL"  # Default


def test_017_performance_settings_defaults(setup_env):
    """TEST-017: 성능 설정의 기본값 확인"""
    config = load_config()

    # Sync performance settings
    assert config.sync_batch_size == 10000
    assert config.oracle_fetch_batch_size == 1000
    assert config.sync_max_duration_seconds == 3600
    assert config.test_sync_default_row_limit == 100000

    # Progress reporting
    assert config.progress_refresh_interval_seconds == 0.5

    # Type detection threshold
    assert config.type_detection_threshold == 0.9

    # Retry settings
    assert config.sync_retry_attempts == 3
    assert config.sync_retry_delay_seconds == 0.1


def test_018_performance_settings_from_env(setup_env, monkeypatch):
    """TEST-018: 환경 변수로부터 성능 설정 로드"""
    monkeypatch.setenv("SYNC_BATCH_SIZE", "5000")
    monkeypatch.setenv("ORACLE_FETCH_BATCH_SIZE", "500")
    monkeypatch.setenv("SYNC_MAX_DURATION_SECONDS", "1800")
    monkeypatch.setenv("TEST_SYNC_DEFAULT_ROW_LIMIT", "50000")

    config = load_config()

    assert config.sync_batch_size == 5000
    assert config.oracle_fetch_batch_size == 500
    assert config.sync_max_duration_seconds == 1800
    assert config.test_sync_default_row_limit == 50000


def test_019_file_path_settings_defaults(setup_env):
    """TEST-019: 파일 경로 설정의 기본값 확인"""
    config = load_config()

    # State directory and file names
    assert config.state_directory == "./data"
    assert config.sync_state_file == "sync_state.json"
    assert config.schema_mapping_file == "schema_mappings.json"
    assert config.sync_progress_file == "sync_progress.json"

    # Path properties
    assert config.sync_state_path == os.path.join("./data", "sync_state.json")
    assert config.schema_mapping_path == os.path.join("./data", "schema_mappings.json")
    assert config.sync_progress_path == os.path.join("./data", "sync_progress.json")


def test_020_file_path_settings_from_env(setup_env, monkeypatch):
    """TEST-020: 환경 변수로부터 파일 경로 설정 로드"""
    monkeypatch.setenv("STATE_DIRECTORY", "/custom/path")
    monkeypatch.setenv("SYNC_STATE_FILE", "custom_state.json")
    monkeypatch.setenv("SCHEMA_MAPPING_FILE", "custom_schema.json")
    monkeypatch.setenv("SYNC_PROGRESS_FILE", "custom_progress.json")

    config = load_config()

    assert config.state_directory == "/custom/path"
    assert config.sync_state_file == "custom_state.json"
    assert config.schema_mapping_file == "custom_schema.json"
    assert config.sync_progress_file == "custom_progress.json"

    # Path properties should use custom values
    assert config.sync_state_path == os.path.join("/custom/path", "custom_state.json")
    assert config.schema_mapping_path == os.path.join("/custom/path", "custom_schema.json")
    assert config.sync_progress_path == os.path.join("/custom/path", "custom_progress.json")


def test_021_duckdb_time_column_from_env(setup_env, monkeypatch):
    """TEST-021: DUCKDB_TIME_COLUMN 환경 변수로부터 로드"""
    monkeypatch.setenv("DUCKDB_TIME_COLUMN", "TRAN_TIME")

    config = load_config()

    assert config.duckdb_time_column == "TRAN_TIME"


def test_022_duckdb_time_column_default_value(setup_env):
    """TEST-022: DUCKDB_TIME_COLUMN 기본값 확인"""
    config = load_config()

    # DUCKDB_TIME_COLUMN이 설정되지 않으면 기본값 사용
    assert config.duckdb_time_column == "TIMESTAMP_COL"


def test_023_duckdb_time_column_fallback_from_sync_time_column(setup_env, monkeypatch):
    """TEST-023: DUCKDB_TIME_COLUMN 미설정 시 SYNC_TIME_COLUMN에서 첫 번째 컬럼 추출"""
    monkeypatch.setenv("SYNC_TIME_COLUMN", "FACTORY, TRAN_TIME")
    # DUCKDB_TIME_COLUMN은 설정하지 않음
    monkeypatch.delenv("DUCKDB_TIME_COLUMN", raising=False)

    config = load_config()

    # SYNC_TIME_COLUMN의 첫 번째 컬럼 (FACTORY)을 fallback으로 사용
    assert config.duckdb_time_column == "FACTORY"


def test_024_duckdb_time_column_explicit_overrides_sync_time_column(setup_env, monkeypatch):
    """TEST-024: DUCKDB_TIME_COLUMN이 명시되면 SYNC_TIME_COLUMN 무시"""
    monkeypatch.setenv("SYNC_TIME_COLUMN", "FACTORY, TRAN_TIME")
    monkeypatch.setenv("DUCKDB_TIME_COLUMN", "TRAN_TIME")

    config = load_config()

    # 명시적으로 설정된 DUCKDB_TIME_COLUMN 사용
    assert config.duckdb_time_column == "TRAN_TIME"


def test_025_duckdb_time_column_handles_whitespace(setup_env, monkeypatch):
    """TEST-025: SYNC_TIME_COLUMN fallback 시 공백 처리"""
    monkeypatch.setenv("SYNC_TIME_COLUMN", "  FACTORY  ,  TRAN_TIME  ")
    monkeypatch.delenv("DUCKDB_TIME_COLUMN", raising=False)

    config = load_config()

    # 공백이 제거된 첫 번째 컬럼 사용
    assert config.duckdb_time_column == "FACTORY"
