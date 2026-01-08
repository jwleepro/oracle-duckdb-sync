"""
UI Helper Functions - Display messages from data layer using StreamlitAdapter.

This module provides helper functions to display messages returned by
UI-independent data layer functions.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from ..adapters.streamlit_adapter import StreamlitAdapter
from ..application.ui_presenter import MessageContext


# Date preset constants
class DatePresets:
    """Constants for date range preset selections."""
    LAST_7_DAYS = "최근 7일"
    LAST_30_DAYS = "최근 30일"
    LAST_90_DAYS = "최근 90일"
    ALL = "전체"


def display_messages(messages: List[Dict[str, str]], adapter: StreamlitAdapter) -> None:
    """
    Display a list of messages using the UI adapter.
    
    Args:
        messages: List of message dictionaries with 'level' and 'message' keys
        adapter: StreamlitAdapter instance
    """
    for msg in messages:
        level = msg.get('level', 'info')
        message = msg.get('message', '')
        
        if level == 'spinner':
            # Spinner messages are handled differently
            continue
        elif level == 'expander':
            # Expandable content
            title = msg.get('title', 'Details')
            content = msg.get('content', '')
            with adapter.layout.create_expander(title):
                import streamlit as st
                st.text(content)
        elif level == 'code':
            # Code block
            import streamlit as st
            st.code(msg.get('content', ''))
        else:
            # Regular message (info, warning, error, success)
            context = MessageContext(
                level=level,
                message=message
            )
            adapter.presenter.show_message(context)


def display_query_result_messages(result: Dict[str, Any], adapter: StreamlitAdapter) -> None:
    """
    Display messages from a query result dictionary.
    
    Args:
        result: Query result dictionary containing 'messages' key
        adapter: StreamlitAdapter instance
    """
    if 'messages' in result and result['messages']:
        display_messages(result['messages'], adapter)


def show_table_list(tables: List[str], adapter: StreamlitAdapter) -> None:
    """
    Display available tables list.
    
    Args:
        tables: List of table names
        adapter: StreamlitAdapter instance
    """
    if tables:
        context = MessageContext(
            level='info',
            message=f"📊 사용 가능한 테이블: {', '.join(tables)}"
        )
    else:
        context = MessageContext(
            level='warning',
            message="⚠️ DuckDB에 테이블이 없습니다. 먼저 '지금 동기화 실행'을 클릭하세요."
        )
    
    adapter.presenter.show_message(context)


def show_row_count(count: int, table_name: str, adapter: StreamlitAdapter) -> None:
    """
    Display table row count.
    
    Args:
        count: Number of rows
        table_name: Table name
        adapter: StreamlitAdapter instance
    """
    context = MessageContext(
        level='info',
        message=f"📊 테이블 '{table_name}': {count:,}행"
    )
    adapter.presenter.show_message(context)


def show_conversion_results(conversions: Dict[str, Any], adapter: StreamlitAdapter) -> None:
    """
    Display type conversion results.

    Args:
        conversions: Dictionary of column conversions
        adapter: StreamlitAdapter instance
    """
    if not conversions:
        return

    conversion_details = []
    for col, conversion_info in conversions.items():
        if isinstance(conversion_info, tuple):
            old_type, new_type = conversion_info
            conversion_details.append(f"  • {col}: {old_type} → {new_type}")
        else:
            conversion_details.append(f"  • {col}: {conversion_info}")

    with adapter.layout.create_expander("🔄 자동 타입 변환 결과"):
        import streamlit as st
        st.text("\n".join(conversion_details))


def get_preset_date_range(preset: str) -> Optional[Tuple[datetime, datetime]]:
    """
    Get date range based on preset period selection.

    Args:
        preset: Preset period name (use DatePresets constants)

    Returns:
        Tuple of (start_date, end_date) as datetime objects, or None for "전체"
    """
    today = datetime.now()

    # Map presets to number of days
    preset_days = {
        DatePresets.LAST_7_DAYS: 7,
        DatePresets.LAST_30_DAYS: 30,
        DatePresets.LAST_90_DAYS: 90,
    }

    if preset in preset_days:
        days = preset_days[preset]
        start_date = today - timedelta(days=days)
        return (start_date, today)
    elif preset == DatePresets.ALL:
        return None
    else:
        # Default to None for unknown presets
        return None
