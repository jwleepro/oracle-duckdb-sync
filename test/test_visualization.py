"""
Tests for visualization module.

This test module covers the data visualization functionality including
chart rendering and data processing for visual display.
"""

import pytest
import pandas as pd
import numpy as np
from oracle_duckdb_sync.visualization import (
    calculate_y_axis_range,
    render_data_visualization
)


class TestCalculateYAxisRange:
    """Tests for Y-axis range calculation."""

    def test_calculate_range_with_varied_values(self):
        """Should calculate range with 5% padding for varied values."""
        y_values = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        y_min, y_max = calculate_y_axis_range(y_values, padding_percent=0.05)

        # Expected: min=10, max=50, range=40, padding=2
        # y_min = 10 - 2 = 8, y_max = 50 + 2 = 52
        assert y_min == pytest.approx(8.0)
        assert y_max == pytest.approx(52.0)

    def test_calculate_range_with_identical_values(self):
        """Should handle identical values with small range."""
        y_values = np.array([100.0, 100.0, 100.0])
        y_min, y_max = calculate_y_axis_range(y_values)

        # Expected: small range around 100
        # y_min = 100 - 1 = 99, y_max = 100 + 1 = 101
        assert y_min == pytest.approx(99.0)
        assert y_max == pytest.approx(101.0)

    def test_calculate_range_with_nan_values(self):
        """Should ignore NaN values in calculation."""
        y_values = np.array([10.0, np.nan, 30.0, np.nan, 50.0])
        y_min, y_max = calculate_y_axis_range(y_values, padding_percent=0.05)

        # Should only use 10, 30, 50
        # range = 40, padding = 2
        assert y_min == pytest.approx(8.0)
        assert y_max == pytest.approx(52.0)

    def test_calculate_range_with_all_nan_values(self):
        """Should return None for all NaN values."""
        y_values = np.array([np.nan, np.nan, np.nan])
        y_min, y_max = calculate_y_axis_range(y_values)

        assert y_min is None
        assert y_max is None

    def test_calculate_range_with_empty_array(self):
        """Should return None for empty array."""
        y_values = np.array([])
        y_min, y_max = calculate_y_axis_range(y_values)

        assert y_min is None
        assert y_max is None

    def test_calculate_range_with_zero_values(self):
        """Should handle zero values correctly."""
        y_values = np.array([0.0, 0.0, 0.0])
        y_min, y_max = calculate_y_axis_range(y_values)

        # When all values are 0, should create small range
        assert y_min == pytest.approx(-0.01)
        assert y_max == pytest.approx(0.01)

    def test_calculate_range_with_custom_padding(self):
        """Should apply custom padding percentage."""
        y_values = np.array([0.0, 100.0])
        y_min, y_max = calculate_y_axis_range(y_values, padding_percent=0.10)

        # range = 100, padding = 10
        assert y_min == pytest.approx(-10.0)
        assert y_max == pytest.approx(110.0)

    def test_calculate_range_with_small_variations(self):
        """Should handle small variations in values (e.g., 0.1746 vs 0.1747)."""
        y_values = np.array([0.1746, 0.1747, 0.1746, 0.1747])
        y_min, y_max = calculate_y_axis_range(y_values, padding_percent=0.05)

        # range = 0.0001, padding = 0.000005
        expected_min = 0.1746 - 0.000005
        expected_max = 0.1747 + 0.000005
        assert y_min == pytest.approx(expected_min, abs=1e-7)
        assert y_max == pytest.approx(expected_max, abs=1e-7)


class TestRenderDataVisualization:
    """Tests for render_data_visualization function."""

    def test_empty_dataframe(self):
        """Should handle empty DataFrame gracefully."""
        df = pd.DataFrame()
        # Should not raise exception
        render_data_visualization(df, "test_table")

    def test_dataframe_without_numeric_or_datetime_columns(self):
        """Should handle DataFrame with no visualizable columns."""
        df = pd.DataFrame({
            'text_col': ['a', 'b', 'c'],
            'category': ['x', 'y', 'z']
        })
        # Should not raise exception
        render_data_visualization(df, "test_table")

    def test_dataframe_with_numeric_columns(self):
        """Should detect numeric columns correctly."""
        df = pd.DataFrame({
            'value1': [1.0, 2.0, 3.0],
            'value2': [10.0, 20.0, 30.0],
            'text': ['a', 'b', 'c']
        })
        # Should not raise exception when numeric columns exist
        render_data_visualization(df, "test_table")

    def test_dataframe_with_datetime_columns(self):
        """Should detect datetime columns correctly."""
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']),
            'value': [1.0, 2.0, 3.0]
        })
        # Should not raise exception when datetime columns exist
        render_data_visualization(df, "test_table")

    def test_dataframe_with_mixed_types(self):
        """Should handle DataFrame with mixed column types."""
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']),
            'value': [1.0, 2.0, 3.0],
            'text': ['a', 'b', 'c'],
            'integer': [10, 20, 30]
        })
        # Should not raise exception
        render_data_visualization(df, "test_table")
