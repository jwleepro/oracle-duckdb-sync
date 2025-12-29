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
    render_data_visualization,
    filter_dataframe_by_range
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


class TestFilterDataframeByRange:
    """Tests for data range filtering functionality."""

    def test_filter_single_column_within_range(self):
        """Should keep rows where column value is within min and max."""
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']),
            'value': [0.12, 0.13, 0.125]
        })
        
        filtered = filter_dataframe_by_range(df, 'value', 0.12, 0.13)
        
        assert len(filtered) == 3
        assert filtered['value'].min() >= 0.12
        assert filtered['value'].max() <= 0.13

    def test_filter_excludes_values_below_min(self):
        """Should exclude rows where value is below minimum."""
        df = pd.DataFrame({
            'value': [0.1, 0.12, 0.13, 0.15, 5.0]
        })
        
        filtered = filter_dataframe_by_range(df, 'value', 0.12, 0.13)
        
        assert len(filtered) == 2
        assert all(filtered['value'] >= 0.12)
        assert all(filtered['value'] <= 0.13)

    def test_filter_excludes_values_above_max(self):
        """Should exclude rows where value is above maximum."""
        df = pd.DataFrame({
            'value': [0.12, 0.125, 0.13, 0.15, 5.0]
        })
        
        filtered = filter_dataframe_by_range(df, 'value', 0.12, 0.14)
        
        assert len(filtered) == 3
        assert all(filtered['value'] >= 0.12)
        assert all(filtered['value'] <= 0.14)

    def test_filter_with_outliers(self):
        """Should remove outlier values (e.g., measurement errors)."""
        df = pd.DataFrame({
            'measurement': [0.12, 0.125, 0.13, 0.128, 5.0, 7.0, 0.121]
        })
        
        filtered = filter_dataframe_by_range(df, 'measurement', 0.12, 0.13)
        
        # Should exclude 5.0 and 7.0
        assert len(filtered) == 5
        assert 5.0 not in filtered['measurement'].values
        assert 7.0 not in filtered['measurement'].values

    def test_filter_with_no_exclusions(self):
        """Should return same dataframe if all values are within range."""
        df = pd.DataFrame({
            'value': [0.12, 0.125, 0.13]
        })
        
        filtered = filter_dataframe_by_range(df, 'value', 0.11, 0.14)
        
        assert len(filtered) == len(df)
        assert filtered.equals(df)

    def test_filter_with_all_exclusions(self):
        """Should return empty dataframe if no values are within range."""
        df = pd.DataFrame({
            'value': [5.0, 7.0, 10.0]
        })
        
        filtered = filter_dataframe_by_range(df, 'value', 0.12, 0.13)
        
        assert len(filtered) == 0
        assert isinstance(filtered, pd.DataFrame)

    def test_filter_preserves_other_columns(self):
        """Should preserve all columns when filtering."""
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04']),
            'measurement': [0.12, 0.13, 0.5, 0.125],
            'label': ['a', 'b', 'c', 'd']
        })
        
        filtered = filter_dataframe_by_range(df, 'measurement', 0.12, 0.13)
        
        assert 'timestamp' in filtered.columns
        assert 'label' in filtered.columns
        assert len(filtered) == 3

    def test_filter_with_nan_values(self):
        """Should handle NaN values in data."""
        df = pd.DataFrame({
            'value': [0.12, np.nan, 0.13, 0.5, 0.125]
        })
        
        filtered = filter_dataframe_by_range(df, 'value', 0.12, 0.13)
        
        # NaN should be excluded
        assert len(filtered) == 3
        assert filtered['value'].isna().sum() == 0

    def test_filter_boundary_values_inclusive(self):
        """Should include values equal to min and max."""
        df = pd.DataFrame({
            'value': [0.11, 0.12, 0.125, 0.13, 0.14]
        })
        
        filtered = filter_dataframe_by_range(df, 'value', 0.12, 0.13)
        
        assert 0.12 in filtered['value'].values
        assert 0.13 in filtered['value'].values
        assert 0.11 not in filtered['value'].values
        assert 0.14 not in filtered['value'].values

    def test_filter_preserves_row_index(self):
        """Should preserve original row indices after filtering."""
        df = pd.DataFrame({
            'value': [0.12, 0.5, 0.13, 0.125]
        }, index=['row1', 'row2', 'row3', 'row4'])

        filtered = filter_dataframe_by_range(df, 'value', 0.12, 0.13)

        assert 'row1' in filtered.index
        assert 'row3' in filtered.index
        assert 'row4' in filtered.index
        assert 'row2' not in filtered.index


