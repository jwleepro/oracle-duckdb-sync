"""
Session state management module for Streamlit app.

This module provides functions for initializing and managing Streamlit
session state variables.
"""

import queue

import streamlit as st

# Auto-refresh interval for sync progress (seconds)
SYNC_PROGRESS_REFRESH_INTERVAL = 2


def initialize_session_state():
    """
    Initialize all session state variables with default values.

    This function should be called at the start of the Streamlit app
    to ensure all required session state variables exist.
    """
    defaults = {
        'sync_status': 'idle',
        'sync_worker': None,
        'progress_queue': queue.Queue(),
        'sync_progress': {},
        'sync_result': {},
        'sync_error': {},
        'sync_lock': None,
        'query_result': None,
        'converted_data_cache': {},  # Cache for converted DataFrames by table
        'cache_metadata': {},  # Metadata for each cached table (last_timestamp, row_count, etc.)
        # Navigation state
        'current_page': '/dashboard',  # Current page path
        'menu_expanded': {'user': True, 'admin': False}  # Menu expansion state
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def release_sync_lock():
    """
    Release the sync lock if it exists.

    This is a helper function to avoid code duplication when releasing
    the lock on completion or error.
    """
    if 'sync_lock' in st.session_state and st.session_state.sync_lock:
        st.session_state.sync_lock.release()
        st.session_state.sync_lock = None
