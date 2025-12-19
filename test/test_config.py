import os
import pytest
from oracle_duckdb_sync.config import load_config


@pytest.fixture
def setup_env(monkeypatch):
    """모든 필수 환경 변수를 기본값으로 설정하는 피스처"""
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_SERVICE_NAME": "xe",
        "ORACLE_USER": "admin",
        "ORACLE_PASSWORD": "password",
        "DUCKDB_PATH": ":memory:",
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
