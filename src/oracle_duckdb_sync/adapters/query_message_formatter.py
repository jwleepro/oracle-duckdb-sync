"""
Query message formatter for UI presentation.

This module converts query service results into UI-friendly message formats,
decoupling business logic from presentation concerns.
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class QueryMessage:
    """
    Represents a single UI message.

    Attributes:
        level: Message severity level
        message: Main message text
        title: Optional title (for expandable sections)
        content: Optional detailed content (for expandable sections)
    """
    level: Literal['info', 'success', 'warning', 'error', 'spinner', 'expander']
    message: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None


class QueryMessageFormatter:
    """
    Formats query results into UI messages.

    This class provides static methods to convert various query operations
    into user-friendly messages for display in the UI.
    """

    @staticmethod
    def format_query_info(table_name: str, limit: int) -> QueryMessage:
        """
        Format basic query information message.

        Args:
            table_name: Name of the table being queried
            limit: Row limit for the query

        Returns:
            QueryMessage with query details

        Example:
            >>> msg = QueryMessageFormatter.format_query_info("users", 100)
            >>> print(msg.message)
            실행 쿼리: SELECT * FROM users LIMIT 100
        """
        return QueryMessage(
            level='info',
            message=f"실행 쿼리: SELECT * FROM {table_name} LIMIT {limit}"
        )

    @staticmethod
    def format_initial_query_info(table_name: str, limit: int) -> QueryMessage:
        """
        Format initial query information message.

        Args:
            table_name: Name of the table
            limit: Row limit

        Returns:
            QueryMessage for initial query

        Example:
            >>> msg = QueryMessageFormatter.format_initial_query_info("logs", 1000)
            >>> print(msg.message)
            🔍 초기 조회: logs (최대 1000행)
        """
        return QueryMessage(
            level='info',
            message=f"🔍 초기 조회: {table_name} (최대 {limit}행)"
        )

    @staticmethod
    def format_incremental_query_info(
        table_name: str,
        last_timestamp: str
    ) -> QueryMessage:
        """
        Format incremental query information message.

        Args:
            table_name: Name of the table
            last_timestamp: Last timestamp from previous query

        Returns:
            QueryMessage for incremental query

        Example:
            >>> msg = QueryMessageFormatter.format_incremental_query_info(
            ...     "logs", "2024-01-01 12:00:00"
            ... )
            >>> print(msg.message)
            🔄 증분 조회: logs (마지막: 2024-01-01 12:00:00)
        """
        return QueryMessage(
            level='info',
            message=f"🔄 증분 조회: {table_name} (마지막: {last_timestamp})"
        )

    @staticmethod
    def format_success(row_count: int) -> QueryMessage:
        """
        Format success message for completed query.

        Args:
            row_count: Number of rows returned

        Returns:
            QueryMessage indicating success

        Example:
            >>> msg = QueryMessageFormatter.format_success(1234)
            >>> print(msg.message)
            ✅ 조회 완료: 1234행
        """
        return QueryMessage(
            level='success',
            message=f"✅ 조회 완료: {row_count}행"
        )

    @staticmethod
    def format_incremental_success(new_rows: int, total_rows: int) -> QueryMessage:
        """
        Format success message for incremental update.

        Args:
            new_rows: Number of new rows loaded
            total_rows: Total rows after merge

        Returns:
            QueryMessage for incremental success

        Example:
            >>> msg = QueryMessageFormatter.format_incremental_success(50, 1284)
            >>> print(msg.message)
            ✅ 증분 업데이트 완료: +50행 → 총 1284행
        """
        return QueryMessage(
            level='success',
            message=f"✅ 증분 업데이트 완료: +{new_rows}행 → 총 {total_rows}행"
        )

    @staticmethod
    def format_no_new_data() -> QueryMessage:
        """
        Format message when no new data is available.

        Returns:
            QueryMessage indicating no new data

        Example:
            >>> msg = QueryMessageFormatter.format_no_new_data()
            >>> print(msg.message)
            ✅ 새로운 데이터가 없습니다. 캐시된 데이터를 사용합니다.
        """
        return QueryMessage(
            level='info',
            message="✅ 새로운 데이터가 없습니다. 캐시된 데이터를 사용합니다."
        )

    @staticmethod
    def format_new_data_found(row_count: int) -> QueryMessage:
        """
        Format message when new data is found.

        Args:
            row_count: Number of new rows found

        Returns:
            QueryMessage indicating new data

        Example:
            >>> msg = QueryMessageFormatter.format_new_data_found(50)
            >>> print(msg.message)
            📊 새 데이터 50행 발견, 변환 중...
        """
        return QueryMessage(
            level='info',
            message=f"📊 새 데이터 {row_count}행 발견, 변환 중..."
        )

    @staticmethod
    def format_type_conversions(
        conversions: dict[str, tuple[str, str]],
        is_incremental: bool = False
    ) -> QueryMessage:
        """
        Format type conversion summary as expandable message.

        Args:
            conversions: Dictionary mapping column names to (old_type, new_type) tuples
            is_incremental: Whether this is for incremental data

        Returns:
            QueryMessage with expandable conversion details

        Example:
            >>> conversions = {
            ...     'price': ('object', 'float64'),
            ...     'created_at': ('object', 'datetime64[ns]')
            ... }
            >>> msg = QueryMessageFormatter.format_type_conversions(conversions)
            >>> print(msg.title)
            🔄 타입 변환 결과 (2개 컬럼)
        """
        if not conversions:
            return QueryMessage(
                level='info',
                message="타입 변환이 적용되지 않았습니다."
            )

        # Build content
        lines = []
        for col, (old_type, new_type) in conversions.items():
            lines.append(f"  • {col}: {old_type} → {new_type}")
        content = "\n".join(lines)

        # Build title
        prefix = "증분 데이터 " if is_incremental else ""
        title = f"🔄 {prefix}타입 변환 결과 ({len(conversions)}개 컬럼)"

        return QueryMessage(
            level='expander',
            title=title,
            content=content
        )

    @staticmethod
    def format_conversion_spinner(row_count: int, is_incremental: bool = False) -> QueryMessage:
        """
        Format spinner message for type conversion in progress.

        Args:
            row_count: Number of rows being converted
            is_incremental: Whether this is incremental data

        Returns:
            QueryMessage with spinner

        Example:
            >>> msg = QueryMessageFormatter.format_conversion_spinner(1000)
            >>> print(msg.message)
            데이터 타입 자동 변환 중... (1000행)
        """
        prefix = "새 데이터 " if is_incremental else "데이터 "
        return QueryMessage(
            level='spinner',
            message=f"{prefix}타입 자동 변환 중... ({row_count}행)"
        )

    @staticmethod
    def format_error(error_message: str) -> QueryMessage:
        """
        Format error message.

        Args:
            error_message: Error description

        Returns:
            QueryMessage with error level

        Example:
            >>> msg = QueryMessageFormatter.format_error("Table not found")
            >>> print(msg.message)
            ❌ 오류: Table not found
        """
        return QueryMessage(
            level='error',
            message=f"❌ 오류: {error_message}"
        )

    @staticmethod
    def format_no_data_warning(table_name: str) -> QueryMessage:
        """
        Format warning when no data is returned.

        Args:
            table_name: Name of the table

        Returns:
            QueryMessage with warning level

        Example:
            >>> msg = QueryMessageFormatter.format_no_data_warning("users")
            >>> print(msg.message)
            조회 결과가 없습니다. 테이블 'users'이(가) 비어있거나 존재하지 않습니다.
        """
        return QueryMessage(
            level='warning',
            message=f"조회 결과가 없습니다. 테이블 '{table_name}'이(가) 비어있거나 존재하지 않습니다."
        )

    @staticmethod
    def format_available_tables(tables: list[str]) -> QueryMessage:
        """
        Format list of available tables.

        Args:
            tables: List of table names

        Returns:
            QueryMessage with available tables

        Example:
            >>> msg = QueryMessageFormatter.format_available_tables(["users", "logs"])
            >>> print(msg.message)
            📊 사용 가능한 테이블: users, logs
        """
        table_str = ", ".join(tables)
        return QueryMessage(
            level='info',
            message=f"📊 사용 가능한 테이블: {table_str}"
        )

    @staticmethod
    def format_conversion_suggestions(
        suggestions: dict[str, str]
    ) -> QueryMessage:
        """
        Format type conversion suggestions.

        Args:
            suggestions: Dictionary mapping column names to suggested types

        Returns:
            QueryMessage with conversion suggestions

        Example:
            >>> suggestions = {'price': 'numeric', 'date': 'datetime'}
            >>> msg = QueryMessageFormatter.format_conversion_suggestions(suggestions)
            >>> print(msg.title)
            💡 변환 가능한 컬럼 (2개)
        """
        if not suggestions:
            return QueryMessage(
                level='info',
                message="변환 가능한 컬럼이 없습니다."
            )

        # Build content
        lines = []
        for col, conv_type in suggestions.items():
            type_label = "숫자" if conv_type == "numeric" else "날짜"
            lines.append(f"  • {col} → {type_label}")
        content = "\n".join(lines)

        title = f"💡 변환 가능한 컬럼 ({len(suggestions)}개)"

        return QueryMessage(
            level='expander',
            title=title,
            content=content
        )

    @staticmethod
    def format_batch(messages: list[QueryMessage]) -> list[QueryMessage]:
        """
        Format a batch of messages.

        This is a convenience method for grouping multiple messages.

        Args:
            messages: List of QueryMessage objects

        Returns:
            Same list (for consistency)

        Example:
            >>> messages = [
            ...     QueryMessageFormatter.format_query_info("users", 100),
            ...     QueryMessageFormatter.format_success(100)
            ... ]
            >>> batch = QueryMessageFormatter.format_batch(messages)
            >>> print(len(batch))
            2
        """
        return messages
