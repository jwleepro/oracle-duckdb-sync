"""UI components for Streamlit dashboard."""

from oracle_duckdb_sync.ui.app import main
from oracle_duckdb_sync.ui.handlers import (
    validate_table_name,
    acquire_sync_lock_with_ui,
    start_sync_worker,
    handle_sync_error,
    handle_test_sync,
    handle_full_sync,
    render_sync_status_ui,
    check_progress
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

__all__ = [
    # App
    'main',
    # Handlers
    'validate_table_name',
    'acquire_sync_lock_with_ui',
    'start_sync_worker',
    'handle_sync_error',
    'handle_test_sync',
    'handle_full_sync',
    'render_sync_status_ui',
    'check_progress',
    # Session state
    'initialize_session_state',
    'release_sync_lock',
    'SYNC_PROGRESS_REFRESH_INTERVAL',
    # Visualization
    'calculate_y_axis_range',
    'filter_dataframe_by_range',
    'render_data_visualization'
]
