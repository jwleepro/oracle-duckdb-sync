"""
테이블 설정 저장소

DuckDB에 테이블 동기화 설정을 저장하고 조회하는 CRUD 레포지토리입니다.
"""

from typing import List, Optional

from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.table_config.models import TableConfig


class TableConfigRepository:
    """
    테이블 설정 저장소

    DuckDB의 table_configs 테이블을 관리합니다.
    """

    TABLE_NAME = 'table_configs'

    def __init__(self, config: Config = None, duckdb_source: DuckDBSource = None):
        """
        Args:
            config: 애플리케이션 설정
            duckdb_source: DuckDB 소스 객체
        """
        self.logger = setup_logger('TableConfigRepository')

        if duckdb_source:
            self.duckdb = duckdb_source
        elif config:
            self.duckdb = DuckDBSource(config)
        else:
            raise ValueError("Either config or duckdb_source must be provided")

        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """table_configs 테이블이 없으면 생성"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            id INTEGER PRIMARY KEY,
            oracle_schema VARCHAR(100) NOT NULL,
            oracle_table VARCHAR(255) NOT NULL,
            duckdb_table VARCHAR(255) NOT NULL,
            primary_key VARCHAR(100) NOT NULL,
            time_column VARCHAR(100),
            sync_enabled BOOLEAN DEFAULT TRUE,
            batch_size INTEGER DEFAULT 10000,
            description TEXT,
            UNIQUE(oracle_schema, oracle_table)
        )
        """

        try:
            self.duckdb.conn.execute(create_table_sql)
            self.logger.debug(f"Table {self.TABLE_NAME} is ready")
        except Exception as e:
            self.logger.error(f"Failed to create {self.TABLE_NAME} table: {e}")
            raise

    def create(self, config: TableConfig) -> TableConfig:
        """
        새 테이블 설정 생성

        Args:
            config: 생성할 TableConfig 객체

        Returns:
            생성된 TableConfig 객체 (id 포함)
        """
        insert_sql = f"""
        INSERT INTO {self.TABLE_NAME}
        (oracle_schema, oracle_table, duckdb_table, primary_key, time_column,
         sync_enabled, batch_size, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            config.oracle_schema,
            config.oracle_table,
            config.duckdb_table,
            config.primary_key,
            config.time_column,
            config.sync_enabled,
            config.batch_size,
            config.description
        )

        try:
            self.duckdb.conn.execute(insert_sql, params)

            # Get the auto-generated ID
            result = self.duckdb.conn.execute("SELECT last_insert_rowid()").fetchone()
            config.id = result[0]

            self.logger.info(f"Created table config: {config.get_oracle_full_name()}")
            return config

        except Exception as e:
            self.logger.error(f"Failed to create table config: {e}")
            raise

    def get_by_id(self, config_id: int) -> Optional[TableConfig]:
        """
        ID로 테이블 설정 조회

        Args:
            config_id: 설정 ID

        Returns:
            TableConfig 객체 또는 None
        """
        select_sql = f"""
        SELECT id, oracle_schema, oracle_table, duckdb_table, primary_key,
               time_column, sync_enabled, batch_size, description
        FROM {self.TABLE_NAME}
        WHERE id = ?
        """

        try:
            result = self.duckdb.conn.execute(select_sql, (config_id,)).fetchone()
            if result:
                return self._row_to_config(result)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get table config by id: {e}")
            raise

    def get_by_oracle_table(self, oracle_schema: str, oracle_table: str) -> Optional[TableConfig]:
        """
        Oracle 테이블명으로 설정 조회

        Args:
            oracle_schema: Oracle 스키마명
            oracle_table: Oracle 테이블명

        Returns:
            TableConfig 객체 또는 None
        """
        select_sql = f"""
        SELECT id, oracle_schema, oracle_table, duckdb_table, primary_key,
               time_column, sync_enabled, batch_size, description
        FROM {self.TABLE_NAME}
        WHERE oracle_schema = ? AND oracle_table = ?
        """

        try:
            result = self.duckdb.conn.execute(select_sql, (oracle_schema, oracle_table)).fetchone()
            if result:
                return self._row_to_config(result)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get table config by oracle table: {e}")
            raise

    def get_all(self, enabled_only: bool = False) -> List[TableConfig]:
        """
        모든 테이블 설정 조회

        Args:
            enabled_only: 활성화된 설정만 조회

        Returns:
            TableConfig 리스트
        """
        where_clause = "WHERE sync_enabled = TRUE" if enabled_only else ""
        select_sql = f"""
        SELECT id, oracle_schema, oracle_table, duckdb_table, primary_key,
               time_column, sync_enabled, batch_size, description
        FROM {self.TABLE_NAME}
        {where_clause}
        ORDER BY oracle_schema, oracle_table
        """

        try:
            results = self.duckdb.conn.execute(select_sql).fetchall()
            return [self._row_to_config(row) for row in results]

        except Exception as e:
            self.logger.error(f"Failed to get all table configs: {e}")
            raise

    def update(self, config: TableConfig) -> TableConfig:
        """
        테이블 설정 업데이트

        Args:
            config: 업데이트할 TableConfig 객체 (id 필수)

        Returns:
            업데이트된 TableConfig 객체
        """
        if not config.id:
            raise ValueError("TableConfig must have an ID to update")

        update_sql = f"""
        UPDATE {self.TABLE_NAME}
        SET oracle_schema = ?,
            oracle_table = ?,
            duckdb_table = ?,
            primary_key = ?,
            time_column = ?,
            sync_enabled = ?,
            batch_size = ?,
            description = ?
        WHERE id = ?
        """

        params = (
            config.oracle_schema,
            config.oracle_table,
            config.duckdb_table,
            config.primary_key,
            config.time_column,
            config.sync_enabled,
            config.batch_size,
            config.description,
            config.id
        )

        try:
            self.duckdb.conn.execute(update_sql, params)
            self.logger.info(f"Updated table config: {config.get_oracle_full_name()}")
            return config

        except Exception as e:
            self.logger.error(f"Failed to update table config: {e}")
            raise

    def delete(self, config_id: int) -> bool:
        """
        테이블 설정 삭제

        Args:
            config_id: 설정 ID

        Returns:
            삭제 성공 여부
        """
        delete_sql = f"""
        DELETE FROM {self.TABLE_NAME}
        WHERE id = ?
        """

        try:
            self.duckdb.conn.execute(delete_sql, (config_id,))
            self.logger.info(f"Deleted table config id: {config_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete table config: {e}")
            raise

    def toggle_sync_enabled(self, config_id: int, enabled: bool) -> bool:
        """
        동기화 활성화/비활성화 토글

        Args:
            config_id: 설정 ID
            enabled: 활성화 여부

        Returns:
            성공 여부
        """
        update_sql = f"""
        UPDATE {self.TABLE_NAME}
        SET sync_enabled = ?
        WHERE id = ?
        """

        try:
            self.duckdb.conn.execute(update_sql, (enabled, config_id))
            status = "enabled" if enabled else "disabled"
            self.logger.info(f"Table config {config_id} sync {status}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to toggle sync enabled: {e}")
            raise

    def get_enabled_configs(self) -> List[TableConfig]:
        """
        활성화된 테이블 설정만 조회

        Returns:
            활성화된 TableConfig 리스트
        """
        return self.get_all(enabled_only=True)

    def exists(self, oracle_schema: str, oracle_table: str) -> bool:
        """
        테이블 설정 존재 여부 확인

        Args:
            oracle_schema: Oracle 스키마명
            oracle_table: Oracle 테이블명

        Returns:
            존재 여부
        """
        return self.get_by_oracle_table(oracle_schema, oracle_table) is not None

    def _row_to_config(self, row: tuple) -> TableConfig:
        """
        DB 행을 TableConfig 객체로 변환

        Args:
            row: (id, oracle_schema, oracle_table, duckdb_table, primary_key,
                  time_column, sync_enabled, batch_size, description)

        Returns:
            TableConfig 객체
        """
        return TableConfig(
            id=row[0],
            oracle_schema=row[1],
            oracle_table=row[2],
            duckdb_table=row[3],
            primary_key=row[4],
            time_column=row[5] or "",
            sync_enabled=row[6],
            batch_size=row[7] or 10000,
            description=row[8]
        )