class TestYAxisRangeAfterFiltering:
    """Tests for Y-axis range calculation after data filtering."""

    def test_y_axis_range_uses_filtered_data(self):
        """Should calculate Y-axis range based on filtered data, not original data."""
        # Create data with outliers: most values are 0.12-0.13, but with outliers 5.0 and 7.0
        y_values_original = np.array([0.12, 0.125, 0.13, 5.0, 7.0, 0.128])

        # Filter to remove outliers
        y_values_filtered = y_values_original[(y_values_original >= 0.12) & (y_values_original <= 0.13)]

        # Calculate Y-axis range for filtered data
        y_min, y_max = calculate_y_axis_range(y_values_filtered, padding_percent=0.05)

        # Expected: min=0.12, max=0.13, range=0.01, padding=0.0005
        # y_min = 0.12 - 0.0005 = 0.1195, y_max = 0.13 + 0.0005 = 0.1305
        expected_min = 0.12 - 0.01 * 0.05
        expected_max = 0.13 + 0.01 * 0.05

        assert y_min == pytest.approx(expected_min, abs=1e-6)
        assert y_max == pytest.approx(expected_max, abs=1e-6)

        # The Y-axis range should NOT include the outliers
        assert y_max < 5.0
        assert y_min < 1.0

    def test_y_axis_range_without_outliers_removed(self):
        """Should show problem when Y-axis range includes outliers."""
        # Same data with outliers
        y_values_with_outliers = np.array([0.12, 0.125, 0.13, 5.0, 7.0, 0.128])

        # Calculate Y-axis range WITHOUT filtering (this is the bug scenario)
        y_min, y_max = calculate_y_axis_range(y_values_with_outliers, padding_percent=0.05)

        # Expected: min=0.12, max=7.0, range=6.88, padding=0.344
        # y_min = 0.12 - 0.344 = -0.224, y_max = 7.0 + 0.344 = 7.344
        expected_range = 7.0 - 0.12
        expected_padding = expected_range * 0.05

        # This shows the problem: Y-axis range is too large
        assert y_max > 7.0
        assert (y_max - y_min) > 6.0  # Range is huge compared to actual data (0.12-0.13)

    def test_y_axis_range_with_multiple_similar_columns_after_filtering(self):
        """Should calculate Y-axis range from all Y columns in filtered dataframe.

        Real scenario from user image:
        - Multiple measurement columns with similar ranges (e.g., 0.1747-0.1748)
        - All columns are selected for Y-axis
        - Filter is applied to one column
        - Y-axis range should include ALL Y columns from the filtered rows
        """
        # Create DataFrame with multiple similar measurement columns
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2020-12-28 09:00', '2020-12-28 10:00', '2020-12-28 11:00', '2020-12-28 12:00']),
            'sensor1': [0.1747, 0.1748, 0.1747, 0.1748],
            'sensor2': [0.1747, 0.1747, 0.1748, 0.1747],
            'sensor3': [0.1748, 0.1747, 0.1747, 0.1748]
        })

        # All values are in range 0.1747-0.1748
        all_y_values = df[['sensor1', 'sensor2', 'sensor3']].values.flatten()
        y_min, y_max = calculate_y_axis_range(all_y_values, padding_percent=0.05)

        # Expected: min=0.1747, max=0.1748, range=0.0001, padding=0.000005
        expected_range = 0.1748 - 0.1747  # 0.0001
        expected_padding = expected_range * 0.05  # 0.000005
        expected_min = 0.1747 - expected_padding
        expected_max = 0.1748 + expected_padding

        assert y_min == pytest.approx(expected_min, abs=1e-7)
        assert y_max == pytest.approx(expected_max, abs=1e-7)

        # The range should be very small
        assert (y_max - y_min) < 0.001
