"""
Data type converter for automatic detection and conversion of string columns.

This module provides utilities to detect and convert string columns that contain
numeric or datetime data into appropriate pandas data types for visualization.
"""

import pandas as pd
import numpy as np
from typing import Optional
import re
from oracle_duckdb_sync.logger import setup_logger

logger = setup_logger('DataConverter')


def is_numeric_string(series: pd.Series, threshold: float = 0.9) -> bool:
    """
    Check if a string series contains numeric values.
    
    Args:
        series: Pandas series to check
        threshold: Minimum proportion of values that must be numeric (default: 0.9)
    
    Returns:
        True if the series appears to contain numeric strings
    """
    if series.dtype != 'object':
        return False
    
    # Remove null values
    non_null = series.dropna()
    if len(non_null) == 0:
        return False
    
    # Try to convert to numeric
    numeric_count = 0
    for value in non_null:
        try:
            float(str(value).strip())
            numeric_count += 1
        except (ValueError, TypeError):
            pass
    
    proportion = numeric_count / len(non_null)
    return proportion >= threshold


def is_datetime_string(series: pd.Series, threshold: float = 0.9) -> bool:
    """
    Check if a string series contains datetime values.
    
    Args:
        series: Pandas series to check
        threshold: Minimum proportion of values that must be datetime (default: 0.9)
    
    Returns:
        True if the series appears to contain datetime strings
    """
    if series.dtype != 'object':
        return False
    
    # Remove null values
    non_null = series.dropna()
    if len(non_null) == 0:
        return False
    
    # Check for common datetime patterns
    datetime_patterns = [
        r'^\d{14}$',  # YYYYMMDDHHMMSS (14 digits)
        r'^\d{8}$',   # YYYYMMDD (8 digits)
        r'^\d{4}-\d{2}-\d{2}',  # ISO date format
        r'^\d{4}/\d{2}/\d{2}',  # Slash date format
    ]
    
    datetime_count = 0
    for value in non_null:
        str_value = str(value).strip()
        for pattern in datetime_patterns:
            if re.match(pattern, str_value):
                datetime_count += 1
                break
    
    proportion = datetime_count / len(non_null)
    return proportion >= threshold


def convert_to_datetime(series: pd.Series) -> Optional[pd.Series]:
    """
    Convert a string series to datetime.
    
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
        
        # Try to detect the format from the first non-null value
        non_null = series.dropna()
        if len(non_null) == 0:
            return None
        
        sample_value = str(non_null.iloc[0]).strip()
        
        # YYYYMMDDHHMMSS format (14 digits)
        if re.match(r'^\d{14}$', sample_value):
            logger.info(f"Detected YYYYMMDDHHMMSS format in column '{series.name}'")
            return pd.to_datetime(series, format='%Y%m%d%H%M%S', errors='coerce')
        
        # YYYYMMDD format (8 digits)
        elif re.match(r'^\d{8}$', sample_value):
            logger.info(f"Detected YYYYMMDD format in column '{series.name}'")
            return pd.to_datetime(series, format='%Y%m%d', errors='coerce')
        
        # Try pandas automatic inference for other formats
        else:
            logger.info(f"Attempting automatic datetime parsing for column '{series.name}'")
            return pd.to_datetime(series, errors='coerce')
    
    except Exception as e:
        logger.warning(f"Failed to convert column '{series.name}' to datetime: {e}")
        return None


def convert_to_numeric(series: pd.Series) -> Optional[pd.Series]:
    """
    Convert a string series to numeric.
    
    Args:
        series: Pandas series to convert
    
    Returns:
        Converted numeric series, or None if conversion fails
    """
    try:
        # Try to convert to numeric
        converted = pd.to_numeric(series, errors='coerce')
        
        # Check if conversion was successful for most values
        non_null_original = series.dropna()
        non_null_converted = converted.dropna()
        
        if len(non_null_original) > 0:
            success_rate = len(non_null_converted) / len(non_null_original)
            if success_rate >= 0.9:
                logger.info(f"Successfully converted column '{series.name}' to numeric ({success_rate:.1%} success rate)")
                return converted
            else:
                logger.debug(f"Low success rate ({success_rate:.1%}) for numeric conversion of column '{series.name}'")
                return None
        
        return None
    
    except Exception as e:
        logger.warning(f"Failed to convert column '{series.name}' to numeric: {e}")
        return None


def detect_column_type(column: pd.Series, threshold: float = 0.9) -> str:
    """
    Detect the expected type of a column.
    
    Args:
        column: Pandas series to analyze
        threshold: Minimum proportion of values that must match the type (default: 0.9)
    
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
    if is_datetime_string(column, threshold):
        return 'datetime'
    
    # Try numeric
    if is_numeric_string(column, threshold):
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


def detect_and_convert_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Automatically detect and convert string columns to appropriate types.
    
    This function analyzes each string column in the dataframe and attempts to
    convert it to numeric or datetime types if the content matches those patterns.
    
    Args:
        df: Input dataframe
    
    Returns:
        Dataframe with converted types
    """
    if df.empty:
        return df
    
    df_converted = df.copy()
    conversion_summary = {
        'numeric': [],
        'datetime': [],
        'unchanged': []
    }
    
    for col in df_converted.columns:
        series = df_converted[col]
        
        # Skip if already numeric or datetime
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            continue
        
        # Only process object (string) columns
        if series.dtype != 'object':
            continue
        
        # Detect column type
        detected_type = detect_column_type(series)
        
        # Convert to detected type
        if detected_type != 'string':
            converted = convert_column_to_type(series, detected_type)
            if not converted.isna().all():
                df_converted[col] = converted
                conversion_summary[detected_type].append(col)
                logger.info(f"Converted column '{col}' to {detected_type}")
            else:
                conversion_summary['unchanged'].append(col)
        else:
            conversion_summary['unchanged'].append(col)
    
    # Log summary
    if conversion_summary['numeric'] or conversion_summary['datetime']:
        logger.info(f"Type conversion summary: "
                   f"{len(conversion_summary['numeric'])} numeric, "
                   f"{len(conversion_summary['datetime'])} datetime, "
                   f"{len(conversion_summary['unchanged'])} unchanged")
    
    return df_converted
