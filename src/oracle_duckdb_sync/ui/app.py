import streamlit as st
import time
from oracle_duckdb_sync.config import load_config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger

# 🆕 Cache provider injection for framework independence
from oracle_duckdb_sync.adapters.streamlit_cache import StreamlitCacheProvider
from oracle_duckdb_sync import data

# 🆕 Use Application Service Layer instead of direct data access
from oracle_duckdb_sync.application.query_service import QueryService

# 🆕 Use StreamlitAdapter for UI abstraction
from oracle_duckdb_sync.adapters.streamlit_adapter import StreamlitAdapter
from oracle_duckdb_sync.application.ui_presenter import MessageContext
from oracle_duckdb_sync.ui.ui_helpers import show_table_list

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
# Legacy imports for backward compatibility (will be removed in Phase 3)
from oracle_duckdb_sync.data.query import (
    query_duckdb_table_cached,
)
from oracle_duckdb_sync.ui.visualization import render_data_visualization

# Set up logger for app.py
app_logger = setup_logger('StreamlitApp')

# 🆕 Initialize cache provider for data layer (enables UI framework independence)
# This allows data layer to use caching without directly depending on Streamlit
_cache_provider = StreamlitCacheProvider()
app_logger.info("Streamlit cache provider initialized for data layer")



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

    # 🆕 Initialize UI Adapter for framework-independent UI operations
    ui_adapter = StreamlitAdapter()
    app_logger.info("StreamlitAdapter initialized")

    try:
        config = load_config()

        if not config.sync_oracle_table:
            raise ValueError("SYNC_ORACLE_TABLE이 .env 파일에 설정되지 않았습니다.")

        duckdb = DuckDBSource(config)

        # 🆕 Initialize QueryService for UI-independent data access
        query_service = QueryService(duckdb)
        app_logger.info("QueryService initialized")
        
    except Exception as e:
        app_logger.error(f"설정 로드 실패: {e}")
        ui_adapter.presenter.show_message(MessageContext(
            level='error',
            message=f"설정을 로드할 수 없습니다: {e}"
        ))
        return
    
    # Sidebar 메뉴 구성을 바꾸려면 여길 고쳐야 함. jwlee
    st.sidebar.header("동기화 설정")
    
    # Display current configuration from .env
    st.sidebar.info(f"📋 설정된 테이블: {config.sync_oracle_table}")
    
    # Use .env configuration
    table_name = config.oracle_full_table_name
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
    
    # Always check for progress updates (including completion/error messages)
    # This ensures we detect when a background sync completes
    check_progress()
    
    # Auto-refresh UI during sync to show real-time progress
    if st.session_state.sync_status == 'running':
        time.sleep(SYNC_PROGRESS_REFRESH_INTERVAL)
        st.rerun()
    
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
        
    # Determine default table name
    # Use QueryService instead of query_core functions
    table_list = query_service.get_available_tables()

    # 🆕 Display table list using UI adapter
    show_table_list(table_list, ui_adapter)

    # Determine default table name
    default_table = query_service.determine_default_table_name(config, table_list)    
    
    duckdb_table_name = st.text_input("조회할 테이블명", value=default_table, help="DuckDB 테이블명 (소문자, 스키마 없이)")

    # Query DuckDB table with caching for type conversion
    row_count = query_service.get_table_row_count(duckdb_table_name)

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
            # 🆕 Use QueryService instead of direct data layer access
            with st.spinner(f"집계 데이터 조회 중... (해상도: {resolution})"):
                agg_result = query_service.query_table_aggregated_legacy(
                    table_name=duckdb_table_name,
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
                    'numeric_cols': agg_result.get('numeric_cols', []),
                    'row_count': row_count
                }
                ui_adapter.presenter.show_message(MessageContext(
                    level='success',
                    message=f"✅ 집계 완료: {len(agg_result['df_aggregated'])} 시간 구간"
                ))
            else:
                ui_adapter.presenter.show_message(MessageContext(
                    level='error',
                    message=f"집계 쿼리 오류: {agg_result['error']}"
                ))
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
                duckdb_query_result['row_count'] = row_count
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
            ui_adapter.presenter.show_message(MessageContext(
                level='info',
                message=f"📊 집계 뷰 표시 중 (해상도: {interval}, 총 {len(df_converted)} 시간 구간)"
            ))
        else:
            ui_adapter.presenter.show_message(MessageContext(
                level='info',
                message=f"📊 상세 뷰 표시 중 (총 {len(df_converted):,}행)"
            ))

        # Render visualization
        base_numeric_cols = None
        if query_mode == 'aggregated':
            base_numeric_cols = st.session_state.query_result.get('numeric_cols')
        render_data_visualization(
            df_converted,
            visualization_table_name,
            query_mode=query_mode,
            base_numeric_cols=base_numeric_cols
        )

    st.subheader("데이터 조회")

    if st.session_state.query_result and st.session_state.query_result.get('success'):
        query_result = st.session_state.query_result
        df_converted = query_result.get('df_converted')
        query_mode = query_result.get('query_mode', 'detailed')
        table_name_for_grid = query_result.get('table_name')
        total_rows = query_result.get('row_count')
        if total_rows is None and table_name_for_grid:
            total_rows = get_table_row_count(duckdb, table_name_for_grid)
        if total_rows is None and df_converted is not None:
            total_rows = len(df_converted)

        if df_converted is not None or query_mode == 'aggregated':
            # Display row count
            if total_rows is not None:
                ui_adapter.presenter.show_message(MessageContext(
                    level='info',
                    message=f"📊 총 {total_rows:,}행 조회됨"
                ))

            # Limit displayed rows to prevent MessageSizeError
            max_display_rows = st.number_input(
                "표시할 최대 행 수",
                min_value=100,
                max_value=1000,
                value=100,
                step=100,
                help="브라우저 성능을 위해 표시되는 행 수를 제한합니다."
            )

            grid_df = None
            if query_mode == 'aggregated' and table_name_for_grid:
                # Use QueryService for raw data fetch
                raw_result = query_service.query_table(
                    table_name_for_grid,
                    limit=max_display_rows,
                    convert_types=True
                )
                
                if raw_result.success:
                    grid_df = raw_result.data
                else:
                    ui_adapter.presenter.show_message(MessageContext(
                        level='error',
                        message=f"원본 데이터 조회 오류: {raw_result.error or 'Unknown error'}"
                    ))
            else:
                grid_df = df_converted

            if grid_df is not None:
                display_rows = min(total_rows, max_display_rows) if total_rows is not None else min(len(grid_df), max_display_rows)

                # Show data with row limit - add spinner to prevent UI blocking
                with st.spinner(f"데이터 테이블 렌더링 중... ({display_rows:,}행)"):
                    if total_rows is not None and total_rows > max_display_rows:
                        ui_adapter.presenter.show_message(MessageContext(
                            level='warning',
                            message=f"⚠️ 성능을 위해 {max_display_rows:,}행만 표시합니다. (전체: {total_rows:,}행)"
                        ))
                        st.dataframe(grid_df.head(max_display_rows))
                    else:
                        st.dataframe(grid_df)

if __name__ == "__main__":
    main()
