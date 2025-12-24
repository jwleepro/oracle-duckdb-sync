"""
Data query module for Oracle-DuckDB Sync Dashboard.

This module provides functions for querying DuckDB tables and managing
table metadata.
"""

import streamlit as st
import pandas as pd
from oracle_duckdb_sync.duckdb_source import DuckDBSource
from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.data_converter import detect_and_convert_types
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
        oracle_table_parts = config.sync_oracle_table.split('.')
        return oracle_table_parts[-1].lower()  # Get last part (table name) and lowercase
    else:
        return table_list[0] if table_list else "sync_table"


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
        
        # Apply automatic type conversion for VARCHAR2 columns
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
