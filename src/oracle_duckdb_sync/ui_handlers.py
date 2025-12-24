"""
Streamlit UI 이벤트 핸들러 모듈

이 모듈은 Streamlit 앱의 버튼 클릭 등 UI 이벤트 처리 로직을 담당합니다.
app.py의 복잡도를 줄이고 코드 재사용성을 높이기 위해 분리되었습니다.
"""

import streamlit as st
import traceback
from oracle_duckdb_sync.sync_worker import SyncWorker
from oracle_duckdb_sync.sync_state import SyncLock
from oracle_duckdb_sync.logger import setup_logger

# Set up logger
handler_logger = setup_logger('UIHandlers')


def handle_test_sync(config, test_row_limit: int, table_name: str):
    """
    테스트 동기화 버튼 클릭 이벤트 처리
    
    Args:
        config: 애플리케이션 설정 객체
        test_row_limit: 테스트로 가져올 최대 행 수
        table_name: Oracle 테이블명
    """
    handler_logger.info(f"Test sync initiated for table: {table_name}, limit: {test_row_limit}")
    
    if not table_name:
        st.sidebar.warning("테이블명을 입력하세요. .env 파일의 SYNC_ORACLE_TABLE을 설정하거나 '수동 설정 사용'을 체크하세요.")
        return
    
    # Check if another sync is running
    sync_lock = SyncLock()
    if sync_lock.is_locked():
        lock_info = sync_lock.get_lock_info()
        st.sidebar.warning(f"⚠️ 다른 동기화 작업이 실행 중입니다. (PID: {lock_info.get('pid', 'unknown')})")
        return
    
    # Acquire lock
    if sync_lock.acquire(timeout=1):
        try:
            # Prepare sync parameters
            sync_params = {
                'sync_type': 'test',
                'row_limit': test_row_limit
            }
            
            # Create and start worker
            worker = SyncWorker(config, sync_params, st.session_state.progress_queue)
            worker.expected_rows = test_row_limit  # For ETA calculation
            worker.start()
            
            st.session_state.sync_worker = worker
            st.session_state.sync_status = 'running'
            st.session_state.sync_progress = {}
            st.session_state.sync_lock = sync_lock
            
            handler_logger.info("Test sync worker started successfully")
            st.rerun()
            
        except Exception as e:
            handler_logger.error(f"Failed to start test sync: {e}")
            sync_lock.release()
            st.sidebar.error(f"❌ 동기화 시작 실패: {e}")
            with st.sidebar.expander("상세 에러 정보"):
                st.code(traceback.format_exc())
    else:
        st.sidebar.error("❌ 동기화 잠금을 획득할 수 없습니다.")


def handle_full_sync(config, table_name: str, primary_key: str, time_column: str, duckdb):
    """
    전체 동기화 버튼 클릭 이벤트 처리
    
    Args:
        config: 애플리케이션 설정 객체
        table_name: Oracle 테이블명
        primary_key: 기본 키 컬럼명
        time_column: 시간 컬럼명
        duckdb: DuckDB 연결 객체
    """
    handler_logger.info(f"Full sync initiated for table: {table_name}")
    
    if not table_name:
        st.sidebar.warning("테이블명을 입력하세요. .env 파일의 SYNC_ORACLE_TABLE을 설정하거나 '수동 설정 사용'을 체크하세요.")
        return
    
    # Check if another sync is running
    sync_lock = SyncLock()
    if sync_lock.is_locked():
        lock_info = sync_lock.get_lock_info()
        st.sidebar.warning(f"⚠️ 다른 동기화 작업이 실행 중입니다. (PID: {lock_info.get('pid', 'unknown')})")
        return
    
    # Acquire lock
    if sync_lock.acquire(timeout=1):
        try:
            # Use duckdb table name from config or convert to lowercase
            if config.sync_duckdb_table:
                duckdb_table = config.sync_duckdb_table
            else:
                table_parts = table_name.split('.')
                duckdb_table = table_parts[-1].lower()
            
            # Check if table exists in DuckDB to determine sync type
            if not duckdb.table_exists(duckdb_table):
                # First time sync - perform full sync
                sync_params = {
                    'sync_type': 'full',
                    'oracle_table': table_name,
                    'duckdb_table': duckdb_table,
                    'primary_key': primary_key
                }
                handler_logger.info(f"Performing full sync for new table: {duckdb_table}")
            else:
                # Incremental sync
                from oracle_duckdb_sync.sync_engine import SyncEngine
                sync_engine = SyncEngine(config)
                
                # Load last sync time
                last_sync_time = sync_engine.load_state(table_name)
                if not last_sync_time:
                    last_sync_time = "2020-01-01 00:00:00"
                
                # Get first column from time_column (could be composite)
                time_col = time_column.split(',')[0].strip() if time_column else "TIMESTAMP_COL"
                
                sync_params = {
                    'sync_type': 'incremental',
                    'oracle_table': table_name,
                    'duckdb_table': duckdb_table,
                    'time_column': time_col,
                    'last_value': last_sync_time
                }
                handler_logger.info(f"Performing incremental sync from: {last_sync_time}")
            
            # Create and start worker
            worker = SyncWorker(config, sync_params, st.session_state.progress_queue)
            worker.start()
            
            st.session_state.sync_worker = worker
            st.session_state.sync_status = 'running'
            st.session_state.sync_progress = {}
            st.session_state.sync_lock = sync_lock
            
            handler_logger.info("Full sync worker started successfully")
            st.rerun()
            
        except Exception as e:
            handler_logger.error(f"Failed to start full sync: {e}")
            sync_lock.release()
            st.sidebar.error(f"❌ 동기화 시작 실패: {e}")
            with st.sidebar.expander("상세 에러 정보"):
                st.code(traceback.format_exc())
    else:
        st.sidebar.error("❌ 동기화 잠금을 획득할 수 없습니다.")


