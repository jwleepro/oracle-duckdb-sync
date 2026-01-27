"""
Adapters - Framework-specific implementations of application interfaces.

This package contains concrete implementations of application layer
interfaces for specific UI frameworks and external services.
"""

from oracle_duckdb_sync.adapters.streamlit_adapter import MessageContext, StreamlitAdapter

__all__ = ['MessageContext', 'StreamlitAdapter']
