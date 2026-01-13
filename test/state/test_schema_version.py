"""Tests for schema and mapping configuration version management"""
from unittest.mock import patch

import pytest

from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.sync_engine import SyncEngine


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


def test_141_schema_mapping_version_management(tmp_path, mock_config):
    """TEST-141: 스키마/매핑 설정 버전 관리

    This test verifies that:
    1. Schema mapping configuration can be saved with version
    2. Schema mapping configuration can be loaded
    3. Version changes are tracked
    4. Multiple versions can coexist
    5. Latest version is identified correctly
    """
    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource"), \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource"):
        engine = SyncEngine(mock_config)
        schema_file = tmp_path / "schema_mappings.json"

        # Test 1: Save initial schema mapping with version
        schema_v1 = {
            "table_name": "ORDERS",
            "columns": [
                {"name": "ORDER_ID", "oracle_type": "NUMBER", "duckdb_type": "DOUBLE"},
                {"name": "CUSTOMER_NAME", "oracle_type": "VARCHAR2(100)", "duckdb_type": "VARCHAR"},
                {"name": "ORDER_DATE", "oracle_type": "DATE", "duckdb_type": "TIMESTAMP"}
            ],
            "primary_key": "ORDER_ID"
        }

        engine.save_schema_mapping(
            table_name="ORDERS",
            schema=schema_v1,
            version="1.0",
            file_path=str(schema_file)
        )

        # Test 2: Load schema mapping
        loaded_schema = engine.load_schema_mapping(
            table_name="ORDERS",
            file_path=str(schema_file)
        )

        assert loaded_schema is not None
        assert loaded_schema["version"] == "1.0"
        assert loaded_schema["schema"]["table_name"] == "ORDERS"
        assert len(loaded_schema["schema"]["columns"]) == 3

        # Test 3: Save updated schema mapping with new version
        schema_v2 = {
            "table_name": "ORDERS",
            "columns": [
                {"name": "ORDER_ID", "oracle_type": "NUMBER", "duckdb_type": "BIGINT"},  # Changed type
                {"name": "CUSTOMER_NAME", "oracle_type": "VARCHAR2(100)", "duckdb_type": "VARCHAR"},
                {"name": "ORDER_DATE", "oracle_type": "DATE", "duckdb_type": "TIMESTAMP"},
                {"name": "TOTAL_AMOUNT", "oracle_type": "NUMBER(10,2)", "duckdb_type": "DECIMAL(10,2)"}  # New column
            ],
            "primary_key": "ORDER_ID"
        }

        engine.save_schema_mapping(
            table_name="ORDERS",
            schema=schema_v2,
            version="2.0",
            file_path=str(schema_file)
        )

        # Test 4: Load latest version
        latest_schema = engine.load_schema_mapping(
            table_name="ORDERS",
            file_path=str(schema_file)
        )

        assert latest_schema["version"] == "2.0"
        assert len(latest_schema["schema"]["columns"]) == 4

        # Test 5: Load specific version
        v1_schema = engine.load_schema_mapping(
            table_name="ORDERS",
            version="1.0",
            file_path=str(schema_file)
        )

        assert v1_schema["version"] == "1.0"
        assert len(v1_schema["schema"]["columns"]) == 3

        # Test 6: Get version history
        versions = engine.get_schema_versions(
            table_name="ORDERS",
            file_path=str(schema_file)
        )

        assert len(versions) == 2
        assert "1.0" in versions
        assert "2.0" in versions

        # Test 7: Handle non-existent table
        non_existent = engine.load_schema_mapping(
            table_name="NON_EXISTENT_TABLE",
            file_path=str(schema_file)
        )

        assert non_existent is None

        # Test 8: Handle non-existent version
        non_existent_version = engine.load_schema_mapping(
            table_name="ORDERS",
            version="99.0",
            file_path=str(schema_file)
        )

        assert non_existent_version is None
