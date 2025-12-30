"""UI components for Streamlit dashboard."""

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

__all__ = [
    # App
    'main',
    # Handlers
    'handle_test_sync',
    'handle_full_sync',
    'render_sync_status_ui',
    # Session state
    'initialize_session_state',
    'release_sync_lock',
    'SYNC_PROGRESS_REFRESH_INTERVAL',
    # Visualization
    'calculate_y_axis_range',
    'filter_dataframe_by_range',
    'render_data_visualization'
]
