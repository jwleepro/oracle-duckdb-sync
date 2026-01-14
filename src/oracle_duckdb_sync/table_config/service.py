"""
테이블 설정 서비스

멀티 테이블 동기화 설정 관리 비즈니스 로직을 담당합니다.
"""

from typing import List, Optional, Tuple

from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.table_config.models import TableConfig
from oracle_duckdb_sync.table_config.repository import TableConfigRepository


class TableConfigService:
    """
    테이블 설정 서비스

    테이블 설정 생성, 유효성 검증, 동기화 대상 관리를 담당합니다.
    """

    def __init__(self, config: Config = None, duckdb_source: DuckDBSource = None):
        """
        Args:
            config: 애플리케이션 설정
            duckdb_source: DuckDB 소스 객체
        """
        self.logger = setup_logger('TableConfigService')
        self.config_repo = TableConfigRepository(config=config, duckdb_source=duckdb_source)

    def create_table_config(
        self,
        oracle_schema: str,
        oracle_table: str,
        duckdb_table: str,
        primary_key: str,
        time_column: str = "",
        batch_size: int = 10000,
        description: str = None
    ) -> Tuple[bool, str, Optional[TableConfig]]:
        """
        새 테이블 설정 생성

        Args:
            oracle_schema: Oracle 스키마명
            oracle_table: Oracle 테이블명
            duckdb_table: DuckDB 테이블명
            primary_key: 기본 키 컬럼명
            time_column: 시간 컬럼명
            batch_size: 배치 크기
            description: 설명

        Returns:
            (성공 여부, 메시지, TableConfig 객체 또는 None)
        """
        # 중복 체크
        if self.config_repo.exists(oracle_schema, oracle_table):
            return False, f"{oracle_schema}.{oracle_table} 설정이 이미 존재합니다.", None

        # TableConfig 객체 생성
        table_config = TableConfig(
            oracle_schema=oracle_schema,
            oracle_table=oracle_table,
            duckdb_table=duckdb_table,
            primary_key=primary_key,
            time_column=time_column,
            batch_size=batch_size,
            description=description
        )

        # 유효성 검증
        is_valid, msg = table_config.validate()
        if not is_valid:
            return False, msg, None

        # 저장
        try:
            created_config = self.config_repo.create(table_config)
            self.logger.info(f"Created table config: {created_config.get_oracle_full_name()}")
            return True, "테이블 설정이 생성되었습니다.", created_config

        except Exception as e:
            self.logger.error(f"Failed to create table config: {e}")
            return False, f"생성 실패: {str(e)}", None

    def update_table_config(self, table_config: TableConfig) -> Tuple[bool, str]:
        """
        테이블 설정 업데이트

        Args:
            table_config: 업데이트할 TableConfig 객체

        Returns:
            (성공 여부, 메시지)
        """
        if not table_config.id:
            return False, "설정 ID가 필요합니다."

        # 유효성 검증
        is_valid, msg = table_config.validate()
        if not is_valid:
            return False, msg

        try:
            self.config_repo.update(table_config)
            self.logger.info(f"Updated table config: {table_config.get_oracle_full_name()}")
            return True, "테이블 설정이 업데이트되었습니다."

        except Exception as e:
            self.logger.error(f"Failed to update table config: {e}")
            return False, f"업데이트 실패: {str(e)}"

    def delete_table_config(self, config_id: int) -> Tuple[bool, str]:
        """
        테이블 설정 삭제

        Args:
            config_id: 설정 ID

        Returns:
            (성공 여부, 메시지)
        """
        config = self.config_repo.get_by_id(config_id)
        if not config:
            return False, "설정을 찾을 수 없습니다."

        try:
            self.config_repo.delete(config_id)
            self.logger.info(f"Deleted table config: {config.get_oracle_full_name()}")
            return True, "테이블 설정이 삭제되었습니다."

        except Exception as e:
            self.logger.error(f"Failed to delete table config: {e}")
            return False, f"삭제 실패: {str(e)}"

    def toggle_sync(self, config_id: int, enabled: bool) -> Tuple[bool, str]:
        """
        동기화 활성화/비활성화

        Args:
            config_id: 설정 ID
            enabled: 활성화 여부

        Returns:
            (성공 여부, 메시지)
        """
        config = self.config_repo.get_by_id(config_id)
        if not config:
            return False, "설정을 찾을 수 없습니다."

        try:
            self.config_repo.toggle_sync_enabled(config_id, enabled)
            status = "활성화" if enabled else "비활성화"
            self.logger.info(f"Toggled sync for {config.get_oracle_full_name()}: {status}")
            return True, f"동기화가 {status}되었습니다."

        except Exception as e:
            self.logger.error(f"Failed to toggle sync: {e}")
            return False, f"토글 실패: {str(e)}"

    def get_table_config(self, config_id: int) -> Optional[TableConfig]:
        """설정 ID로 조회"""
        return self.config_repo.get_by_id(config_id)

    def get_table_config_by_oracle_table(
        self,
        oracle_schema: str,
        oracle_table: str
    ) -> Optional[TableConfig]:
        """Oracle 테이블명으로 조회"""
        return self.config_repo.get_by_oracle_table(oracle_schema, oracle_table)

    def get_all_configs(self, enabled_only: bool = False) -> List[TableConfig]:
        """모든 설정 조회"""
        return self.config_repo.get_all(enabled_only=enabled_only)

    def get_sync_targets(self) -> List[TableConfig]:
        """
        동기화 대상 테이블 목록 조회

        Returns:
            활성화된 TableConfig 리스트
        """
        return self.config_repo.get_enabled_configs()

    def import_from_env(self, config: Config) -> Tuple[bool, str, Optional[TableConfig]]:
        """
        환경변수(.env)에서 테이블 설정 가져오기

        Args:
            config: 애플리케이션 설정

        Returns:
            (성공 여부, 메시지, TableConfig 객체 또는 None)
        """
        # 환경변수에서 설정 추출
        oracle_schema = config.sync_oracle_schema
        oracle_table = config.sync_oracle_table
        duckdb_table = config.sync_duckdb_table
        primary_key = config.sync_primary_key
        time_column = config.sync_time_column

        if not oracle_schema or not oracle_table:
            return False, "환경변수에 Oracle 테이블 정보가 없습니다.", None

        # DuckDB 테이블명이 없으면 Oracle 테이블명의 소문자 사용
        if not duckdb_table:
            duckdb_table = oracle_table.lower()

        # 기본 키가 없으면 경고
        if not primary_key:
            return False, "기본 키(PRIMARY_KEY)가 설정되지 않았습니다.", None

        # 이미 존재하는지 확인
        existing = self.config_repo.get_by_oracle_table(oracle_schema, oracle_table)
        if existing:
            return False, f"{oracle_schema}.{oracle_table} 설정이 이미 존재합니다.", existing

        # 생성
        return self.create_table_config(
            oracle_schema=oracle_schema,
            oracle_table=oracle_table,
            duckdb_table=duckdb_table,
            primary_key=primary_key,
            time_column=time_column,
            description="환경변수에서 가져온 설정"
        )

    def validate_config(self, table_config: TableConfig) -> Tuple[bool, List[str]]:
        """
        테이블 설정의 상세 유효성 검증

        Args:
            table_config: 검증할 TableConfig 객체

        Returns:
            (유효 여부, 에러 메시지 리스트)
        """
        errors = []

        # 기본 검증
        is_valid, msg = table_config.validate()
        if not is_valid:
            errors.append(msg)

        # 추가 검증
        # 1. 테이블명 형식 검증
        if not table_config.oracle_table.replace('_', '').isalnum():
            errors.append("Oracle 테이블명에 특수문자는 사용할 수 없습니다.")

        if not table_config.duckdb_table.replace('_', '').isalnum():
            errors.append("DuckDB 테이블명에 특수문자는 사용할 수 없습니다.")

        # 2. 컬럼명 형식 검증
        if not table_config.primary_key.replace('_', '').isalnum():
            errors.append("기본 키 컬럼명에 특수문자는 사용할 수 없습니다.")

        if table_config.time_column and not table_config.time_column.replace('_', '').isalnum():
            errors.append("시간 컬럼명에 특수문자는 사용할 수 없습니다.")

        return len(errors) == 0, errors
