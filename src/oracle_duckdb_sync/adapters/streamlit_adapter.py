"""
Streamlit Adapter - Streamlit-specific implementation of UI interfaces.

This adapter allows the application to work with Streamlit without
the core business logic depending on it.
"""

from typing import Any, Dict, List, Optional
from contextlib import contextmanager
import streamlit as st

from ..application.ui_presenter import (
    UIPresenter, 
    SessionStateManager, 
    LayoutManager,
    MessageContext
)


class StreamlitPresenter(UIPresenter):
    """Streamlit-specific implementation of UIPresenter."""
    
    def show_message(self, context: MessageContext) -> None:
        """Display a message using Streamlit."""
        message_func = {
            'info': st.info,
            'warning': st.warning,
            'error': st.error,
            'success': st.success
        }.get(context.level, st.info)
        
        message_func(context.message)
        
        if context.expandable and context.details:
            with st.expander("상세 정보"):
                st.code(context.details)
    
    def show_progress(self, percentage: float, message: str) -> None:
        """Display progress bar."""
        st.progress(min(percentage, 1.0))
        st.text(message)
    
    @contextmanager
    def show_spinner(self, message: str):
        """Show loading spinner."""
        with st.spinner(message):
            yield
    
    def get_user_input(self, 
                       label: str, 
                       default_value: Any = None,
                       input_type: str = 'text',
                       **kwargs) -> Any:
        """Get input from user."""
        if input_type == 'text':
            return st.text_input(label, value=default_value or '', **kwargs)
        elif input_type == 'number':
            return st.number_input(label, value=default_value or 0, **kwargs)
        elif input_type == 'select':
            options = kwargs.pop('options', [])
            return st.selectbox(label, options, **kwargs)
        elif input_type == 'multiselect':
            options = kwargs.pop('options', [])
            return st.multiselect(label, options, **kwargs)
        elif input_type == 'radio':
            options = kwargs.pop('options', [])
            return st.radio(label, options, **kwargs)
        elif input_type == 'checkbox':
            return st.checkbox(label, value=default_value or False, **kwargs)
        else:
            return st.text_input(label, value=default_value or '', **kwargs)
    
    def show_button(self, label: str, disabled: bool = False, **kwargs) -> bool:
        """Show button and return True if clicked."""
        return st.button(label, disabled=disabled, **kwargs)
    
    def show_dataframe(self, df: Any, max_rows: Optional[int] = None) -> None:
        """Display a DataFrame."""
        if max_rows and len(df) > max_rows:
            st.warning(f"⚠️ 성능을 위해 {max_rows:,}행만 표시합니다. (전체: {len(df):,}행)")
            st.dataframe(df.head(max_rows))
        else:
            st.dataframe(df)
    
    def show_chart(self, chart_data: Any, **kwargs) -> None:
        """Display a chart."""
        st.plotly_chart(chart_data, use_container_width=True, **kwargs)
    
    def trigger_rerun(self) -> None:
        """Trigger Streamlit rerun."""
        st.rerun()


class StreamlitSessionState(SessionStateManager):
    """Streamlit-specific session state manager."""
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from Streamlit session state."""
        return st.session_state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set value in Streamlit session state."""
        st.session_state[key] = value
    
    def has(self, key: str) -> bool:
        """Check if key exists."""
        return key in st.session_state
    
    def delete(self, key: str) -> None:
        """Remove key from session state."""
        if key in st.session_state:
            del st.session_state[key]
    
    def clear_pattern(self, pattern: str) -> None:
        """Clear all keys matching a pattern."""
        keys_to_delete = [k for k in st.session_state.keys() if pattern in k]
        for key in keys_to_delete:
            del st.session_state[key]


class StreamlitLayout(LayoutManager):
    """Streamlit-specific layout manager."""
    
    @contextmanager
    def create_columns(self, ratios: List[int]):
        """Create column layout."""
        cols = st.columns(ratios)
        yield cols
    
    @contextmanager
    def create_expander(self, title: str, expanded: bool = False):
        """Create expandable section."""
        with st.expander(title, expanded=expanded) as exp:
            yield exp
    
    @contextmanager
    def create_sidebar(self):
        """Get sidebar context."""
        # Streamlit sidebar is global, so we just yield a marker
        yield st.sidebar
    
    def add_divider(self) -> None:
        """Add a visual divider."""
        st.markdown("---")


class StreamlitAdapter:
    """
    Main adapter class that combines all Streamlit-specific implementations.
    
    This provides a single point of access to all UI functionality.
    """
    
    def __init__(self):
        self.presenter = StreamlitPresenter()
        self.session = StreamlitSessionState()
        self.layout = StreamlitLayout()
    
    @staticmethod
    def configure_page(**kwargs):
        """Configure Streamlit page settings."""
        st.set_page_config(**kwargs)
    
    @staticmethod
    def set_title(title: str):
        """Set page title."""
        st.title(title)
    
    @staticmethod
    def set_header(header: str):
        """Set header."""
        st.header(header)
    
    @staticmethod
    def set_subheader(subheader: str):
        """Set subheader."""
        st.subheader(subheader)
