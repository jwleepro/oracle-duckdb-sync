"""
Type conversion service for DataFrames.

This module provides a clean interface for automatic and selective
type conversion of DataFrame columns, including numeric and datetime conversions.
"""

import pandas as pd
from dataclasses import dataclass
from typing import Optional

from oracle_duckdb_sync.data.converter import (
    convert_selected_columns,
    detect_and_convert_types,
    detect_convertible_columns,
)
from oracle_duckdb_sync.log.logger import setup_logger


# Set up logger
converter_logger = setup_logger('TypeConverterService')


@dataclass
class TypeConversionResult:
    """
    Result of a type conversion operation.

    Attributes:
        df_converted: DataFrame with converted types
        df_original: Original DataFrame before conversion
        conversions: Dictionary mapping column names to (old_type, new_type) tuples
        suggestions: Dictionary of columns that can be converted {'col': 'numeric'/'datetime'}
    """
    df_converted: pd.DataFrame
    df_original: pd.DataFrame
    conversions: dict[str, tuple[str, str]]
    suggestions: dict[str, str]


class TypeConverterService:
    """
    Handles automatic and selective type conversion for DataFrames.

    This service:
    - Detects columns that can be converted to numeric or datetime types
    - Applies automatic conversion to all convertible columns
    - Allows selective conversion of specific columns
    - Tracks type changes for auditing and display
    """

    def __init__(self):
        """Initialize TypeConverterService."""
        self.logger = converter_logger

    def convert_automatic(
        self,
        df: pd.DataFrame,
        preserve_original: bool = True
    ) -> TypeConversionResult:
        """
        Automatically convert all convertible columns.

        This method detects and converts:
        - String columns that contain only numbers → numeric
        - String columns that contain dates → datetime

        Args:
            df: Input DataFrame to convert
            preserve_original: If True, keeps a copy of the original DataFrame

        Returns:
            TypeConversionResult with converted DataFrame and metadata

        Example:
            >>> service = TypeConverterService()
            >>> df = pd.DataFrame({
            ...     'num_str': ['1', '2', '3'],
            ...     'date_str': ['2024-01-01', '2024-01-02', '2024-01-03'],
            ...     'text': ['abc', 'def', 'ghi']
            ... })
            >>> result = service.convert_automatic(df)
            >>> print(result.conversions)
            {'num_str': ('object', 'float64'), 'date_str': ('object', 'datetime64[ns]')}
        """
        self.logger.info(f"Starting automatic type conversion: {len(df)} rows, {len(df.columns)} columns")

        # Keep original if requested
        df_original = df.copy() if preserve_original else df

        # Detect conversion suggestions
        suggestions = detect_convertible_columns(df)
        self.logger.info(f"Detected {len(suggestions)} convertible columns: {list(suggestions.keys())}")

        # Apply automatic conversion
        df_converted, _ = detect_and_convert_types(df)

        # Calculate type changes
        conversions = self._calculate_type_changes(df_original, df_converted)

        self.logger.info(f"Automatic conversion complete: {len(conversions)} columns converted")

        return TypeConversionResult(
            df_converted=df_converted,
            df_original=df_original,
            conversions=conversions,
            suggestions=suggestions
        )

    def convert_selected(
        self,
        df: pd.DataFrame,
        selected_conversions: dict[str, str],
        preserve_original: bool = True
    ) -> TypeConversionResult:
        """
        Convert only selected columns based on user choice.

        Args:
            df: Input DataFrame to convert
            selected_conversions: Dictionary mapping column names to target types
                                 Format: {'column_name': 'numeric' | 'datetime'}
            preserve_original: If True, keeps a copy of the original DataFrame

        Returns:
            TypeConversionResult with converted DataFrame and metadata

        Example:
            >>> service = TypeConverterService()
            >>> df = pd.DataFrame({
            ...     'num_str': ['1', '2', '3'],
            ...     'date_str': ['2024-01-01', '2024-01-02', '2024-01-03'],
            ...     'text': ['abc', 'def', 'ghi']
            ... })
            >>> result = service.convert_selected(df, {'num_str': 'numeric'})
            >>> print(result.conversions)
            {'num_str': ('object', 'float64')}
        """
        self.logger.info(
            f"Starting selective type conversion: "
            f"{len(selected_conversions)} columns selected"
        )

        # Keep original if requested
        df_original = df.copy() if preserve_original else df

        # Apply selective conversion
        df_converted = convert_selected_columns(df, selected_conversions)

        # Calculate type changes
        conversions = self._calculate_type_changes(df_original, df_converted)

        # Detect all possible conversions (for reference)
        suggestions = detect_convertible_columns(df_original)

        self.logger.info(f"Selective conversion complete: {len(conversions)} columns converted")

        return TypeConversionResult(
            df_converted=df_converted,
            df_original=df_original,
            conversions=conversions,
            suggestions=suggestions
        )

    def detect_convertible_columns(self, df: pd.DataFrame) -> dict[str, str]:
        """
        Detect which columns can be converted to numeric or datetime types.

        Args:
            df: Input DataFrame to analyze

        Returns:
            Dictionary mapping column names to suggested conversion types
            Format: {'column_name': 'numeric' | 'datetime'}

        Example:
            >>> service = TypeConverterService()
            >>> df = pd.DataFrame({
            ...     'num_str': ['1', '2', '3'],
            ...     'date_str': ['2024-01-01', '2024-01-02', '2024-01-03'],
            ...     'text': ['abc', 'def', 'ghi']
            ... })
            >>> suggestions = service.detect_convertible_columns(df)
            >>> print(suggestions)
            {'num_str': 'numeric', 'date_str': 'datetime'}
        """
        suggestions = detect_convertible_columns(df)
        self.logger.info(f"Detected {len(suggestions)} convertible columns")

        return suggestions

    def _calculate_type_changes(
        self,
        df_original: pd.DataFrame,
        df_converted: pd.DataFrame
    ) -> dict[str, tuple[str, str]]:
        """
        Calculate which columns had their types changed.

        Args:
            df_original: Original DataFrame before conversion
            df_converted: DataFrame after type conversion

        Returns:
            Dictionary mapping column names to (old_type, new_type) tuples
            Only includes columns where types actually changed

        Example:
            >>> service = TypeConverterService()
            >>> df_orig = pd.DataFrame({'col1': ['1', '2'], 'col2': ['a', 'b']})
            >>> df_conv = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
            >>> changes = service._calculate_type_changes(df_orig, df_conv)
            >>> print(changes)
            {'col1': ('object', 'int64')}
        """
        original_types = df_original.dtypes.to_dict()
        converted_types = df_converted.dtypes.to_dict()

        # Find columns where types changed
        type_changes = {
            col: (str(original_types[col]), str(converted_types[col]))
            for col in df_original.columns
            if str(original_types[col]) != str(converted_types[col])
        }

        return type_changes

    def format_conversion_summary(
        self,
        conversions: dict[str, tuple[str, str]]
    ) -> str:
        """
        Format type conversions as a human-readable summary.

        Args:
            conversions: Dictionary of type changes

        Returns:
            Formatted string describing the conversions

        Example:
            >>> service = TypeConverterService()
            >>> conversions = {
            ...     'price': ('object', 'float64'),
            ...     'created_at': ('object', 'datetime64[ns]')
            ... }
            >>> print(service.format_conversion_summary(conversions))
            Type conversions applied:
            • price: object → float64
            • created_at: object → datetime64[ns]
        """
        if not conversions:
            return "No type conversions applied"

        lines = ["Type conversions applied:"]
        for col, (old_type, new_type) in conversions.items():
            lines.append(f"• {col}: {old_type} → {new_type}")

        return "\n".join(lines)

    def apply_conversions_to_raw_data(
        self,
        data: list[tuple],
        columns: list[str],
        selected_conversions: Optional[dict[str, str]] = None
    ) -> TypeConversionResult:
        """
        Convert raw data (list of tuples) to a typed DataFrame.

        This is useful when working with query results that haven't been
        converted to DataFrames yet.

        Args:
            data: Raw data rows (list of tuples/lists)
            columns: Column names
            selected_conversions: Optional dict of columns to convert
                                 If None, converts all detectable columns automatically

        Returns:
            TypeConversionResult with converted DataFrame

        Example:
            >>> service = TypeConverterService()
            >>> data = [('1', '2024-01-01'), ('2', '2024-01-02')]
            >>> columns = ['id', 'date']
            >>> result = service.apply_conversions_to_raw_data(data, columns)
            >>> print(result.df_converted.dtypes)
            id      float64
            date    datetime64[ns]
        """
        # Create DataFrame from raw data
        df = pd.DataFrame(data, columns=columns)

        # Apply conversion
        if selected_conversions is None:
            result = self.convert_automatic(df)
        else:
            result = self.convert_selected(df, selected_conversions)

        self.logger.info(f"Converted raw data: {len(data)} rows, {len(result.conversions)} conversions")

        return result
