"""Data processing, type conversion, and query utilities."""

from oracle_duckdb_sync.data.converter import (
    convert_column_to_type,
    convert_selected_columns,
    convert_to_datetime,
    convert_to_numeric,
    detect_and_convert_types,
    detect_column_type,
    detect_convertible_columns,
    is_datetime_string,
    is_numeric_string,
)
from oracle_duckdb_sync.data.lttb import lttb_downsample, lttb_downsample_multi_y
from oracle_duckdb_sync.data.query import (
    determine_default_table_name,
    get_available_tables,
    get_table_row_count,
    query_duckdb_table,
    query_duckdb_table_aggregated,
    query_duckdb_table_cached,
    query_duckdb_table_with_conversion_ui,
)

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
    'query_duckdb_table_cached',
    'query_duckdb_table_aggregated',
    # LTTB functions
    'lttb_downsample',
    'lttb_downsample_multi_y'
]
