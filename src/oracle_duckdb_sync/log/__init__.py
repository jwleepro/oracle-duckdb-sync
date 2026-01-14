"""Logging module for Oracle-DuckDB Sync."""

from oracle_duckdb_sync.log.logger import cleanup_logger, setup_logger
from oracle_duckdb_sync.log.log_stream import (
    LogEntry,
    LogStreamHandler,
    attach_stream_handler_to_logger,
    detach_stream_handler_from_logger,
    get_log_stream_handler,
)

__all__ = [
    'setup_logger',
    'cleanup_logger',
    'LogEntry',
    'LogStreamHandler',
    'get_log_stream_handler',
    'attach_stream_handler_to_logger',
    'detach_stream_handler_from_logger',
]
