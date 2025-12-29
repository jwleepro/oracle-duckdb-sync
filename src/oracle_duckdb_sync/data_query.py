"""
Data query module for Oracle-DuckDB Sync Dashboard.

This module provides functions for querying DuckDB tables and managing
table metadata.
"""

import streamlit as st
import pandas as pd
from oracle_duckdb_sync.duckdb_source import DuckDBSource
from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.data_converter import (
    detect_and_convert_types,
    detect_convertible_columns,
    convert_selected_columns
)
from oracle_duckdb_sync.logger import setup_logger

# Set up logger
query_logger = setup_logger('DataQuery')


def get_available_tables(duckdb: DuckDBSource) -> list:
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
        
        if table_list:
            st.info(f"📊 사용 가능한 테이블: {', '.join(table_list)}")
        else:
            st.warning("⚠️ DuckDB에 테이블이 없습니다. 먼저 '지금 동기화 실행'을 클릭하세요.")
        
        return table_list
    except Exception as e:
        query_logger.warning(f"테이블 목록 조회 실패: {e}")
        st.warning(f"테이블 목록 조회 실패: {e}")
        return []


def determine_default_table_name(config: Config, table_list: list) -> str:
    """
    Determine default table name for query based on configuration.
    
    Args:
        config: Configuration object
        table_list: List of available tables
    
    Returns:
        Default table name
    """
    if config.sync_duckdb_table:
        return config.sync_duckdb_table
    elif config.sync_oracle_table:
        # Remove schema prefix and convert to lowercase
        oracle_table_parts = ""
        if config.sync_oracle_schema:
            oracle_table_parts = config.sync_oracle_schema + "." + config.sync_oracle_table
        else:
            oracle_table_parts = config.sync_oracle_table
        
        oracle_table_parts += config.sync_oracle_table
        return oracle_table_parts[-1].lower()  # Get last part (table name) and lowercase
    else:
        return table_list[0] if table_list else "sync_table"


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
        # Show query being executed
        result = duckdb.execute(f"SELECT COUNT(*) FROM {table_name}")
        return result[0][0] if result else 0
    except Exception as e:
        query_logger.error(f"테이블 row 수 조회 실패: {e}")
        return 0

