"""
동기화 로그 저장소

DuckDB에 동기화 작업 로그를 저장하고 조회하는 CRUD 레포지토리입니다.
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

import duckdb

from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.models.sync_log import SyncLog, SyncStatus, SyncType


class SyncLogRepository:
    """
    동기화 로그 레포지토리

    DuckDB의 sync_logs 테이블을 관리합니다.
    """

    TABLE_NAME = 'sync_logs'

    def __init__(self, config: Config = None, duckdb_source: DuckDBSource = None):
        """
        Args:
            config: 애플리케이션 설정 (duckdb_source가 없을 때 필수)
            duckdb_source: DuckDB 소스 객체 (테스트 시 사용)
        """
        self.logger = setup_logger('SyncLogRepository')

        if duckdb_source:
            self.duckdb = duckdb_source
        elif config:
            self.duckdb = DuckDBSource(config)
        else:
            raise ValueError("Either config or duckdb_source must be provided")

        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """sync_logs 테이블이 없으면 생성"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            id INTEGER PRIMARY KEY,
            sync_id VARCHAR(36) NOT NULL,
            table_name VARCHAR(255) NOT NULL,
            sync_type VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            total_rows INTEGER DEFAULT 0,
            error_message TEXT
        )
        """

        try:
            self.duckdb.conn.execute(create_table_sql)
            self.logger.debug(f"Table {self.TABLE_NAME} is ready")
        except Exception as e:
            self.logger.error(f"Failed to create {self.TABLE_NAME} table: {e}")
            raise

    def create(self, sync_log: SyncLog) -> SyncLog:
        """
        새 동기화 로그 생성

        Args:
            sync_log: 생성할 SyncLog 객체

        Returns:
            생성된 SyncLog 객체 (id 포함)
        """
        # sync_id가 없으면 자동 생성
        if not sync_log.sync_id:
            sync_log.sync_id = str(uuid4())

        insert_sql = f"""
        INSERT INTO {self.TABLE_NAME}
        (sync_id, table_name, sync_type, status, start_time, end_time, total_rows, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            sync_log.sync_id,
            sync_log.table_name,
            sync_log.sync_type.value if isinstance(sync_log.sync_type, SyncType) else sync_log.sync_type,
            sync_log.status.value if isinstance(sync_log.status, SyncStatus) else sync_log.status,
            sync_log.start_time,
            sync_log.end_time,
            sync_log.total_rows,
            sync_log.error_message
        )

        try:
            self.duckdb.conn.execute(insert_sql, params)

            # Get the auto-generated ID
            result = self.duckdb.conn.execute("SELECT last_insert_rowid()").fetchone()
            sync_log.id = result[0]

            self.logger.info(f"Created sync log: {sync_log.sync_id} for table {sync_log.table_name}")
            return sync_log

        except Exception as e:
            self.logger.error(f"Failed to create sync log: {e}")
            raise

    def update(self, sync_log: SyncLog) -> SyncLog:
        """
        동기화 로그 업데이트

        Args:
            sync_log: 업데이트할 SyncLog 객체 (id 필수)

        Returns:
            업데이트된 SyncLog 객체
        """
        if not sync_log.id:
            raise ValueError("SyncLog must have an ID to update")

        update_sql = f"""
        UPDATE {self.TABLE_NAME}
        SET status = ?,
            end_time = ?,
            total_rows = ?,
            error_message = ?
        WHERE id = ?
        """

        params = (
            sync_log.status.value if isinstance(sync_log.status, SyncStatus) else sync_log.status,
            sync_log.end_time,
            sync_log.total_rows,
            sync_log.error_message,
            sync_log.id
        )

        try:
            self.duckdb.conn.execute(update_sql, params)
            self.logger.info(f"Updated sync log: {sync_log.sync_id}")
            return sync_log

        except Exception as e:
            self.logger.error(f"Failed to update sync log: {e}")
            raise

    def get_by_id(self, log_id: int) -> Optional[SyncLog]:
        """
        ID로 로그 조회

        Args:
            log_id: 로그 ID

        Returns:
            SyncLog 객체 또는 None
        """
        select_sql = f"""
        SELECT id, sync_id, table_name, sync_type, status, start_time, end_time, total_rows, error_message
        FROM {self.TABLE_NAME}
        WHERE id = ?
        """

        try:
            result = self.duckdb.conn.execute(select_sql, (log_id,)).fetchone()
            if result:
                return self._row_to_sync_log(result)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get sync log by id: {e}")
            raise

    def get_by_sync_id(self, sync_id: str) -> Optional[SyncLog]:
        """
        Sync ID로 로그 조회

        Args:
            sync_id: 동기화 작업 ID (UUID)

        Returns:
            SyncLog 객체 또는 None
        """
        select_sql = f"""
        SELECT id, sync_id, table_name, sync_type, status, start_time, end_time, total_rows, error_message
        FROM {self.TABLE_NAME}
        WHERE sync_id = ?
        """

        try:
            result = self.duckdb.conn.execute(select_sql, (sync_id,)).fetchone()
            if result:
                return self._row_to_sync_log(result)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get sync log by sync_id: {e}")
            raise

    def get_recent_logs(self, limit: int = 50, table_name: Optional[str] = None) -> List[SyncLog]:
        """
        최근 로그 조회

        Args:
            limit: 조회할 최대 개수
            table_name: 필터링할 테이블명 (선택적)

        Returns:
            SyncLog 리스트 (최신순)
        """
        where_clause = f"WHERE table_name = ?" if table_name else ""
        select_sql = f"""
        SELECT id, sync_id, table_name, sync_type, status, start_time, end_time, total_rows, error_message
        FROM {self.TABLE_NAME}
        {where_clause}
        ORDER BY start_time DESC
        LIMIT ?
        """

        try:
            if table_name:
                results = self.duckdb.conn.execute(select_sql, (table_name, limit)).fetchall()
            else:
                results = self.duckdb.conn.execute(select_sql, (limit,)).fetchall()

            return [self._row_to_sync_log(row) for row in results]

        except Exception as e:
            self.logger.error(f"Failed to get recent logs: {e}")
            raise

    def get_statistics(self, table_name: Optional[str] = None) -> dict:
        """
        동기화 통계 조회

        Args:
            table_name: 필터링할 테이블명 (선택적)

        Returns:
            통계 딕셔너리 (total, completed, failed, avg_rows 등)
        """
        where_clause = f"WHERE table_name = ?" if table_name else ""
        stats_sql = f"""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
            AVG(CASE WHEN status = 'completed' THEN total_rows ELSE NULL END) as avg_rows,
            SUM(CASE WHEN status = 'completed' THEN total_rows ELSE 0 END) as total_rows_synced
        FROM {self.TABLE_NAME}
        {where_clause}
        """

        try:
            if table_name:
                result = self.duckdb.conn.execute(stats_sql, (table_name,)).fetchone()
            else:
                result = self.duckdb.conn.execute(stats_sql).fetchone()

            if result:
                return {
                    'total': result[0] or 0,
                    'completed': result[1] or 0,
                    'failed': result[2] or 0,
                    'running': result[3] or 0,
                    'avg_rows': result[4] or 0,
                    'total_rows_synced': result[5] or 0
                }
            return {}

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            raise

    def delete_old_logs(self, days: int = 30) -> int:
        """
        오래된 로그 삭제

        Args:
            days: 보관 기간 (일)

        Returns:
            삭제된 로그 수
        """
        delete_sql = f"""
        DELETE FROM {self.TABLE_NAME}
        WHERE start_time < CURRENT_TIMESTAMP - INTERVAL '{days} days'
        """

        try:
            result = self.duckdb.conn.execute(delete_sql)
            deleted_count = result.fetchone()[0] if result else 0
            self.logger.info(f"Deleted {deleted_count} old logs (older than {days} days)")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to delete old logs: {e}")
            raise

    def _row_to_sync_log(self, row: tuple) -> SyncLog:
        """
        DB 행을 SyncLog 객체로 변환

        Args:
            row: (id, sync_id, table_name, sync_type, status, start_time, end_time, total_rows, error_message)

        Returns:
            SyncLog 객체
        """
        return SyncLog(
            id=row[0],
            sync_id=row[1],
            table_name=row[2],
            sync_type=SyncType(row[3]),
            status=SyncStatus(row[4]),
            start_time=row[5],
            end_time=row[6],
            total_rows=row[7] or 0,
            error_message=row[8]
        )
