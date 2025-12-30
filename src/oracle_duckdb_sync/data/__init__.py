"""Data processing, type conversion, and query utilities."""

from oracle_duckdb_sync.data.converter import (
    is_numeric_string,
    is_datetime_string,
    convert_to_numeric,
    convert_to_datetime,
    detect_column_type,
    convert_column_to_type,
    detect_and_convert_types,
    detect_convertible_columns,
    convert_selected_columns
)
from oracle_duckdb_sync.data.query import (
    get_available_tables,
    determine_default_table_name,
    get_table_row_count,
    query_duckdb_table,
    query_duckdb_table_with_conversion_ui,
    fetch_raw_data,
    cached_convert_dataframe,
    query_duckdb_table_cached,
    query_duckdb_table_aggregated
)
from oracle_duckdb_sync.data.lttb import lttb_downsample, lttb_downsample_multi_y

__all__ = [
    # Converter functions
    'is_numeric_string',
    'is_datetime_string',
    'convert_to_numeric',
    'convert_to_datetime',
    'detect_column_type',
    'convert_column_to_type',
    'detect_and_convert_types',
    'detect_convertible_columns',
    'convert_selected_columns',
    # Query functions
    'get_available_tables',
    'determine_default_table_name',
    'get_table_row_count',
    'query_duckdb_table',
    'query_duckdb_table_with_conversion_ui',
    'fetch_raw_data',
    'cached_convert_dataframe',
    'query_duckdb_table_cached',
    'query_duckdb_table_aggregated',
    # LTTB functions
    'lttb_downsample',
    'lttb_downsample_multi_y'
]
