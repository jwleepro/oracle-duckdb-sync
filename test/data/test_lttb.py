"""
Tests for LTTB (Largest Triangle Three Buckets) downsampling algorithm.
"""

import pytest
import numpy as np
import pandas as pd
from oracle_duckdb_sync.data.lttb import lttb_downsample, lttb_downsample_multi_y, _lttb_core


class TestLTTBCore:
    """Tests for the core LTTB algorithm."""

    def test_no_downsampling_when_below_threshold(self):
        """Should return all indices when data size <= threshold."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([1.0, 2.0, 3.0, 2.0, 1.0])

        indices = _lttb_core(x, y, threshold=10)

        assert len(indices) == 5
        np.testing.assert_array_equal(indices, np.arange(5))

    def test_always_includes_first_and_last_points(self):
        """First and last points should always be included."""
        x = np.arange(100, dtype=np.float64)
        y = np.random.randn(100)

        indices = _lttb_core(x, y, threshold=10)

        assert indices[0] == 0
        assert indices[-1] == 99

    def test_returns_correct_number_of_points(self):
        """Should return exactly threshold number of points."""
        x = np.arange(1000, dtype=np.float64)
        y = np.random.randn(1000)

        indices = _lttb_core(x, y, threshold=50)

        assert len(indices) == 50

    def test_preserves_peak(self):
        """Should preserve obvious peak in the data."""
        # Create data with a clear peak at index 50
        x = np.arange(100, dtype=np.float64)
        y = np.zeros(100)
        y[50] = 100.0  # Clear peak

        indices = _lttb_core(x, y, threshold=10)

        # Peak should be preserved
        assert 50 in indices

    def test_preserves_valley(self):
        """Should preserve obvious valley in the data."""
        # Create data with a clear valley at index 50
        x = np.arange(100, dtype=np.float64)
        y = np.ones(100) * 100
        y[50] = 0.0  # Clear valley

        indices = _lttb_core(x, y, threshold=10)

        # Valley should be preserved
        assert 50 in indices


class TestLTTBDownsample:
    """Tests for the lttb_downsample function."""

    def test_dataframe_input(self):
        """Should work with DataFrame input."""
        df = pd.DataFrame({
            'time': range(1000),
            'value': np.random.randn(1000)
        })

        result = lttb_downsample(df, threshold=100, x_col='time', y_col='value')

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 100
        assert 'time' in result.columns
        assert 'value' in result.columns

    def test_numpy_array_input(self):
        """Should work with numpy array input."""
        data = np.column_stack([
            np.arange(1000, dtype=np.float64),
            np.random.randn(1000)
        ])

        result = lttb_downsample(data, threshold=100)

        assert isinstance(result, np.ndarray)
        assert result.shape == (100, 2)

    def test_datetime_x_column(self):
        """Should handle datetime X column correctly."""
        dates = pd.date_range('2024-01-01', periods=1000, freq='1min')
        df = pd.DataFrame({
            'timestamp': dates,
            'value': np.random.randn(1000)
        })

        result = lttb_downsample(df, threshold=100, x_col='timestamp', y_col='value')

        assert len(result) == 100
        assert result['timestamp'].iloc[0] == dates[0]
        assert result['timestamp'].iloc[-1] == dates[-1]

    def test_raises_error_for_missing_columns(self):
        """Should raise error when x_col or y_col is missing for DataFrame."""
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})

        with pytest.raises(ValueError):
            lttb_downsample(df, threshold=2, x_col='a', y_col=None)

    def test_raises_error_for_invalid_numpy_shape(self):
        """Should raise error for numpy array with wrong shape."""
        data = np.array([1, 2, 3, 4, 5])  # 1D array

        with pytest.raises(ValueError):
            lttb_downsample(data, threshold=3)


class TestLTTBDownsampleMultiY:
    """Tests for multi-column LTTB downsampling."""

    def test_multi_column_downsampling(self):
        """Should downsample all Y columns consistently."""
        df = pd.DataFrame({
            'time': range(1000),
            'sensor1': np.random.randn(1000),
            'sensor2': np.random.randn(1000),
            'sensor3': np.random.randn(1000)
        })

        result = lttb_downsample_multi_y(
            df,
            threshold=100,
            x_col='time',
            y_cols=['sensor1', 'sensor2', 'sensor3']
        )

        assert len(result) == 100
        assert list(result.columns) == ['time', 'sensor1', 'sensor2', 'sensor3']

    def test_no_downsampling_when_below_threshold(self):
        """Should return original DataFrame when size <= threshold."""
        df = pd.DataFrame({
            'time': range(50),
            'value': np.random.randn(50)
        })

        result = lttb_downsample_multi_y(df, threshold=100, x_col='time', y_cols=['value'])

        assert len(result) == 50

    def test_preserves_outliers_in_primary_column(self):
        """Should preserve outliers in the first Y column."""
        # Create data with clear outlier
        values = np.ones(1000) * 10
        values[500] = 1000  # Outlier

        df = pd.DataFrame({
            'time': range(1000),
            'value': values
        })

        result = lttb_downsample_multi_y(df, threshold=50, x_col='time', y_cols=['value'])

        # Outlier should be preserved
        assert result['value'].max() == 1000

    def test_handles_nan_values(self):
        """Should handle NaN values gracefully."""
        values = np.random.randn(1000)
        values[100:110] = np.nan  # Add some NaN values

        df = pd.DataFrame({
            'time': range(1000),
            'value': values
        })

        result = lttb_downsample_multi_y(df, threshold=100, x_col='time', y_cols=['value'])

        assert len(result) == 100

    def test_empty_y_cols_raises_error(self):
        """Should raise error when y_cols is empty."""
        df = pd.DataFrame({'time': [1, 2, 3], 'value': [4, 5, 6]})

        with pytest.raises(ValueError):
            lttb_downsample_multi_y(df, threshold=2, x_col='time', y_cols=[])


class TestLTTBPerformance:
    """Performance-related tests for LTTB."""

    def test_large_dataset_performance(self):
        """Should handle 100k rows efficiently."""
        import time

        df = pd.DataFrame({
            'time': range(100000),
            'value': np.random.randn(100000)
        })

        start = time.time()
        result = lttb_downsample_multi_y(df, threshold=5000, x_col='time', y_cols=['value'])
        elapsed = time.time() - start

        assert len(result) == 5000
        assert elapsed < 1.0, f"LTTB took {elapsed:.2f}s, should be < 1s"

    def test_very_large_dataset(self):
        """Should handle 1M rows."""
        df = pd.DataFrame({
            'time': range(1000000),
            'value': np.random.randn(1000000)
        })

        result = lttb_downsample_multi_y(df, threshold=5000, x_col='time', y_cols=['value'])

        assert len(result) == 5000


class TestLTTBVisualizationIntegration:
    """Tests for LTTB integration with visualization module."""

    def test_trend_preservation(self):
        """Downsampled data should preserve overall trend."""
        # Create clear upward trend
        x = np.arange(10000, dtype=np.float64)
        y = x * 2 + np.random.randn(10000) * 10  # Linear trend with noise

        df = pd.DataFrame({'time': x, 'value': y})
        result = lttb_downsample_multi_y(df, threshold=100, x_col='time', y_cols=['value'])

        # Check trend is preserved (correlation should be high)
        correlation = np.corrcoef(result['time'], result['value'])[0, 1]
        assert correlation > 0.95, f"Trend not preserved, correlation: {correlation}"

    def test_min_max_preservation(self):
        """Should preserve global min and max values."""
        values = np.random.randn(10000)
        original_min = values.min()
        original_max = values.max()

        df = pd.DataFrame({
            'time': range(10000),
            'value': values
        })

        result = lttb_downsample_multi_y(df, threshold=100, x_col='time', y_cols=['value'])

        # Min and max should be close to original (within bucket range)
        assert result['value'].min() <= original_min * 0.9 or result['value'].min() >= original_min
        assert result['value'].max() >= original_max * 0.9 or result['value'].max() <= original_max