def query_duckdb_table(duckdb: DuckDBSource, table_name: str, limit: int = 100) -> dict:
    """
    Query DuckDB table and return converted DataFrame with metadata.
    
    Args:
        duckdb: DuckDBSource instance
        table_name: Name of table to query
        limit: Maximum number of rows to return
    
    Returns:
        Dictionary containing:
            - df_converted: Converted DataFrame
            - table_name: Table name
            - type_changes: Dictionary of type conversions applied
            - success: Boolean indicating success
            - error: Error message if failed
    """
    try:
        # Show query being executed
        st.info(f"실행 쿼리: SELECT * FROM {table_name} LIMIT {limit}")
        
        # Execute query
        data = duckdb.execute(f"SELECT * FROM {table_name} LIMIT {limit}")

        if not data or len(data) == 0:
            st.warning(f"조회 결과가 없습니다. 테이블 '{table_name}'이(가) 비어있거나 존재하지 않습니다.")
            # Show available tables
            try:
                tables = duckdb.conn.execute("SHOW TABLES").fetchall()
                st.info(f"사용 가능한 테이블: {[t[0] for t in tables]}")
            except:
                pass
            
            return {
                'df_converted': None,
                'table_name': table_name,
                'type_changes': {},
                'success': False,
                'error': 'No data returned'
            }
        
        # Get column names from DuckDB
        result = duckdb.conn.execute(f"SELECT * FROM {table_name} LIMIT 0")
        columns = [desc[0] for desc in result.description]
        df = pd.DataFrame(data, columns=columns)

        st.success(f"✅ {len(df)} 행 조회 완료")

        # Apply automatic type conversion for VARCHAR2 columns with spinner
        with st.spinner("데이터 타입 자동 변환 중..."):
            query_logger.info("Applying automatic type conversion to detect numeric and datetime columns")
            df_converted = detect_and_convert_types(df)
        
        # Show conversion results
        original_types = df.dtypes.to_dict()
        converted_types = df_converted.dtypes.to_dict()
        type_changes = {col: (str(original_types[col]), str(converted_types[col])) 
                       for col in df.columns 
                       if str(original_types[col]) != str(converted_types[col])}
        
        if type_changes:
            with st.expander("🔄 자동 타입 변환 결과"):
                for col, (old_type, new_type) in type_changes.items():
                    st.text(f"  • {col}: {old_type} → {new_type}")
            query_logger.info(f"Type conversions applied: {type_changes}")
        
        return {
            'df_converted': df_converted,
            'table_name': table_name,
            'type_changes': type_changes,
            'success': True,
            'error': None
        }
    except Exception as e:
        # Log error to file
        query_logger.error(f"데이터 조회 오류: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        query_logger.error(f"Traceback:\n{error_traceback}")
        
        # Display error to user
        st.error(f"데이터 조회 오류: {e}")
        st.code(error_traceback)
        
        return {
            'df_converted': None,
            'table_name': table_name,
            'type_changes': {},
            'success': False,
            'error': str(e)
        }


def _fetch_raw_data(conn, table_name: str, limit: int) -> dict:
    """
    Fetch raw data from DuckDB without type conversion.

    Args:
        conn: DuckDB connection object
        table_name: Name of table to query
        limit: Maximum number of rows to return

    Returns:
        Dictionary containing raw data, columns, or error
    """
    try:
        # Execute query
        data = conn.execute(f"SELECT * FROM {table_name} LIMIT {limit}").fetchall()

        if not data or len(data) == 0:
            return {
                'data': None,
                'columns': None,
                'success': False,
                'error': 'No data returned'
            }

        # Get column names
        result = conn.execute(f"SELECT * FROM {table_name} LIMIT 0")
        columns = [desc[0] for desc in result.description]

        return {
            'data': data,
            'columns': columns,
            'success': True,
            'error': None
        }
    except Exception as e:
        query_logger.error(f"Data fetch error: {e}")
        import traceback
        query_logger.error(f"Traceback:\n{traceback.format_exc()}")
        return {
            'data': None,
            'columns': None,
            'success': False,
            'error': str(e)
        }


def _fetch_incremental_data(conn, table_name: str, time_column: str, last_timestamp, limit: int = None) -> dict:
    """
    Fetch only new/updated data since the last timestamp.
    
    Args:
        conn: DuckDB connection object
        table_name: Name of table to query
        time_column: Name of timestamp column for incremental detection
        last_timestamp: Last timestamp from previous query (can be None for initial load)
        limit: Optional maximum number of rows to return
    
    Returns:
        Dictionary containing incremental data, columns, max_timestamp, or error
    """
    try:
        # Build query based on whether we have a previous timestamp
        if last_timestamp is None:
            # Initial load - fetch all data
            if limit:
                query = f"SELECT * FROM {table_name} ORDER BY {time_column} LIMIT {limit}"
            else:
                query = f"SELECT * FROM {table_name} ORDER BY {time_column}"
        else:
            # Incremental load - fetch only new data
            if limit:
                query = f"SELECT * FROM {table_name} WHERE {time_column} > '{last_timestamp}' ORDER BY {time_column} LIMIT {limit}"
            else:
                query = f"SELECT * FROM {table_name} WHERE {time_column} > '{last_timestamp}' ORDER BY {time_column}"
        
        query_logger.info(f"Incremental query: {query}")
        data = conn.execute(query).fetchall()
        
        # Get column names
        result = conn.execute(f"SELECT * FROM {table_name} LIMIT 0")
        columns = [desc[0] for desc in result.description]
        
        # Find max timestamp from fetched data
        max_timestamp = None
        if data and time_column in columns:
            time_col_idx = columns.index(time_column)
            max_timestamp = max(row[time_col_idx] for row in data)
        
        return {
            'data': data,
            'columns': columns,
            'max_timestamp': max_timestamp,
            'row_count': len(data) if data else 0,
            'success': True,
            'error': None
        }
    except Exception as e:
        query_logger.error(f"Incremental data fetch error: {e}")
        import traceback
        query_logger.error(f"Traceback:\n{traceback.format_exc()}")
        return {
            'data': None,
            'columns': None,
            'max_timestamp': None,
            'row_count': 0,
            'success': False,
            'error': str(e)
        }


def _merge_dataframes(existing_df: pd.DataFrame, new_df: pd.DataFrame, time_column: str) -> pd.DataFrame:
    """
    Merge existing cached DataFrame with new incremental data.
    
    Args:
        existing_df: Existing cached DataFrame (can be None)
        new_df: Newly fetched and converted DataFrame
        time_column: Name of timestamp column for sorting
    
    Returns:
        Merged DataFrame sorted by time_column
    """
    if existing_df is None or existing_df.empty:
        return new_df
    
    if new_df is None or new_df.empty:
        return existing_df
    
    # Concatenate and sort by timestamp
    merged_df = pd.concat([existing_df, new_df], ignore_index=True)
    
    # Sort by timestamp if column exists
    if time_column in merged_df.columns:
        merged_df = merged_df.sort_values(by=time_column).reset_index(drop=True)
    
    query_logger.info(f"Merged DataFrames: {len(existing_df)} + {len(new_df)} = {len(merged_df)} rows")
    
    return merged_df


def _detect_conversion_suggestions(df: pd.DataFrame) -> dict:
    """
    Detect which columns can be converted to numeric or datetime types.

    Args:
        df: Input DataFrame

    Returns:
        Dictionary with conversion suggestions
        Format: {'column_name': 'numeric'|'datetime'}
    """
    return detect_convertible_columns(df)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_convert_dataframe(data: list, columns: list, table_name: str, selected_conversions: dict = None) -> dict:
    """
    Cached function that converts raw data to typed DataFrame.

    This function is cached to avoid redundant type conversions.
    It only accepts serializable parameters (lists, not connection objects).

    Args:
        data: Raw data rows (list of tuples/lists)
        columns: Column names
        table_name: Table name for logging
        selected_conversions: Optional dict of columns to convert
                            Format: {'column_name': 'numeric'|'datetime'}
                            If None, converts all detectable columns automatically

    Returns:
        Dictionary with converted DataFrame and type changes
    """
    try:
        # Create DataFrame
        df = pd.DataFrame(data, columns=columns)

        # Apply type conversion
        if selected_conversions is None:
            # Automatic conversion (default behavior)
            query_logger.info(f"Applying automatic type conversion to {table_name}: {len(df)} rows")
            df_converted = detect_and_convert_types(df)
        else:
            # Convert only selected columns
            query_logger.info(f"Applying selective type conversion to {table_name}: {len(selected_conversions)} columns")
            df_converted = convert_selected_columns(df, selected_conversions)

        # Calculate type changes
        original_types = df.dtypes.to_dict()
        converted_types = df_converted.dtypes.to_dict()
        type_changes = {col: (str(original_types[col]), str(converted_types[col]))
                       for col in df.columns
                       if str(original_types[col]) != str(converted_types[col])}

        query_logger.info(f"Type conversion complete (cached): {len(type_changes)} conversions")

        return {
            'df_converted': df_converted,
            'type_changes': type_changes,
            'success': True,
            'error': None
        }
    except Exception as e:
        query_logger.error(f"Type conversion error: {e}")
        import traceback
        query_logger.error(f"Traceback:\n{traceback.format_exc()}")
        return {
            'df_converted': None,
            'type_changes': {},
            'success': False,
            'error': str(e)
        }


def query_duckdb_table_cached(duckdb: DuckDBSource, table_name: str, limit: int = 100, time_column: str = None) -> dict:
    """
    Query DuckDB table with incremental caching for type conversion.
    
    This function uses timestamp-based incremental loading:
    - On first query: Fetches all data up to limit and caches converted result
    - On subsequent queries: Only fetches new data since last timestamp, converts it, and merges with cache
    
    Args:
        duckdb: DuckDBSource instance
        table_name: Name of table to query
        limit: Maximum number of rows to return (applies to initial load only)
        time_column: Name of timestamp column for incremental detection (required for incremental mode)
    
    Returns:
        Dictionary containing:
            - df_converted: Converted DataFrame
            - table_name: Table name
            - type_changes: Dictionary of type conversions applied
            - success: Boolean indicating success
            - error: Error message if failed
            - is_incremental: Boolean indicating if incremental data was loaded
    """
    # Initialize cache structures in session state if needed
    if 'converted_data_cache' not in st.session_state:
        st.session_state.converted_data_cache = {}
    if 'cache_metadata' not in st.session_state:
        st.session_state.cache_metadata = {}
    
    # Check if we have cached data for this table
    cache_key = table_name
    has_cache = cache_key in st.session_state.converted_data_cache
    last_timestamp = st.session_state.cache_metadata.get(cache_key, {}).get('last_timestamp')
    
    # Determine if incremental mode is possible
    use_incremental = time_column is not None and has_cache and last_timestamp is not None
    
    if use_incremental:
        st.info(f"🔄 증분 조회: {table_name} (마지막: {last_timestamp})")
        
        # Fetch only incremental data
        fetch_result = _fetch_incremental_data(duckdb.conn, table_name, time_column, last_timestamp, limit=None)
        
        if not fetch_result['success']:
            st.error(f"증분 데이터 조회 오류: {fetch_result['error']}")
            return {
                'df_converted': st.session_state.converted_data_cache.get(cache_key),
                'table_name': table_name,
                'type_changes': {},
                'success': False,
                'error': fetch_result['error'],
                'is_incremental': True
            }
        
        if fetch_result['row_count'] == 0:
            st.info("✅ 새로운 데이터가 없습니다. 캐시된 데이터를 사용합니다.")
            cached_df = st.session_state.converted_data_cache.get(cache_key)
            return {
                'df_converted': cached_df,
                'table_name': table_name,
                'type_changes': {},
                'success': True,
                'error': None,
                'is_incremental': True
            }
        
        # Convert incremental data
        data = fetch_result['data']
        columns = fetch_result['columns']
        
        st.info(f"📊 새 데이터 {fetch_result['row_count']}행 발견, 변환 중...")
        
        # Convert to DataFrame and apply type conversion with spinner
        df_new = pd.DataFrame(data, columns=columns)
        with st.spinner(f"새 데이터 타입 변환 중... ({fetch_result['row_count']}행)"):
            df_new_converted = detect_and_convert_types(df_new)
        
        # Merge with existing cache
        existing_df = st.session_state.converted_data_cache.get(cache_key)
        df_merged = _merge_dataframes(existing_df, df_new_converted, time_column)
        
        # Update cache
        st.session_state.converted_data_cache[cache_key] = df_merged
        st.session_state.cache_metadata[cache_key] = {
            'last_timestamp': fetch_result['max_timestamp'],
            'row_count': len(df_merged),
            'last_update': pd.Timestamp.now()
        }
        
        # Calculate type changes for new data only
        original_types = df_new.dtypes.to_dict()
        converted_types = df_new_converted.dtypes.to_dict()
        type_changes = {col: (str(original_types[col]), str(converted_types[col]))
                       for col in df_new.columns
                       if str(original_types[col]) != str(converted_types[col])}
        
        st.success(f"✅ 증분 업데이트 완료: +{fetch_result['row_count']}행 → 총 {len(df_merged)}행")
        
        if type_changes:
            with st.expander("🔄 증분 데이터 타입 변환 결과"):
                for col, (old_type, new_type) in type_changes.items():
                    st.text(f"  • {col}: {old_type} → {new_type}")
        
        return {
            'df_converted': df_merged,
            'table_name': table_name,
            'type_changes': type_changes,
            'success': True,
            'error': None,
            'is_incremental': True
        }
    
    else:
        # Initial load or non-incremental mode
        if time_column:
            st.info(f"🔍 초기 조회: {table_name} (최대 {limit}행)")
            fetch_result = _fetch_incremental_data(duckdb.conn, table_name, time_column, None, limit)
        else:
            st.info(f"실행 쿼리: SELECT * FROM {table_name} LIMIT {limit}")
            fetch_result = _fetch_raw_data(duckdb.conn, table_name, limit)
            # Convert to same format as incremental fetch
            if fetch_result['success']:
                fetch_result['max_timestamp'] = None
                fetch_result['row_count'] = len(fetch_result['data']) if fetch_result['data'] else 0
        
        if not fetch_result['success']:
            if fetch_result['error'] == 'No data returned':
                st.warning(f"조회 결과가 없습니다. 테이블 '{table_name}'이(가) 비어있거나 존재하지 않습니다.")
                try:
                    tables = duckdb.conn.execute("SHOW TABLES").fetchall()
                    st.info(f"사용 가능한 테이블: {[t[0] for t in tables]}")
                except:
                    pass
            else:
                st.error(f"데이터 조회 오류: {fetch_result['error']}")
            
            return {
                'df_converted': None,
                'table_name': table_name,
                'type_changes': {},
                'success': False,
                'error': fetch_result['error'],
                'is_incremental': False
            }
        
        # Convert data types with spinner
        data = fetch_result['data']
        columns = fetch_result['columns']

        df_raw = pd.DataFrame(data, columns=columns)
        with st.spinner(f"데이터 타입 자동 변환 중... ({len(df_raw)}행)"):
            df_converted = detect_and_convert_types(df_raw)
        
        # Calculate type changes
        original_types = df_raw.dtypes.to_dict()
        converted_types = df_converted.dtypes.to_dict()
        type_changes = {col: (str(original_types[col]), str(converted_types[col]))
                       for col in df_raw.columns
                       if str(original_types[col]) != str(converted_types[col])}
        
        # Cache the result
        st.session_state.converted_data_cache[cache_key] = df_converted
        st.session_state.cache_metadata[cache_key] = {
            'last_timestamp': fetch_result['max_timestamp'],
            'row_count': len(df_converted),
            'last_update': pd.Timestamp.now()
        }
        
        st.success(f"✅ {len(df_converted)} 행 조회 완료")
        
        if type_changes:
            with st.expander("🔄 자동 타입 변환 결과"):
                for col, (old_type, new_type) in type_changes.items():
                    st.text(f"  • {col}: {old_type} → {new_type}")
        
        return {
            'df_converted': df_converted,
            'table_name': table_name,
            'type_changes': type_changes,
            'success': True,
            'error': None,
            'is_incremental': False
        }



def query_duckdb_table_with_conversion_ui(duckdb: DuckDBSource, table_name: str, limit: int = 100, time_column: str = None) -> dict:
    """
    Query DuckDB table with incremental loading and show UI for selecting type conversions.
    
    This function supports incremental loading:
    - On first query: Fetches data and shows UI for selecting conversions
    - On subsequent queries: Only fetches new data, applies same conversions, and merges
    
    Args:
        duckdb: DuckDBSource instance
        table_name: Name of table to query
        limit: Maximum number of rows to return (applies to initial load only)
        time_column: Name of timestamp column for incremental detection
    
    Returns:
        Dictionary containing converted DataFrame and metadata
    """
    # Initialize cache structures in session state if needed
    if 'converted_data_cache' not in st.session_state:
        st.session_state.converted_data_cache = {}
    if 'cache_metadata' not in st.session_state:
        st.session_state.cache_metadata = {}
    
    # Check if we have cached data for this table
    cache_key = f"{table_name}_ui"
    has_cache = cache_key in st.session_state.converted_data_cache
    cache_meta = st.session_state.cache_metadata.get(cache_key, {})
    last_timestamp = cache_meta.get('last_timestamp')
    saved_conversions = cache_meta.get('selected_conversions')
    
    # Determine if incremental mode is possible
    use_incremental = time_column is not None and has_cache and last_timestamp is not None
    
    if use_incremental:
        st.info(f"🔄 증분 조회: {table_name} (마지막: {last_timestamp})")
        
        # Fetch only incremental data
        fetch_result = _fetch_incremental_data(duckdb.conn, table_name, time_column, last_timestamp, limit=None)
        
        if not fetch_result['success']:
            st.error(f"증분 데이터 조회 오류: {fetch_result['error']}")
            return {
                'df_converted': st.session_state.converted_data_cache.get(cache_key),
                'table_name': table_name,
                'type_changes': {},
                'conversion_suggestions': {},
                'success': False,
                'error': fetch_result['error'],
                'is_incremental': True
            }
        
        if fetch_result['row_count'] == 0:
            st.info("✅ 새로운 데이터가 없습니다. 캐시된 데이터를 사용합니다.")
            cached_df = st.session_state.converted_data_cache.get(cache_key)
            return {
                'df_converted': cached_df,
                'table_name': table_name,
                'type_changes': {},
                'conversion_suggestions': {},
                'success': True,
                'error': None,
                'is_incremental': True
            }
        
        # Convert incremental data using saved conversion settings
        data = fetch_result['data']
        columns = fetch_result['columns']
        
        st.info(f"📊 새 데이터 {fetch_result['row_count']}행 발견, 변환 중...")
        
        df_new = pd.DataFrame(data, columns=columns)
        
        # Apply saved conversions from initial load
        if saved_conversions:
            df_new_converted = convert_selected_columns(df_new, saved_conversions)
        else:
            df_new_converted = detect_and_convert_types(df_new)
        
        # Merge with existing cache
        existing_df = st.session_state.converted_data_cache.get(cache_key)
        df_merged = _merge_dataframes(existing_df, df_new_converted, time_column)
        
        # Update cache
        st.session_state.converted_data_cache[cache_key] = df_merged
        st.session_state.cache_metadata[cache_key] = {
            'last_timestamp': fetch_result['max_timestamp'],
            'row_count': len(df_merged),
            'last_update': pd.Timestamp.now(),
            'selected_conversions': saved_conversions
        }
        
        # Calculate type changes for new data
        original_types = df_new.dtypes.to_dict()
        converted_types = df_new_converted.dtypes.to_dict()
        type_changes = {col: (str(original_types[col]), str(converted_types[col]))
                       for col in df_new.columns
                       if str(original_types[col]) != str(converted_types[col])}
        
        st.success(f"✅ 증분 업데이트 완료: +{fetch_result['row_count']}행 → 총 {len(df_merged)}행")
        
        if type_changes:
            with st.expander("🔄 증분 데이터 타입 변환 결과"):
                for col, (old_type, new_type) in type_changes.items():
                    st.text(f"  • {col}: {old_type} → {new_type}")
        
        return {
            'df_converted': df_merged,
            'table_name': table_name,
            'type_changes': type_changes,
            'conversion_suggestions': saved_conversions or {},
            'success': True,
            'error': None,
            'is_incremental': True
        }
    
    else:
        # Initial load - show UI for conversion selection
        if time_column:
            st.info(f"🔍 초기 조회: {table_name} (최대 {limit}행)")
            fetch_result = _fetch_incremental_data(duckdb.conn, table_name, time_column, None, limit)
        else:
            st.info(f"실행 쿼리: SELECT * FROM {table_name} LIMIT {limit}")
            fetch_result = _fetch_raw_data(duckdb.conn, table_name, limit)
            fetch_result['max_timestamp'] = None
            fetch_result['row_count'] = len(fetch_result['data']) if fetch_result['data'] else 0
        
        if not fetch_result['success']:
            if fetch_result['error'] == 'No data returned':
                st.warning(f"조회 결과가 없습니다. 테이블 '{table_name}'이(가) 비어있거나 존재하지 않습니다.")
                try:
                    tables = duckdb.conn.execute("SHOW TABLES").fetchall()
                    st.info(f"사용 가능한 테이블: {[t[0] for t in tables]}")
                except:
                    pass
            else:
                st.error(f"데이터 조회 오류: {fetch_result['error']}")
            
            return {
                'df_converted': None,
                'table_name': table_name,
                'type_changes': {},
                'conversion_suggestions': {},
                'success': False,
                'error': fetch_result['error'],
                'is_incremental': False
            }
        
        data = fetch_result['data']
        columns = fetch_result['columns']
        
        # Create DataFrame to detect conversions
        df_raw = pd.DataFrame(data, columns=columns)
        
        # Detect conversion suggestions
        suggestions = _detect_conversion_suggestions(df_raw)
        
        if not suggestions:
            # No conversions available, cache and return raw data
            st.info("📊 변환 가능한 컬럼이 없습니다. 모든 컬럼이 이미 적절한 타입입니다.")
            
            st.session_state.converted_data_cache[cache_key] = df_raw
            st.session_state.cache_metadata[cache_key] = {
                'last_timestamp': fetch_result['max_timestamp'],
                'row_count': len(df_raw),
                'last_update': pd.Timestamp.now(),
                'selected_conversions': None
            }
            
            return {
                'df_converted': df_raw,
                'table_name': table_name,
                'type_changes': {},
                'conversion_suggestions': {},
                'success': True,
                'error': None,
                'is_incremental': False
            }
        
        # Show UI for column selection
        with st.expander("🔧 타입 변환 설정", expanded=True):
            st.markdown("**변환 가능한 컬럼을 선택하세요:**")
            
            selected_conversions = {}
            
            for col, suggested_type in suggestions.items():
                # Show checkbox for each convertible column
                type_label = "숫자" if suggested_type == "numeric" else "날짜/시간"
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    should_convert = st.checkbox(
                        f"`{col}` → {type_label}",
                        value=True,  # Default to converting
                        key=f"convert_{table_name}_{col}"
                    )
                
                with col2:
                    # Show sample data
                    sample_values = df_raw[col].dropna().head(3).tolist()
                    st.caption(f"예: {', '.join(map(str, sample_values[:2]))}")
                
                if should_convert:
                    selected_conversions[col] = suggested_type
        
        # Apply selected conversions
        if selected_conversions:
            df_converted = convert_selected_columns(df_raw, selected_conversions)
        else:
            df_converted = df_raw
        
        # Calculate type changes
        original_types = df_raw.dtypes.to_dict()
        converted_types = df_converted.dtypes.to_dict()
        type_changes = {col: (str(original_types[col]), str(converted_types[col]))
                       for col in df_raw.columns
                       if str(original_types[col]) != str(converted_types[col])}
        
        # Cache the result with conversion settings
        st.session_state.converted_data_cache[cache_key] = df_converted
        st.session_state.cache_metadata[cache_key] = {
            'last_timestamp': fetch_result['max_timestamp'],
            'row_count': len(df_converted),
            'last_update': pd.Timestamp.now(),
            'selected_conversions': selected_conversions
        }
        
        st.success(f"✅ {len(df_converted)} 행 조회 완료")
        
        if type_changes:
            with st.expander("🔄 적용된 타입 변환"):
                for col, (old_type, new_type) in type_changes.items():
                    st.text(f"  • {col}: {old_type} → {new_type}")
        
        return {
            'df_converted': df_converted,
            'table_name': table_name,
            'type_changes': type_changes,
            'conversion_suggestions': suggestions,
            'success': True,
            'error': None,
            'is_incremental': False
        }
