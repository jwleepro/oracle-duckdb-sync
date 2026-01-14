"""
테이블 설정 데이터 모델

멀티 테이블 동기화 설정을 위한 모델입니다.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TableConfig:
    """
    테이블 동기화 설정 데이터 클래스

    Attributes:
        id: 설정 고유 ID (자동 생성)
        oracle_schema: Oracle 스키마명
        oracle_table: Oracle 테이블명
        duckdb_table: DuckDB 테이블명
        primary_key: 기본 키 컬럼명
        time_column: 증분 동기화용 시간 컬럼명
        sync_enabled: 동기화 활성화 여부
        batch_size: 배치 크기 (한 번에 처리할 행 수)
        description: 테이블 설명
    """
    oracle_schema: str
    oracle_table: str
    duckdb_table: str
    primary_key: str
    time_column: str = ""
    sync_enabled: bool = True
    batch_size: int = 10000
    id: Optional[int] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'oracle_schema': self.oracle_schema,
            'oracle_table': self.oracle_table,
            'duckdb_table': self.duckdb_table,
            'primary_key': self.primary_key,
            'time_column': self.time_column,
            'sync_enabled': self.sync_enabled,
            'batch_size': self.batch_size,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TableConfig':
        """딕셔너리로부터 생성"""
        return cls(
            id=data.get('id'),
            oracle_schema=data['oracle_schema'],
            oracle_table=data['oracle_table'],
            duckdb_table=data['duckdb_table'],
            primary_key=data['primary_key'],
            time_column=data.get('time_column', ''),
            sync_enabled=data.get('sync_enabled', True),
            batch_size=data.get('batch_size', 10000),
            description=data.get('description')
        )

    def get_oracle_full_name(self) -> str:
        """
        Oracle 전체 테이블명 반환 (스키마.테이블)

        Returns:
            스키마.테이블 형식의 문자열
        """
        return f"{self.oracle_schema}.{self.oracle_table}"

    def has_time_column(self) -> bool:
        """증분 동기화용 시간 컬럼 존재 여부"""
        return bool(self.time_column)

    def validate(self) -> tuple[bool, str]:
        """
        설정 유효성 검증

        Returns:
            (유효 여부, 메시지)
        """
        if not self.oracle_schema:
            return False, "Oracle 스키마는 필수입니다."

        if not self.oracle_table:
            return False, "Oracle 테이블명은 필수입니다."

        if not self.duckdb_table:
            return False, "DuckDB 테이블명은 필수입니다."

        if not self.primary_key:
            return False, "기본 키는 필수입니다."

        if self.batch_size <= 0:
            return False, "배치 크기는 1 이상이어야 합니다."

        if self.batch_size > 100000:
            return False, "배치 크기는 100,000 이하로 설정하세요."

        return True, "유효한 설정입니다."
