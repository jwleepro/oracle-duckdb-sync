import streamlit as st
import time
from oracle_duckdb_sync.config import load_config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.ui.handlers import (
    handle_test_sync,
    handle_full_sync,
    render_sync_status_ui
)
from oracle_duckdb_sync.ui.session_state import (
    initialize_session_state,
    release_sync_lock,
    SYNC_PROGRESS_REFRESH_INTERVAL
)
from oracle_duckdb_sync.data.query_core import (
    get_available_tables,
    determine_default_table_name,
    get_table_row_count,
    query_table_with_conversion
)
# Import aggregated query from old module until migrated
from oracle_duckdb_sync.data.query import (
    query_duckdb_table_cached,
    query_duckdb_table_aggregated
)
from oracle_duckdb_sync.ui.visualization import render_data_visualization

# Set up logger for app.py
app_logger = setup_logger('StreamlitApp')


def check_progress():
    """Check for progress updates from worker"""
    import queue
    try:
        while not st.session_state.progress_queue.empty():
            msg = st.session_state.progress_queue.get_nowait()
            
            if msg['type'] == 'progress':
                st.session_state.sync_progress = msg['data']
            elif msg['type'] == 'complete':
                st.session_state.sync_status = 'completed'
                st.session_state.sync_result = msg['data']
                # Release lock on completion
                release_sync_lock()
            elif msg['type'] == 'error':
                st.session_state.sync_status = 'error'
                st.session_state.sync_error = msg['data']
                # Release lock on error
                release_sync_lock()
    except queue.Empty:
        pass


