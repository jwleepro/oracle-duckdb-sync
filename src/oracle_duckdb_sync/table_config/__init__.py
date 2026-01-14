"""Table configuration module for Oracle-DuckDB Sync."""

from oracle_duckdb_sync.table_config.models import TableConfig
from oracle_duckdb_sync.table_config.repository import TableConfigRepository
from oracle_duckdb_sync.table_config.service import TableConfigService

__all__ = [
    'TableConfig',
    'TableConfigRepository',
    'TableConfigService',
]
