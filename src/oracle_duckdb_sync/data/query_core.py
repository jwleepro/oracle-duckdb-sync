"""
Core query module - UI-independent data query functions.

This module provides pure data query functionality without any UI dependencies.
It can be used by any presentation layer (Streamlit, Flask, CLI, etc.).
"""

import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from ..database.duckdb_source import DuckDBSource
from ..config import Config
from ..data.converter import detect_and_convert_types
from ..log.logger import setup_logger

logger = setup_logger(__name__)


def get_available_tables(duckdb: DuckDBSource) -> List[str]:
    """
    Get list of available tables in DuckDB.
    
    Args:
        duckdb: DuckDBSource instance
    
    Returns:
        List of table names
    """
    try:
        available_tables = duckdb.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
            ORDER BY table_name
        """)
        table_list = [row[0] for row in available_tables] if available_tables else []
        return table_list
    except Exception as e:
        logger.warning(f"Failed to get table list: {e}")
        return []


def determine_default_table_name(config: Config, table_list: List[str]) -> str:
    """
    Determine default table name for query based on configuration.
    
    Args:
        config: Configuration object
        table_list: List of available tables

    Returns:
        Default table name (from SYNC_DUCKDB_TABLE config or first available table)
    """
    if config.sync_duckdb_table:
        return config.sync_duckdb_table
    elif table_list:
        return table_list[0]
    else:
        return "sync_table"


def get_table_row_count(duckdb: DuckDBSource, table_name: str) -> int:
    """
    Get total row count for a table.

    Args:
        duckdb: DuckDBSource instance
        table_name: Name of table to count

    Returns:
        Total number of rows, or 0 if error
    """
    try:
        result = duckdb.execute(f"SELECT COUNT(*) FROM {table_name}")
        return result[0][0] if result else 0
    except Exception as e:
        logger.error(f"Failed to get row count: {e}")
        return 0


def query_table_raw(duckdb: DuckDBSource, 
                    table_name: str, 
                    limit: int = 100) -> Dict[str, Any]:
    """
    Query DuckDB table and return raw DataFrame.
    
    Args:
        duckdb: DuckDBSource instance
        table_name: Table name to query
        limit: Maximum rows to fetch
    
    Returns:
        Dictionary with success status, DataFrame, and metadata
    """
    try:
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        logger.info(f"Executing query: {query}")
        
        result = duckdb.execute(query)
        
        if not result:
            return {
                'success': False,
                'error': f"No data found in table '{table_name}'",
                'df': None
            }
        
        # Convert to DataFrame
        conn = duckdb.get_connection()
        df = conn.execute(query).df()
        
        if df is None or len(df) == 0:
            # Check if table exists
            tables = duckdb.execute("SHOW TABLES")
            return {
                'success': False,
                'error': f"Table '{table_name}' is empty or does not exist",
                'df': None,
                'available_tables': [t[0] for t in tables] if tables else []
            }
        
        return {
            'success': True,
            'df': df,
            'row_count': len(df),
            'table_name': table_name
        }
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'df': None
        }


def query_table_with_conversion(duckdb: DuckDBSource,
                                 table_name: str,
                                 limit: int = 100,
                                 auto_convert: bool = True) -> Dict[str, Any]:
    """
    Query DuckDB table with automatic type conversion.
    
    Args:
        duckdb: DuckDBSource instance
        table_name: Table name to query
        limit: Maximum rows to fetch
        auto_convert: Whether to automatically convert types
    
    Returns:
        Dictionary with success status, converted DataFrame, and conversion metadata
    """
    # First get raw data
    raw_result = query_table_raw(duckdb, table_name, limit)
    
    if not raw_result['success']:
        return raw_result
    
    df_raw = raw_result['df']
    
    if not auto_convert:
        return {
            'success': True,
            'df_converted': df_raw,
            'df_raw': df_raw,
            'conversions': {},
            'row_count': len(df_raw),
            'table_name': table_name
        }
    
    # Apply automatic type conversion
    try:
        df_converted, conversions = detect_and_convert_types(df_raw)
        
        return {
            'success': True,
            'df_converted': df_converted,
            'df_raw': df_raw,
            'conversions': conversions,
            'row_count': len(df_converted),
            'table_name': table_name
        }
    except Exception as e:
        logger.error(f"Type conversion failed: {e}")
        return {
            'success': True,  # Query succeeded, only conversion failed
            'df_converted': df_raw,
            'df_raw': df_raw,
            'conversions': {},
            'conversion_error': str(e),
            'row_count': len(df_raw),
            'table_name': table_name
        }


def query_table_aggregated(duckdb: DuckDBSource,
                           table_name: str,
                           time_column: str,
                           value_columns: List[str],
                           interval: str = '1h') -> Dict[str, Any]:
    """
    Query table with time-based aggregation.
    
    Args:
        duckdb: DuckDBSource instance
        table_name: Table name
        time_column: Timestamp column name
        value_columns: Columns to aggregate
        interval: Time interval (e.g., '1h', '1d')
    
    Returns:
        Dictionary with aggregated data
    """
    try:
        # Build aggregation query
        agg_parts = []
        for col in value_columns:
            agg_parts.append(f"AVG({col}) as {col}_avg")
            agg_parts.append(f"MIN({col}) as {col}_min")
            agg_parts.append(f"MAX({col}) as {col}_max")
        
        agg_clause = ", ".join(agg_parts)
        
        query = f"""
            SELECT 
                time_bucket(INTERVAL '{interval}', {time_column}) as time_bucket,
                COUNT(*) as point_count,
                {agg_clause}
            FROM {table_name}
            GROUP BY time_bucket
            ORDER BY time_bucket
        """
        
        logger.info(f"Executing aggregation query with interval {interval}")
        
        conn = duckdb.get_connection()
        df_agg = conn.execute(query).df()
        
        if df_agg is None or len(df_agg) == 0:
            return {
                'success': False,
                'error': 'No data returned from aggregation query',
                'df_aggregated': None
            }
        
        return {
            'success': True,
            'df_aggregated': df_agg,
            'row_count': len(df_agg),
            'table_name': table_name,
            'interval': interval,
            'query_mode': 'aggregated'
        }
        
    except Exception as e:
        logger.error(f"Aggregation query failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'df_aggregated': None
        }


def detect_time_column(df: pd.DataFrame) -> Optional[str]:
    """
    Detect timestamp column in DataFrame.
    
    Args:
        df: DataFrame to analyze
    
    Returns:
        Name of timestamp column, or None if not found
    """
    # Check for datetime columns
    datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
    if datetime_cols:
        return datetime_cols[0]
    
    # Check for common timestamp column names
    common_names = ['timestamp', 'time', 'datetime', 'date', 'created_at', 'updated_at']
    for name in common_names:
        if name.lower() in [col.lower() for col in df.columns]:
            return name
    
    return None


def detect_numeric_columns(df: pd.DataFrame) -> List[str]:
    """
    Detect numeric columns in DataFrame.
    
    Args:
        df: DataFrame to analyze
    
    Returns:
        List of numeric column names
    """
    return df.select_dtypes(include=['number']).columns.tolist()
