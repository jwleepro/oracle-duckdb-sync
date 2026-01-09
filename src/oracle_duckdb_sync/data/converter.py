"""
Data type converter for automatic detection and conversion of string columns.

This module provides utilities to detect and convert string columns that contain
numeric or datetime data into appropriate pandas data types for visualization.
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd

from oracle_duckdb_sync.log.logger import setup_logger

logger = setup_logger('DataConverter')


def is_numeric_string(series: pd.Series, threshold: float = 0.9, sample_size: int = 1000) -> bool:
    """
    Check if a string series contains numeric values (optimized with sampling).

    Args:
        series: Pandas series to check
        threshold: Minimum proportion of values that must be numeric (default: 0.9)
        sample_size: Number of rows to sample for detection (default: 1000)

    Returns:
        True if the series appears to contain numeric strings
    """
    if series.dtype != 'object':
        return False

    # Remove null values
    non_null = series.dropna()
    if len(non_null) == 0:
        return False

    # Use sampling for large datasets
    if len(non_null) > sample_size:
        sample = non_null.sample(n=sample_size, random_state=42)
    else:
        sample = non_null

    # Vectorized approach: try to convert and count successes
    converted = pd.to_numeric(sample, errors='coerce')
    numeric_count = converted.notna().sum()

    proportion = numeric_count / len(sample)
    return bool(proportion >= threshold)


def is_datetime_string(series: pd.Series, threshold: float = 0.9, sample_size: int = 1000) -> bool:
    """
    Check if a string series contains datetime values (optimized with sampling).

    Args:
        series: Pandas series to check
        threshold: Minimum proportion of values that must be datetime (default: 0.9)
        sample_size: Number of rows to sample for detection (default: 1000)

    Returns:
        True if the series appears to contain datetime strings
    """
    if series.dtype != 'object':
        return False

    # Remove null values
    non_null = series.dropna()
    if len(non_null) == 0:
        return False

    # Use sampling for large datasets
    if len(non_null) > sample_size:
        sample = non_null.sample(n=sample_size, random_state=42)
    else:
        sample = non_null

    # Quick check: look at first value to determine likely format
    first_value = str(sample.iloc[0]).strip()

    # Compile regex patterns once for efficiency
    patterns = {
        'yyyymmddhhmmss': re.compile(r'^\d{14}$'),
        'yyyymmdd': re.compile(r'^\d{8}$'),
        'iso_date': re.compile(r'^\d{4}-\d{2}-\d{2}'),
        'slash_date': re.compile(r'^\d{4}/\d{2}/\d{2}'),
    }

    # Determine most likely format from first value
    matched_format = None
    for _format_name, pattern in patterns.items():
        if pattern.match(first_value):
            matched_format = pattern
            break

    if matched_format:
        # Use vectorized string matching for the detected format
        datetime_mask = sample.astype(str).str.match(matched_format)
        proportion = datetime_mask.sum() / len(sample)
    else:
        # Fall back to pandas datetime parsing (vectorized)
        # Note: Format inference is now enabled by default in pandas 2.0+
        try:
            converted = pd.to_datetime(sample, errors='coerce', format='mixed')
            proportion = converted.notna().sum() / len(sample)
        except Exception:
            # If inference fails, return False
            return False

    return bool(proportion >= threshold)


def convert_to_datetime(series: pd.Series) -> Optional[pd.Series]:
    """
    Convert a string series to datetime (optimized).

    Supports multiple formats:
    - YYYYMMDDHHMMSS (14 digits): "20231219153045"
    - YYYYMMDD (8 digits): "20231219"
    - ISO 8601: "2023-12-19T15:30:45"
    - Common formats: "2023-12-19 15:30:45", "2023/12/19", etc.

    Args:
        series: Pandas series to convert

    Returns:
        Converted datetime series, or None if conversion fails
    """
    try:
        # First, check if it's already datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            return series

        # Get first non-null value for format detection
        non_null = series.dropna()
        if len(non_null) == 0:
            return None

        sample_value = str(non_null.iloc[0]).strip()

        # Pre-compiled regex patterns for better performance
        pattern_14_digits = re.compile(r'^\d{14}$')
        pattern_8_digits = re.compile(r'^\d{8}$')

        # Detect format and convert (vectorized operation)
        if pattern_14_digits.match(sample_value):
            # YYYYMMDDHHMMSS format (14 digits) - use format parameter for speed
            logger.info(f"Detected YYYYMMDDHHMMSS format in column '{series.name}'")
            return pd.to_datetime(series, format='%Y%m%d%H%M%S', errors='coerce')

        elif pattern_8_digits.match(sample_value):
            # YYYYMMDD format (8 digits) - use format parameter for speed
            logger.info(f"Detected YYYYMMDD format in column '{series.name}'")
            return pd.to_datetime(series, format='%Y%m%d', errors='coerce')

        else:
            # Try pandas automatic inference (slower but handles various formats)
            logger.info(f"Attempting automatic datetime parsing for column '{series.name}'")
            # Note: Format inference is now enabled by default in pandas 2.0+
            return pd.to_datetime(series, errors='coerce', format='mixed')

    except Exception as e:
        logger.warning(f"Failed to convert column '{series.name}' to datetime: {e}")
        return None


def convert_to_numeric(series: pd.Series) -> Optional[pd.Series]:
    """
    Convert a string series to numeric (optimized).

    Args:
        series: Pandas series to convert

    Returns:
        Converted numeric series, or None if conversion fails
    """
    try:
        # Vectorized conversion - pandas handles this efficiently
        converted = pd.to_numeric(series, errors='coerce')

        # Quick validation: check if at least 90% of non-null values converted successfully
        non_null_count = series.notna().sum()
        if non_null_count == 0:
            return None

        converted_count = converted.notna().sum()
        success_rate = converted_count / non_null_count

        if success_rate >= 0.9:
            logger.info(f"Successfully converted column '{series.name}' to numeric ({success_rate:.1%} success rate)")
            return converted
        else:
            logger.debug(f"Low success rate ({success_rate:.1%}) for numeric conversion of column '{series.name}'")
            return None

    except Exception as e:
        logger.warning(f"Failed to convert column '{series.name}' to numeric: {e}")
        return None


def detect_column_type(column: pd.Series, threshold: float = 0.9, sample_size: int = 1000) -> str:
    """
    Detect the expected type of a column (optimized with sampling).

    Args:
        column: Pandas series to analyze
        threshold: Minimum proportion of values that must match the type (default: 0.9)
        sample_size: Number of rows to sample for detection (default: 1000)

    Returns:
        Detected type: 'numeric', 'datetime', or 'string'
    """
    # Skip if already numeric or datetime
    if pd.api.types.is_numeric_dtype(column) or pd.api.types.is_datetime64_any_dtype(column):
        return 'numeric' if pd.api.types.is_numeric_dtype(column) else 'datetime'

    # Only process object (string) columns
    if column.dtype != 'object':
        return 'string'

    # Try datetime first (more specific)
    if is_datetime_string(column, threshold, sample_size):
        return 'datetime'

    # Try numeric
    if is_numeric_string(column, threshold, sample_size):
        return 'numeric'

    return 'string'


def convert_column_to_type(column: pd.Series, target_type: str) -> pd.Series:
    """
    Convert a column to the specified target type.

    Args:
        column: Pandas series to convert
        target_type: Target type ('numeric', 'datetime', or 'string')

    Returns:
        Converted series
    """
    if target_type == 'numeric':
        converted = convert_to_numeric(column)
        return converted if converted is not None else column
    elif target_type == 'datetime':
        converted = convert_to_datetime(column)
        return converted if converted is not None else column
    else:  # 'string'
        return column


def detect_and_convert_types(df: pd.DataFrame, use_parallel: bool = True, max_workers: int = 4) -> tuple[pd.DataFrame, dict]:
    """
    Automatically detect and convert string columns to appropriate types (optimized).

    This function analyzes each string column in the dataframe and attempts to
    convert it to numeric or datetime types if the content matches those patterns.

    Optimizations:
    - Sampling for type detection on large datasets
    - Vectorized operations instead of loops
    - Optional parallel processing for multiple columns
    - Early exit for non-convertible types

    Args:
        df: Input dataframe
        use_parallel: Enable parallel processing for multiple columns (default: True)
        max_workers: Maximum number of parallel workers (default: 4)

    Returns:
        Dataframe with converted types
    """
    if df.empty:
        return df, {}

    df_converted = df.copy()
    conversion_summary = {
        'numeric': [],
        'datetime': [],
        'unchanged': []
    }

    # Filter columns that need conversion (only object type)
    columns_to_process = [
        col for col in df_converted.columns
        if df_converted[col].dtype == 'object'
        and not (pd.api.types.is_numeric_dtype(df_converted[col]) or
                pd.api.types.is_datetime64_any_dtype(df_converted[col]))
    ]

    if not columns_to_process:
        logger.info("No columns to convert")
        return df_converted, conversion_summary

    def process_column(col):
        """Process a single column for type conversion."""
        series = df_converted[col]

        # Detect column type with sampling
        detected_type = detect_column_type(series)

        # Convert to detected type
        if detected_type != 'string':
            converted = convert_column_to_type(series, detected_type)
            if not converted.isna().all():
                return (col, converted, detected_type)

        return (col, None, 'unchanged')

    # Process columns in parallel or sequentially
    if use_parallel and len(columns_to_process) > 1:
        logger.info(f"Processing {len(columns_to_process)} columns in parallel with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_column, col): col for col in columns_to_process}

            processed_count = 0
            total_count = len(columns_to_process)

            for future in as_completed(futures):
                col, converted, detected_type = future.result()
                processed_count += 1

                if converted is not None:
                    df_converted[col] = converted
                    conversion_summary[detected_type].append(col)
                    logger.info(f"[{processed_count}/{total_count}] Converted column '{col}' to {detected_type}")
                else:
                    conversion_summary['unchanged'].append(col)
                    logger.info(f"[{processed_count}/{total_count}] Column '{col}' unchanged")
    else:
        # Sequential processing
        logger.info(f"Processing {len(columns_to_process)} columns sequentially")

        for idx, col in enumerate(columns_to_process, 1):
            col_name, converted, detected_type = process_column(col)

            if converted is not None:
                df_converted[col_name] = converted
                conversion_summary[detected_type].append(col_name)
                logger.info(f"[{idx}/{len(columns_to_process)}] Converted column '{col_name}' to {detected_type}")
            else:
                conversion_summary['unchanged'].append(col_name)
                logger.info(f"[{idx}/{len(columns_to_process)}] Column '{col_name}' unchanged")

    # Log summary
    if conversion_summary['numeric'] or conversion_summary['datetime']:
        logger.info(f"Type conversion summary: "
                   f"{len(conversion_summary['numeric'])} numeric, "
                   f"{len(conversion_summary['datetime'])} datetime, "
                   f"{len(conversion_summary['unchanged'])} unchanged")

    return df_converted, conversion_summary



def detect_convertible_columns(df: pd.DataFrame) -> dict:
    """
    Detect which columns can be converted to numeric or datetime types.

    This function analyzes each string column and returns suggestions
    for type conversions without actually converting them.

    Args:
        df: Input dataframe

    Returns:
        Dictionary with column names as keys and detected types as values.
        Format: {'column_name': 'numeric'|'datetime'|'string'}
    """
    if df.empty:
        return {}

    suggestions = {}

    for col in df.columns:
        series = df[col]

        # Skip if already numeric or datetime
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            continue

        # Only process object (string) columns
        if series.dtype != 'object':
            continue

        # Detect column type
        detected_type = detect_column_type(series)
        if detected_type != 'string':
            suggestions[col] = detected_type

    return suggestions


def convert_selected_columns(df: pd.DataFrame, selected_conversions: dict) -> pd.DataFrame:
    """
    Convert only the selected columns to their specified types.

    Args:
        df: Input dataframe
        selected_conversions: Dictionary mapping column names to target types
                            Format: {'column_name': 'numeric'|'datetime'}

    Returns:
        DataFrame with only selected columns converted
    """
    if df.empty or not selected_conversions:
        return df

    df_converted = df.copy()

    for col, target_type in selected_conversions.items():
        if col not in df_converted.columns:
            logger.warning(f"Column '{col}' not found in dataframe, skipping")
            continue

        series = df_converted[col]

        # Convert to target type
        converted = convert_column_to_type(series, target_type)
        if not converted.isna().all():
            df_converted[col] = converted
            logger.info(f"Converted column '{col}' to {target_type}")
        else:
            logger.warning(f"Failed to convert column '{col}' to {target_type}")

    return df_converted
