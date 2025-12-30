"""
Oracle-DuckDB Sync Package

Backward compatibility layer for legacy imports.
New code should import from subpackages directly.
"""

# Keep widely-used modules at root
from oracle_duckdb_sync.config import Config, load_config
from oracle_duckdb_sync.logger import setup_logger

# Backward compatibility: re-export all public APIs from subpackages
from oracle_duckdb_sync.ui.app import main
from oracle_duckdb_sync.ui.handlers import (
    handle_test_sync,
    handle_full_sync,
    render_sync_status_ui
)
from oracle_duckdb_sync.ui.session_state import (
    initialize_session_state,
    release_sync_lock,
    SYNC_PROGRESS_REFRESH_INTERVAL
)
from oracle_duckdb_sync.ui.visualization import (
    calculate_y_axis_range,
    filter_dataframe_by_range,
    render_data_visualization
)

from oracle_duckdb_sync.database.oracle_source import OracleSource, datetime_handler
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.database.sync_engine import SyncEngine

from oracle_duckdb_sync.scheduler.scheduler import SyncScheduler
from oracle_duckdb_sync.scheduler.sync_worker import SyncWorker

from oracle_duckdb_sync.data.converter import (
    is_numeric_string,
    is_datetime_string,
    convert_to_numeric,
    convert_to_datetime,
    detect_column_type,
    convert_column_to_type,
    detect_and_convert_types,
    detect_convertible_columns,
    convert_selected_columns
)
from oracle_duckdb_sync.data.query import (
    get_available_tables,
    determine_default_table_name,
    get_table_row_count,
    query_duckdb_table,
    query_duckdb_table_with_conversion_ui,
    query_duckdb_table_cached,
    query_duckdb_table_aggregated
)
from oracle_duckdb_sync.data.lttb import lttb_downsample, lttb_downsample_multi_y

from oracle_duckdb_sync.state.sync_state import SyncLock
from oracle_duckdb_sync.state.file_manager import StateFileManager

__all__ = [
    # Config & Logger
    'Config', 'load_config', 'setup_logger',

    # UI
    'main',
    'handle_test_sync', 'handle_full_sync', 'render_sync_status_ui',
    'initialize_session_state', 'release_sync_lock', 'SYNC_PROGRESS_REFRESH_INTERVAL',
    'calculate_y_axis_range', 'filter_dataframe_by_range', 'render_data_visualization',

    # Database
    'OracleSource', 'datetime_handler', 'DuckDBSource', 'SyncEngine',

    # Scheduler
    'SyncScheduler', 'SyncWorker',

    # Data
    'is_numeric_string', 'is_datetime_string', 'convert_to_numeric', 'convert_to_datetime',
    'detect_column_type', 'convert_column_to_type', 'detect_and_convert_types',
    'detect_convertible_columns', 'convert_selected_columns',
    'get_available_tables', 'determine_default_table_name', 'get_table_row_count',
    'query_duckdb_table', 'query_duckdb_table_with_conversion_ui',
    'query_duckdb_table_cached', 'query_duckdb_table_aggregated',
    'lttb_downsample', 'lttb_downsample_multi_y',

    # State
    'SyncLock', 'StateFileManager'
]
