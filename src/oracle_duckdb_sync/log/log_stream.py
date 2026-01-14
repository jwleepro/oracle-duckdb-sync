"""
실시간 로그 스트리밍 모듈

Queue 기반의 실시간 로그 핸들러를 제공하여
UI에서 동기화 작업의 로그를 실시간으로 확인할 수 있습니다.
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class LogEntry:
    """
    로그 엔트리 데이터 클래스

    Attributes:
        timestamp: 로그 발생 시각
        level: 로그 레벨 (INFO, WARNING, ERROR, DEBUG)
        source: 로그 소스 (SyncEngine, SyncWorker 등)
        message: 로그 메시지
        details: 추가 상세 정보 (선택적)
    """
    timestamp: datetime
    level: str
    source: str
    message: str
    details: Optional[dict] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'level': self.level,
            'source': self.source,
            'message': self.message,
            'details': self.details
        }

    def __str__(self) -> str:
        """문자열 표현"""
        time_str = self.timestamp.strftime('%H:%M:%S')
        return f"[{time_str}] [{self.level}] {self.source}: {self.message}"


class LogStreamHandler(logging.Handler):
    """
    Queue 기반 실시간 로그 핸들러

    메모리 내 deque를 사용하여 최근 로그를 저장하고,
    UI에서 실시간으로 로그를 조회할 수 있도록 합니다.

    Attributes:
        log_queue: 최근 로그를 저장하는 deque (maxlen으로 자동 관리)
        max_size: 저장할 최대 로그 수
    """

    def __init__(self, max_size: int = 100, level: int = logging.INFO):
        """
        Args:
            max_size: 저장할 최대 로그 수 (기본값: 100)
            level: 최소 로그 레벨 (기본값: INFO)
        """
        super().__init__(level)
        self.log_queue: deque[LogEntry] = deque(maxlen=max_size)
        self.max_size = max_size

    def emit(self, record: logging.LogRecord):
        """
        로그 레코드를 받아서 LogEntry로 변환하여 저장

        Args:
            record: Python logging 레코드
        """
        try:
            # LogRecord를 LogEntry로 변환
            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created),
                level=record.levelname,
                source=record.name,
                message=self.format(record),
                details={
                    'pathname': record.pathname,
                    'lineno': record.lineno,
                    'funcName': record.funcName,
                } if record.exc_info else None
            )

            # Queue에 추가 (deque의 maxlen이 자동으로 관리)
            self.log_queue.append(entry)

        except Exception as e:
            # 핸들러 자체에서 에러 발생 시 무시 (로그 시스템 보호)
            self.handleError(record)

    def get_logs(self, count: Optional[int] = None, level: Optional[str] = None) -> list[LogEntry]:
        """
        저장된 로그를 조회

        Args:
            count: 조회할 로그 수 (None이면 전체)
            level: 필터링할 로그 레벨 (None이면 전체)

        Returns:
            LogEntry 리스트 (최신 로그가 마지막)
        """
        logs = list(self.log_queue)

        # 레벨 필터링
        if level:
            logs = [log for log in logs if log.level == level]

        # 개수 제한
        if count:
            logs = logs[-count:]

        return logs

    def clear(self):
        """저장된 모든 로그 삭제"""
        self.log_queue.clear()

    def get_count(self) -> int:
        """저장된 로그 수 반환"""
        return len(self.log_queue)

    def get_latest(self, count: int = 10) -> list[LogEntry]:
        """
        최근 N개의 로그 조회

        Args:
            count: 조회할 로그 수

        Returns:
            최근 LogEntry 리스트
        """
        return list(self.log_queue)[-count:]


# ============================================================================
# 전역 로그 스트림 핸들러 인스턴스
# ============================================================================

_global_stream_handler: Optional[LogStreamHandler] = None


def get_log_stream_handler(max_size: int = 100) -> LogStreamHandler:
    """
    전역 로그 스트림 핸들러를 가져오거나 생성

    싱글톤 패턴으로 하나의 핸들러만 유지하여
    모든 로거가 동일한 로그 큐를 공유합니다.

    Args:
        max_size: 저장할 최대 로그 수 (첫 생성 시에만 적용)

    Returns:
        LogStreamHandler 인스턴스
    """
    global _global_stream_handler

    if _global_stream_handler is None:
        _global_stream_handler = LogStreamHandler(max_size=max_size)

    return _global_stream_handler


def attach_stream_handler_to_logger(logger_name: str = None, max_size: int = 100):
    """
    특정 로거에 스트림 핸들러 연결

    Args:
        logger_name: 로거 이름 (None이면 root logger)
        max_size: 저장할 최대 로그 수
    """
    logger = logging.getLogger(logger_name)
    handler = get_log_stream_handler(max_size)

    # 중복 방지: 이미 추가되어 있지 않은 경우에만 추가
    if handler not in logger.handlers:
        logger.addHandler(handler)


def detach_stream_handler_from_logger(logger_name: str = None):
    """
    특정 로거에서 스트림 핸들러 제거

    Args:
        logger_name: 로거 이름 (None이면 root logger)
    """
    global _global_stream_handler

    if _global_stream_handler is None:
        return

    logger = logging.getLogger(logger_name)
    if _global_stream_handler in logger.handlers:
        logger.removeHandler(_global_stream_handler)
