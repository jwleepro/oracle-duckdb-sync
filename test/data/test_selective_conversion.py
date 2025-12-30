"""
Tests for selective type conversion functionality.

This test module covers the selective column type conversion features.
"""

import pytest
import pandas as pd
from oracle_duckdb_sync.data_converter import (
    detect_convertible_columns,
    convert_selected_columns
)


class TestDetectConvertibleColumns:
    """Tests for detect_convertible_columns function."""

    def test_detect_numeric_column(self):
        """Should detect numeric string column."""
        df = pd.DataFrame({
            'number_str': ['1', '2', '3'],
            'text': ['a', 'b', 'c']
        })

        suggestions = detect_convertible_columns(df)

        assert 'number_str' in suggestions
        assert suggestions['number_str'] == 'numeric'
        assert 'text' not in suggestions

    def test_detect_datetime_column(self):
        """Should detect datetime string column."""
        df = pd.DataFrame({
            'date_str': ['20250101', '20250102', '20250103'],
            'text': ['a', 'b', 'c']
        })

        suggestions = detect_convertible_columns(df)

        assert 'date_str' in suggestions
        assert suggestions['date_str'] == 'datetime'

    def test_no_convertible_columns(self):
        """Should return empty dict when no columns are convertible."""
        df = pd.DataFrame({
            'text1': ['a', 'b', 'c'],
            'text2': ['x', 'y', 'z']
        })

        suggestions = detect_convertible_columns(df)

        assert suggestions == {}

    def test_skip_already_converted_columns(self):
        """Should skip columns that are already numeric or datetime."""
        df = pd.DataFrame({
            'already_numeric': [1, 2, 3],
            'already_datetime': pd.to_datetime(['2025-01-01', '2025-01-02', '2025-01-03']),
            'convertible': ['4', '5', '6']
        })

        suggestions = detect_convertible_columns(df)

        assert 'already_numeric' not in suggestions
        assert 'already_datetime' not in suggestions
        assert 'convertible' in suggestions

    def test_empty_dataframe(self):
        """Should handle empty DataFrame."""
        df = pd.DataFrame()

        suggestions = detect_convertible_columns(df)

        assert suggestions == {}


class TestConvertSelectedColumns:
    """Tests for convert_selected_columns function."""

    def test_convert_single_numeric_column(self):
        """Should convert only selected numeric column."""
        df = pd.DataFrame({
            'col1': ['1', '2', '3'],
            'col2': ['4', '5', '6'],
            'col3': ['a', 'b', 'c']
        })

        selected = {'col1': 'numeric'}
        result = convert_selected_columns(df, selected)

        # col1 should be converted
        assert pd.api.types.is_numeric_dtype(result['col1'])
        # col2 should remain string
        assert result['col2'].dtype == 'object'
        # col3 should remain string
        assert result['col3'].dtype == 'object'

    def test_convert_multiple_columns(self):
        """Should convert multiple selected columns."""
        df = pd.DataFrame({
            'num1': ['1', '2', '3'],
            'num2': ['4', '5', '6'],
            'date1': ['20250101', '20250102', '20250103'],
            'text': ['a', 'b', 'c']
        })

        selected = {
            'num1': 'numeric',
            'num2': 'numeric',
            'date1': 'datetime'
        }
        result = convert_selected_columns(df, selected)

        assert pd.api.types.is_numeric_dtype(result['num1'])
        assert pd.api.types.is_numeric_dtype(result['num2'])
        assert pd.api.types.is_datetime64_any_dtype(result['date1'])
        assert result['text'].dtype == 'object'

    def test_convert_no_columns(self):
        """Should return unchanged DataFrame when no columns selected."""
        df = pd.DataFrame({
            'col1': ['1', '2', '3'],
            'col2': ['a', 'b', 'c']
        })

        selected = {}
        result = convert_selected_columns(df, selected)

        # Should be unchanged
        assert result['col1'].dtype == 'object'
        assert result['col2'].dtype == 'object'

    def test_skip_nonexistent_column(self):
        """Should skip columns that don't exist in DataFrame."""
        df = pd.DataFrame({
            'col1': ['1', '2', '3']
        })

        selected = {
            'col1': 'numeric',
            'nonexistent': 'numeric'
        }
        result = convert_selected_columns(df, selected)

        # Should convert col1 without error
        assert pd.api.types.is_numeric_dtype(result['col1'])

    def test_empty_dataframe(self):
        """Should handle empty DataFrame."""
        df = pd.DataFrame()
        selected = {'col1': 'numeric'}

        result = convert_selected_columns(df, selected)

        assert result.empty


class TestSelectiveConversionIntegration:
    """Integration tests for selective conversion workflow."""

    def test_detect_then_convert_workflow(self):
        """Should detect convertible columns then convert only selected ones."""
        df = pd.DataFrame({
            'number_col': ['1', '2', '3'],
            'date_col': ['20250101', '20250102', '20250103'],
            'text_col': ['a', 'b', 'c']
        })

        # Step 1: Detect suggestions
        suggestions = detect_convertible_columns(df)

        assert 'number_col' in suggestions
        assert 'date_col' in suggestions
        assert 'text_col' not in suggestions

        # Step 2: User selects only number_col
        selected = {'number_col': suggestions['number_col']}

        # Step 3: Convert
        result = convert_selected_columns(df, selected)

        # Only number_col should be converted
        assert pd.api.types.is_numeric_dtype(result['number_col'])
        assert result['date_col'].dtype == 'object'  # Not converted
        assert result['text_col'].dtype == 'object'

    def test_user_overrides_suggestion(self):
        """User can choose not to convert suggested columns."""
        df = pd.DataFrame({
            'number_col': ['1', '2', '3'],
            'date_col': ['20250101', '20250102', '20250103']
        })

        # Detect suggestions
        suggestions = detect_convertible_columns(df)
        assert len(suggestions) == 2

        # User selects none
        selected = {}

        # Convert
        result = convert_selected_columns(df, selected)

        # Nothing should be converted
        assert result['number_col'].dtype == 'object'
        assert result['date_col'].dtype == 'object'