def main():
    st.set_page_config(page_title="Oracle-DuckDB Sync Dashboard", layout="wide")
    st.title("데이터 동기화 및 분석 대시보드")
    
    # Initialize session state
    initialize_session_state()

    try:
        config = load_config()

        if not config.sync_oracle_table:
            raise ValueError("SYNC_ORACLE_TABLE이 .env 파일에 설정되지 않았습니다.")

        duckdb = DuckDBSource(config)
    except Exception as e:
        app_logger.error(f"설정 로드 실패: {e}")
        st.error(f"설정을 로드할 수 없습니다: {e}")
        return
    
    # Sidebar 메뉴 구성을 바꾸려면 여길 고쳐야 함. jwlee
    st.sidebar.header("동기화 설정")
    
    # Display current configuration from .env
    st.sidebar.info(f"📋 설정된 테이블: {config.sync_oracle_table}")
    
    # Use .env configuration
    table_name = config.sync_oracle_table
    primary_key = config.sync_primary_key
    time_column = config.duckdb_time_column  # Use DuckDB-specific time column
    
    # Test sync button with row limit
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧪 테스트 동기화")
    test_row_limit = st.sidebar.number_input(
        "테스트 행 수", 
        min_value=10000, 
        max_value=100000, 
        value=100000, 
        step=10000,
        help="테스트로 가져올 최대 행 수 (기본: 10만)"
    )
    
    # Check if sync is running and update progress
    if st.session_state.sync_status == 'running':
        check_progress()
        # Use st.empty() placeholder for progress updates without blocking
        # Note: Removed automatic rerun to prevent UI lock
    
    # Render sync status UI (running, completed, or error)
    render_sync_status_ui()
    
    # Test sync button - only enabled when idle
    if st.sidebar.button("🧪 테스트 동기화 실행 (제한된 행)", 
                         disabled=(st.session_state.sync_status == 'running')):
        handle_test_sync(config, test_row_limit, table_name)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 전체 동기화")
    
    
    if st.sidebar.button("🚀 전체 동기화 실행", 
                         disabled=(st.session_state.sync_status == 'running')):
        handle_full_sync(config, table_name, primary_key, time_column, duckdb)
        
    #메인 화면
    # Show available tables in DuckDB
    table_list = get_available_tables(duckdb)
    
    # Determine default table name
    default_table = determine_default_table_name(config, table_list)    
    
    duckdb_table_name = st.text_input("조회할 테이블명", value=default_table, help="DuckDB 테이블명 (소문자, 스키마 없이)")

    # Query DuckDB table with caching for type conversion
    row_count = get_table_row_count(duckdb, duckdb_table_name)

    # Resolution selector for time bucket aggregation
    st.subheader("📊 데이터 조회 옵션")

    col1, col2 = st.columns([2, 1])

    with col1:
        query_mode = st.radio(
            "조회 모드",
            options=["집계 뷰 (빠름)", "상세 뷰 (전체 데이터 + LTTB)"],
            index=0,
            help="집계 뷰: 빠른 초기 로딩, 트렌드 확인용 | 상세 뷰: 이상치 포함 전체 데이터"
        )

    with col2:
        if query_mode == "집계 뷰 (빠름)":
            resolution = st.selectbox(
                "시간 해상도",
                options=["1 minute", "10 minutes", "1 hour"],
                index=1,
                help="데이터 집계 간격 (작을수록 상세하지만 느림)"
            )
        else:
            resolution = None
            st.info("💡 LTTB 샘플링 적용됨")
    
    if st.button("조회"):
        if query_mode == "집계 뷰 (빠름)":
            # Use time bucket aggregation for fast initial view
            with st.spinner(f"집계 데이터 조회 중... (해상도: {resolution})"):
                agg_result = query_duckdb_table_aggregated(
                    duckdb,
                    duckdb_table_name,
                    time_column=time_column,
                    interval=resolution
                )

            if agg_result['success']:
                # Store aggregated result with query mode info
                st.session_state.query_result = {
                    'df_converted': agg_result['df_aggregated'],
                    'table_name': agg_result['table_name'],
                    'success': True,
                    'query_mode': 'aggregated',
                    'interval': agg_result['interval'],
                    'numeric_cols': agg_result.get('numeric_cols', [])
                }
                st.success(f"✅ 집계 완료: {len(agg_result['df_aggregated'])} 시간 구간")
            else:
                st.error(f"집계 쿼리 오류: {agg_result['error']}")
                st.session_state.query_result = None

        else:
            # Use detailed view with LTTB downsampling
            with st.spinner(f"전체 데이터 조회 중... ({row_count:,}행)"):
                duckdb_query_result = query_duckdb_table_cached(
                    duckdb,
                    duckdb_table_name,
                    row_count,
                    time_column=time_column
                )

            if duckdb_query_result['success']:
                # Add query mode info
                duckdb_query_result['query_mode'] = 'detailed'
                st.session_state.query_result = duckdb_query_result
            else:
                st.session_state.query_result = None            
            
    st.subheader("시각화")
    # Display cached query result if available and successful
    if st.session_state.query_result and st.session_state.query_result.get('success') and st.session_state.query_result.get('df_converted') is not None:
        df_converted = st.session_state.query_result['df_converted']
        visualization_table_name = st.session_state.query_result['table_name']
        query_mode = st.session_state.query_result.get('query_mode', 'detailed')

        # Show query mode info
        if query_mode == 'aggregated':
            interval = st.session_state.query_result.get('interval', 'unknown')
            st.info(f"📊 집계 뷰 표시 중 (해상도: {interval}, 총 {len(df_converted)} 시간 구간)")
        else:
            st.info(f"📊 상세 뷰 표시 중 (총 {len(df_converted):,}행)")

        # Render visualization
        render_data_visualization(df_converted, visualization_table_name, query_mode=query_mode)        

    st.subheader("데이터 조회")

    if st.session_state.query_result and st.session_state.query_result.get('success'):
        # Get df_converted from query_result to avoid variable scope issues
        df_converted = st.session_state.query_result.get('df_converted')

        if df_converted is not None:
            # Display row count
            total_rows = len(df_converted)
            st.info(f"📊 총 {total_rows:,}행 조회됨")

            # Limit displayed rows to prevent MessageSizeError
            max_display_rows = st.number_input(
                "표시할 최대 행 수",
                min_value=100,
                max_value=1000,
                value=100,
                step=100,
                help="브라우저 성능을 위해 표시되는 행 수를 제한합니다."
            )

            # Show data with row limit - add spinner to prevent UI blocking
            with st.spinner(f"데이터 테이블 렌더링 중... ({min(total_rows, max_display_rows):,}행)"):
                if total_rows > max_display_rows:
                    st.warning(f"⚠️ 성능을 위해 {max_display_rows:,}행만 표시합니다. (전체: {total_rows:,}행)")
                    st.dataframe(df_converted.head(max_display_rows))
                else:
                    st.dataframe(df_converted)

if __name__ == "__main__":
    main()
