"""
동기화 로그 데이터 모델

동기화 작업의 이력과 통계를 관리하기 위한 모델입니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SyncType(Enum):
    """동기화 유형"""
    TEST = "test"
    FULL = "full"
    INCREMENTAL = "incremental"


class SyncStatus(Enum):
    """동기화 상태"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class SyncLog:
    """
    동기화 로그 데이터 클래스

    Attributes:
        id: 로그 고유 ID (자동 생성)
        sync_id: 동기화 작업 고유 ID (UUID)
        table_name: Oracle 테이블명
        sync_type: 동기화 유형 (test, full, incremental)
        status: 동기화 상태
        start_time: 시작 시각
        end_time: 종료 시각 (진행 중이면 None)
        total_rows: 처리된 총 행 수
        error_message: 에러 메시지 (실패 시)
    """
    sync_id: str
    table_name: str
    sync_type: SyncType
    status: SyncStatus
    start_time: datetime
    id: Optional[int] = None
    end_time: Optional[datetime] = None
    total_rows: int = 0
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'sync_id': self.sync_id,
            'table_name': self.table_name,
            'sync_type': self.sync_type.value if isinstance(self.sync_type, SyncType) else self.sync_type,
            'status': self.status.value if isinstance(self.status, SyncStatus) else self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_rows': self.total_rows,
            'error_message': self.error_message
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SyncLog':
        """딕셔너리로부터 생성"""
        return cls(
            id=data.get('id'),
            sync_id=data['sync_id'],
            table_name=data['table_name'],
            sync_type=SyncType(data['sync_type']) if isinstance(data['sync_type'], str) else data['sync_type'],
            status=SyncStatus(data['status']) if isinstance(data['status'], str) else data['status'],
            start_time=datetime.fromisoformat(data['start_time']) if isinstance(data['start_time'], str) else data['start_time'],
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') and isinstance(data['end_time'], str) else data.get('end_time'),
            total_rows=data.get('total_rows', 0),
            error_message=data.get('error_message')
        )

    def get_duration_seconds(self) -> Optional[float]:
        """
        동기화 소요 시간을 초 단위로 반환

        Returns:
            소요 시간 (초), 종료되지 않았으면 None
        """
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def is_completed(self) -> bool:
        """완료 여부"""
        return self.status == SyncStatus.COMPLETED

    def is_failed(self) -> bool:
        """실패 여부"""
        return self.status == SyncStatus.FAILED

    def is_running(self) -> bool:
        """실행 중 여부"""
        return self.status == SyncStatus.RUNNING
