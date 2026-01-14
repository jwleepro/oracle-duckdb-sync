"""
Streamlit query presenter.

This module provides Streamlit-specific presentation logic for query results,
keeping all Streamlit dependencies isolated in this adapter layer.
"""

import pandas as pd
import streamlit as st
from typing import Optional

from oracle_duckdb_sync.adapters.query_message_formatter import (
    QueryMessage,
    QueryMessageFormatter
)
from oracle_duckdb_sync.application.enhanced_query_service import (
    EnhancedQueryService,
    QueryServiceResult
)
from oracle_duckdb_sync.config.query_constants import QUERY_CONSTANTS
from oracle_duckdb_sync.log.logger import setup_logger


# Set up logger
presenter_logger = setup_logger('StreamlitQueryPresenter')


class StreamlitQueryPresenter:
    """
    Presents query results in Streamlit UI.

    This class handles all Streamlit-specific UI rendering, isolating
    framework dependencies from business logic.
    """

    def __init__(self, service: EnhancedQueryService):
        """
        Initialize StreamlitQueryPresenter with a query service.

        Args:
            service: EnhancedQueryService for executing queries
        """
        self.service = service
        self.formatter = QueryMessageFormatter()
        self.logger = presenter_logger

    def present_query_with_caching(
        self,
        table_name: str,
        limit: int = QUERY_CONSTANTS.DEFAULT_QUERY_LIMIT,
        time_column: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Execute query with caching and display results in Streamlit.

        This method:
        1. Shows query information messages
        2. Executes query via service
        3. Displays success/error messages
        4. Shows type conversion details
        5. Returns the DataFrame for further display

        Args:
            table_name: Name of the table to query
            limit: Maximum rows for initial load
            time_column: Timestamp column for incremental loading

        Returns:
            DataFrame if successful, None if error

        Example:
            >>> presenter = StreamlitQueryPresenter(service)
            >>> df = presenter.present_query_with_caching("users", limit=1000, time_column="created_at")
            >>> if df is not None:
            ...     st.dataframe(df)
        """
        self.logger.info(f"Presenting query: table='{table_name}', limit={limit}")

        # Check if incremental mode will be used
        cache_info = self.service.get_cache_info(table_name)
        is_incremental = (
            time_column is not None
            and cache_info is not None
            and cache_info.last_timestamp is not None
        )

        # Show query information
        if is_incremental:
            msg = self.formatter.format_incremental_query_info(
                table_name, str(cache_info.last_timestamp)
            )
        elif time_column:
            msg = self.formatter.format_initial_query_info(table_name, limit)
        else:
            msg = self.formatter.format_query_info(table_name, limit)

        self._display_message(msg)

        # Execute query
        result = self.service.query_with_caching(table_name, limit, time_column)

        # Display results
        if result.success:
            self._display_success_result(result)
            return result.df_converted
        else:
            self._display_error_result(result, table_name)
            return result.df_converted  # May be cached data on incremental error

    def present_query_with_conversion_ui(
        self,
        table_name: str,
        limit: int = QUERY_CONSTANTS.DEFAULT_QUERY_LIMIT,
        time_column: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Execute query and show UI for selecting type conversions.

        This method:
        1. Queries data with conversion suggestions
        2. Shows checkboxes for each convertible column
        3. Applies selected conversions
        4. Returns the converted DataFrame

        Args:
            table_name: Name of the table to query
            limit: Maximum rows to return
            time_column: Timestamp column for incremental loading

        Returns:
            DataFrame with applied conversions, or None if error

        Example:
            >>> presenter = StreamlitQueryPresenter(service)
            >>> df = presenter.present_query_with_conversion_ui("users", limit=100)
            >>> if df is not None:
            ...     st.dataframe(df)
        """
        self.logger.info(f"Presenting query with conversion UI: table='{table_name}'")

        # Show query info
        msg = self.formatter.format_query_info(table_name, limit)
        self._display_message(msg)

        # Get conversion suggestions
        result = self.service.query_with_conversion_options(table_name, limit, time_column)

        if not result.success:
            self._display_error_result(result, table_name)
            return None

        # Display conversion UI
        if result.suggestions:
            st.info(f"💡 {len(result.suggestions)}개의 컬럼을 자동 변환할 수 있습니다.")

            selected_conversions = self._show_conversion_selection_ui(result.suggestions)

            if selected_conversions:
                # Apply selected conversions
                with st.spinner(f"선택한 {len(selected_conversions)}개 컬럼 변환 중..."):
                    result = self.service.query_with_caching(
                        table_name, limit, time_column,
                        selected_conversions=selected_conversions
                    )

                if result.success and result.conversions:
                    msg = self.formatter.format_type_conversions(
                        result.conversions, result.is_incremental
                    )
                    self._display_message(msg)

                    st.success(f"✅ {len(result.conversions)}개 컬럼 변환 완료")
        else:
            st.info("변환 가능한 컬럼이 없습니다.")

        return result.df_converted if result.success else None

    def _display_message(self, message: QueryMessage) -> None:
        """
        Display a single QueryMessage in Streamlit.

        Args:
            message: QueryMessage to display
        """
        if message.level == 'info':
            st.info(message.message)
        elif message.level == 'success':
            st.success(message.message)
        elif message.level == 'warning':
            st.warning(message.message)
        elif message.level == 'error':
            st.error(message.message)
        elif message.level == 'expander' and message.title:
            with st.expander(message.title):
                if message.content:
                    st.text(message.content)
        elif message.level == 'spinner' and message.message:
            # Note: spinner is handled differently (with context manager)
            # This is just for documentation
            pass

    def _display_messages(self, messages: list[QueryMessage]) -> None:
        """
        Display multiple QueryMessages in Streamlit.

        Args:
            messages: List of QueryMessages to display
        """
        for message in messages:
            self._display_message(message)

    def _display_success_result(self, result: QueryServiceResult) -> None:
        """
        Display successful query result.

        Args:
            result: QueryServiceResult with successful data
        """
        # Show success message
        if result.is_incremental:
            # Calculate new rows (for incremental display)
            cache_info = self.service.get_cache_info(
                # We need table_name, but it's not in result
                # This is a limitation - we'll just show row count
                ""
            )
            msg = self.formatter.format_success(result.row_count)
        else:
            msg = self.formatter.format_success(result.row_count)

        self._display_message(msg)

        # Show type conversions
        if result.conversions:
            msg = self.formatter.format_type_conversions(
                result.conversions, result.is_incremental
            )
            self._display_message(msg)

    def _display_error_result(self, result: QueryServiceResult, table_name: str) -> None:
        """
        Display error result.

        Args:
            result: QueryServiceResult with error
            table_name: Name of the table (for context)
        """
        if result.error == "No data returned":
            msg = self.formatter.format_no_data_warning(table_name)
            self._display_message(msg)

            # Try to show available tables
            try:
                from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
                # Note: We don't have access to duckdb_source here
                # This is a limitation of the current design
                pass
            except Exception:
                pass
        else:
            msg = self.formatter.format_error(result.error)
            self._display_message(msg)

    def _show_conversion_selection_ui(
        self,
        suggestions: dict[str, str]
    ) -> dict[str, str]:
        """
        Show UI for selecting type conversions.

        Args:
            suggestions: Dictionary mapping column names to suggested types

        Returns:
            Dictionary of selected conversions

        Example:
            >>> suggestions = {'price': 'numeric', 'date': 'datetime'}
            >>> selected = presenter._show_conversion_selection_ui(suggestions)
            >>> print(selected)
            {'price': 'numeric'}  # If user only selected price
        """
        st.write("**변환할 컬럼을 선택하세요:**")

        selected_conversions = {}

        # Group by conversion type
        numeric_cols = [col for col, t in suggestions.items() if t == 'numeric']
        datetime_cols = [col for col, t in suggestions.items() if t == 'datetime']

        # Create columns for layout
        col1, col2 = st.columns(2)

        with col1:
            if numeric_cols:
                st.write("**숫자 변환:**")
                for col in numeric_cols:
                    if st.checkbox(f"📊 {col}", key=f"conv_num_{col}"):
                        selected_conversions[col] = 'numeric'

        with col2:
            if datetime_cols:
                st.write("**날짜/시간 변환:**")
                for col in datetime_cols:
                    if st.checkbox(f"📅 {col}", key=f"conv_dt_{col}"):
                        selected_conversions[col] = 'datetime'

        return selected_conversions

    def show_cache_info(self, table_name: str) -> None:
        """
        Display cache information for a table.

        Args:
            table_name: Name of the table

        Example:
            >>> presenter.show_cache_info("users")
            # Displays cache metadata in Streamlit
        """
        cache_info = self.service.get_cache_info(table_name)

        if cache_info:
            with st.expander("💾 캐시 정보"):
                st.write(f"**마지막 타임스탬프:** {cache_info.last_timestamp}")
                st.write(f"**행 수:** {cache_info.row_count:,}")
                st.write(f"**마지막 업데이트:** {cache_info.last_update}")

                if cache_info.selected_conversions:
                    st.write(f"**선택된 변환:** {len(cache_info.selected_conversions)}개")
        else:
            st.info("캐시된 데이터가 없습니다.")

    def clear_cache_button(self, table_name: Optional[str] = None) -> None:
        """
        Show button to clear cache.

        Args:
            table_name: Optional table name. If None, clears all caches

        Example:
            >>> presenter.clear_cache_button("users")
            # Shows button, clears cache when clicked
        """
        label = f"🗑️ {table_name} 캐시 삭제" if table_name else "🗑️ 모든 캐시 삭제"

        if st.button(label):
            self.service.clear_cache(table_name)
            st.success("캐시가 삭제되었습니다.")
            st.rerun()
