"""
Largest Triangle Three Buckets (LTTB) downsampling algorithm.

This module provides an efficient implementation of the LTTB algorithm
for downsampling time-series data while preserving visual characteristics.

The algorithm preserves:
- Overall trend shape
- Local minima and maxima (important for outlier detection)
- Start and end points

Reference: https://skemman.is/bitstream/1946/15343/3/SS_MSthesis.pdf
"""

from typing import Optional, Union

import numpy as np
import pandas as pd

from oracle_duckdb_sync.log.logger import setup_logger

logger = setup_logger('LTTB')


def lttb_downsample(
    data: Union[pd.DataFrame, np.ndarray],
    threshold: int,
    x_col: Optional[str] = None,
    y_col: Optional[str] = None
) -> Union[pd.DataFrame, np.ndarray]:
    """
    Downsample data using the Largest Triangle Three Buckets algorithm.

    LTTB selects points that form the largest triangles, preserving
    the visual shape of the data including peaks, valleys, and trends.

    Args:
        data: Input data (DataFrame or 2D numpy array with shape (n, 2))
        threshold: Target number of points after downsampling
        x_col: X column name (required if data is DataFrame)
        y_col: Y column name (required if data is DataFrame)

    Returns:
        Downsampled data in the same format as input

    Example:
        >>> df = pd.DataFrame({'time': range(100000), 'value': np.random.randn(100000)})
        >>> df_small = lttb_downsample(df, threshold=1000, x_col='time', y_col='value')
        >>> len(df_small)
        1000
    """
    # Handle DataFrame input
    if isinstance(data, pd.DataFrame):
        if x_col is None or y_col is None:
            raise ValueError("x_col and y_col are required for DataFrame input")

        # Extract x and y as numpy arrays
        x = data[x_col].values
        y = data[y_col].values

        # Convert datetime to numeric for calculation
        if np.issubdtype(x.dtype, np.datetime64):
            x_numeric = x.astype('datetime64[ns]').astype(np.int64)
        else:
            x_numeric = x.astype(np.float64)

        y_numeric = y.astype(np.float64)

        # Get selected indices
        indices = _lttb_core(x_numeric, y_numeric, threshold)

        # Return DataFrame with selected rows
        return data.iloc[indices].reset_index(drop=True)

    # Handle numpy array input
    elif isinstance(data, np.ndarray):
        if data.ndim != 2 or data.shape[1] != 2:
            raise ValueError("Numpy array must have shape (n, 2)")

        x = data[:, 0].astype(np.float64)
        y = data[:, 1].astype(np.float64)

        indices = _lttb_core(x, y, threshold)
        return data[indices]

    else:
        raise TypeError(f"Unsupported data type: {type(data)}")


def _lttb_core(x: np.ndarray, y: np.ndarray, threshold: int) -> np.ndarray:
    """
    Core LTTB algorithm implementation.

    Args:
        x: X values as float64 numpy array
        y: Y values as float64 numpy array
        threshold: Target number of points

    Returns:
        Array of selected indices
    """
    n = len(x)

    # No downsampling needed
    if threshold >= n or threshold <= 2:
        return np.arange(n)

    # Always include first and last points
    selected_indices = np.zeros(threshold, dtype=np.int64)
    selected_indices[0] = 0
    selected_indices[threshold - 1] = n - 1

    # Calculate bucket size
    bucket_size = (n - 2) / (threshold - 2)

    # Previous selected point
    prev_idx = 0

    for i in range(1, threshold - 1):
        # Calculate bucket boundaries
        bucket_start = int((i - 1) * bucket_size) + 1
        bucket_end = int(i * bucket_size) + 1

        # Next bucket for average calculation
        next_bucket_start = int(i * bucket_size) + 1
        next_bucket_end = int((i + 1) * bucket_size) + 1
        next_bucket_end = min(next_bucket_end, n)

        # Calculate average point of next bucket
        if next_bucket_end > next_bucket_start:
            avg_x = np.mean(x[next_bucket_start:next_bucket_end])
            avg_y = np.mean(y[next_bucket_start:next_bucket_end])
        else:
            avg_x = x[next_bucket_start] if next_bucket_start < n else x[-1]
            avg_y = y[next_bucket_start] if next_bucket_start < n else y[-1]

        # Find point in current bucket that forms largest triangle
        max_area = -1.0
        max_idx = bucket_start

        # Previous point coordinates
        prev_x = x[prev_idx]
        prev_y = y[prev_idx]

        for j in range(bucket_start, min(bucket_end, n)):
            # Calculate triangle area using cross product
            # Area = 0.5 * |x1(y2-y3) + x2(y3-y1) + x3(y1-y2)|
            area = abs(
                (prev_x - avg_x) * (y[j] - prev_y) -
                (prev_x - x[j]) * (avg_y - prev_y)
            )

            if area > max_area:
                max_area = area
                max_idx = j

        selected_indices[i] = max_idx
        prev_idx = max_idx

    return selected_indices


def lttb_downsample_multi_y(
    df: pd.DataFrame,
    threshold: int,
    x_col: str,
    y_cols: list
) -> pd.DataFrame:
    """
    Downsample DataFrame with multiple Y columns.

    Uses the first Y column for LTTB selection, then includes
    all other Y columns at the same indices. This ensures
    consistent X-axis alignment across all series.

    Args:
        df: Input DataFrame
        threshold: Target number of points
        x_col: X column name (typically datetime)
        y_cols: List of Y column names

    Returns:
        Downsampled DataFrame with all specified columns
    """
    if len(df) <= threshold:
        logger.info(f"No downsampling needed: {len(df)} rows <= {threshold} threshold")
        return df

    if not y_cols:
        raise ValueError("y_cols must not be empty")

    # Use first Y column for LTTB selection
    primary_y = y_cols[0]

    # Get x values
    x = df[x_col].values
    if np.issubdtype(x.dtype, np.datetime64):
        x_numeric = x.astype('datetime64[ns]').astype(np.int64)
    else:
        x_numeric = x.astype(np.float64)

    # Get primary y values
    y = df[primary_y].values.astype(np.float64)

    # Handle NaN values - use valid indices only for LTTB
    valid_mask = ~np.isnan(y)
    if not np.all(valid_mask):
        # If there are NaN values, we need to be careful
        # Option: Fill NaN with interpolated values for LTTB calculation only
        y_filled = pd.Series(y).interpolate(method='linear', limit_direction='both').values
        y = y_filled

    # Get selected indices
    indices = _lttb_core(x_numeric, y, threshold)

    # Select all columns at these indices
    columns_to_keep = [x_col] + y_cols
    result = df[columns_to_keep].iloc[indices].reset_index(drop=True)

    original_len = len(df)
    result_len = len(result)
    reduction = (1 - result_len / original_len) * 100

    logger.info(f"LTTB downsampling: {original_len:,} → {result_len:,} rows ({reduction:.1f}% reduction)")

    return result