def handle_reset_sync():
    """
    동기화 완료 후 리셋 버튼 클릭 이벤트 처리
    """
    handler_logger.info("Resetting sync state")
    st.session_state.sync_status = 'idle'
    st.session_state.sync_worker = None
    st.session_state.sync_progress = {}
    st.session_state.sync_result = {}
    st.rerun()


def handle_retry_sync():
    """
    동기화 실패 후 재시도 버튼 클릭 이벤트 처리
    """
    handler_logger.info("Retrying sync after error")
    st.session_state.sync_status = 'idle'
    st.session_state.sync_worker = None
    st.session_state.sync_error = {}
    st.rerun()


def render_running_status():
    """
    동기화 실행 중 상태 UI 렌더링
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔄 동기화 진행 중")
    
    if st.session_state.sync_progress:
        progress = st.session_state.sync_progress
        
        # Progress bar (if percentage available)
        if progress.get('percentage', 0) > 0:
            st.sidebar.progress(min(progress['percentage'], 1.0))
        
        # Statistics
        col1, col2 = st.sidebar.columns(2)
        col1.metric("처리된 행", f"{progress.get('total_rows', 0):,}")
        col2.metric("처리 속도", f"{progress.get('rows_per_second', 0):.0f} rows/s")
        
        # Elapsed time
        elapsed = progress.get('elapsed_time', 0)
        st.sidebar.text(f"⏱️ 경과 시간: {elapsed:.0f}초")
        
        # ETA
        if progress.get('eta'):
            st.sidebar.text(f"⏰ 예상 완료: {progress['eta']}")
    else:
        st.sidebar.info("동기화 시작 중...")


def render_completed_status():
    """
    동기화 완료 상태 UI 렌더링
    """
    st.sidebar.success("✅ 동기화 완료!")
    if st.session_state.sync_result:
        result = st.session_state.sync_result
        st.sidebar.info(f"총 {result.get('total_rows', 0):,} 행 처리됨")
    
    # Reset button
    if st.sidebar.button("새 동기화 시작"):
        handle_reset_sync()


def render_error_status():
    """
    동기화 에러 상태 UI 렌더링
    """
    st.sidebar.error("❌ 동기화 실패")
    if st.session_state.sync_error:
        error = st.session_state.sync_error
        st.sidebar.text(f"에러: {error.get('exception', 'Unknown error')}")
        
        with st.sidebar.expander("상세 에러 정보"):
            st.code(error.get('traceback', ''))
    
    # Reset button
    if st.sidebar.button("다시 시도"):
        handle_retry_sync()


def render_sync_status_ui():
    """
    현재 동기화 상태에 따라 적절한 UI를 렌더링
    """
    if st.session_state.sync_status == 'running':
        render_running_status()
    elif st.session_state.sync_status == 'completed':
        render_completed_status()
    elif st.session_state.sync_status == 'error':
        render_error_status()
