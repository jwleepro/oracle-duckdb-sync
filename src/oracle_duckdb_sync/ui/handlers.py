"""
Streamlit UI 이벤트 핸들러 모듈

이 모듈은 Streamlit 앱의 버튼 클릭 등 UI 이벤트 처리 로직을 담당합니다.
app.py의 복잡도를 줄이고 코드 재사용성을 높이기 위해 분리되었습니다.
"""

import os
import streamlit as st
import traceback
from oracle_duckdb_sync.scheduler.sync_worker import SyncWorker
from oracle_duckdb_sync.state.sync_state import SyncLock
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.adapters.streamlit_adapter import StreamlitAdapter
from oracle_duckdb_sync.application.ui_presenter import MessageContext

# Set up logger
handler_logger = setup_logger('UIHandlers')


# ============================================================================
# Helper Functions for DRY (Don't Repeat Yourself)
# ============================================================================

def _validate_table_name(table_name: str, ui_adapter: StreamlitAdapter = None) -> bool:
    """
    테이블명 검증 헬퍼 함수

    Args:
        table_name: 검증할 테이블명
        ui_adapter: UI 어댑터 (옵션)

    Returns:
        bool: 유효하면 True, 그렇지 않으면 False
    """
    if not table_name:
        handler_logger.warning("Table name validation failed: No table name provided")
        if ui_adapter:
            with ui_adapter.layout.create_sidebar():
                ui_adapter.presenter.show_message(MessageContext(
                    level='warning',
                    message="테이블명을 입력하세요. .env 파일의 SYNC_ORACLE_TABLE을 설정하거나 '수동 설정 사용'을 체크하세요."
                ))
        else:
            st.sidebar.warning("테이블명을 입력하세요. .env 파일의 SYNC_ORACLE_TABLE을 설정하거나 '수동 설정 사용'을 체크하세요.")
        return False
    handler_logger.info(f"Table name validated: {table_name}")
    return True


def _acquire_sync_lock_with_ui(sync_lock: SyncLock):
    """
    UI 에러 메시지를 포함한 중앙화된 락 획득

    Args:
        sync_lock: 동기화 락 객체

    Returns:
        SyncLock: 락 획득 성공 시 sync_lock 객체, 실패 시 None
    """
    if sync_lock.is_locked():
        lock_info = sync_lock.get_lock_info()
        handler_logger.warning(
            f"Sync blocked: Another sync operation is running "
            f"(PID: {lock_info.get('pid', 'unknown')}, "
            f"Hostname: {lock_info.get('hostname', 'unknown')}, "
            f"Started: {lock_info.get('timestamp', 'unknown')})"
        )
        st.sidebar.warning(f"⚠️ 다른 동기화 작업이 실행 중입니다. (PID: {lock_info.get('pid', 'unknown')})")
        return None

    if not sync_lock.acquire(timeout=1):
        handler_logger.error("Failed to acquire sync lock after 1 second timeout")
        st.sidebar.error("❌ 동기화 잠금을 획득할 수 없습니다.")
        return None

    handler_logger.info(f"Sync lock acquired successfully (PID: {os.getpid()})")
    return sync_lock


def _start_sync_worker(config, sync_params: dict, sync_lock: SyncLock):
    """
    동기화 워커 생성 및 시작
    
    Args:
        config: 애플리케이션 설정 객체
        sync_params: 동기화 파라미터 딕셔너리
        sync_lock: 획득된 동기화 락 객체
    """
    # Create and start worker
    worker = SyncWorker(config, sync_params, st.session_state.progress_queue)
    
    # Set expected_rows for test sync (for ETA calculation)
    if sync_params.get('sync_type') == 'test' and 'row_limit' in sync_params:
        worker.expected_rows = sync_params['row_limit']
    
    worker.start()
    
    # Update session state
    st.session_state.sync_worker = worker
    st.session_state.sync_status = 'running'
    st.session_state.sync_progress = {}
    st.session_state.sync_lock = sync_lock
    
    handler_logger.info(f"{sync_params.get('sync_type', 'unknown')} sync worker started successfully")
    st.rerun()


def _handle_sync_error(sync_lock: SyncLock, exception: Exception):
    """
    동기화 시작 실패 시 에러 처리
    
    Args:
        sync_lock: 해제할 동기화 락 객체
        exception: 발생한 예외
    """
    handler_logger.error(f"Failed to start sync: {exception}")
    sync_lock.release()
    st.sidebar.error(f"❌ 동기화 시작 실패: {exception}")
    with st.sidebar.expander("상세 에러 정보"):
        st.code(traceback.format_exc())


# ============================================================================
# Main Event Handlers
# ============================================================================


def handle_test_sync(config, test_row_limit: int, table_name: str):
    """
    테스트 동기화 버튼 클릭 이벤트 처리
    
    Args:
        config: 애플리케이션 설정 객체
        test_row_limit: 테스트로 가져올 최대 행 수
        table_name: Oracle 테이블명
    """
    handler_logger.info(f"Test sync initiated for table: {table_name}, limit: {test_row_limit}")
    
    # Validate table name
    if not _validate_table_name(table_name):
        return
    
    # Acquire sync lock with UI feedback
    sync_lock = SyncLock()
    acquired_lock = _acquire_sync_lock_with_ui(sync_lock)
    if not acquired_lock:
        return
    
    try:
        # Prepare sync parameters
        sync_params = {
            'sync_type': 'test',
            'row_limit': test_row_limit
        }
        
        # Start sync worker
        _start_sync_worker(config, sync_params, sync_lock)
        
    except Exception as e:
        _handle_sync_error(sync_lock, e)


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
    
    # Validate table name
    if not _validate_table_name(table_name):
        return
    
    # Acquire sync lock with UI feedback
    sync_lock = SyncLock()
    acquired_lock = _acquire_sync_lock_with_ui(sync_lock)
    if not acquired_lock:
        return
    
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
            
            # time_column is already parsed by config.duckdb_time_column
            sync_params = {
                'sync_type': 'incremental',
                'oracle_table': table_name,
                'duckdb_table': duckdb_table,
                'time_column': time_column,  # Already parsed, no need to split
                'last_value': last_sync_time,
                'primary_key': primary_key  # Add primary_key for UPSERT
            }
            handler_logger.info(f"Performing incremental sync from: {last_sync_time}")
        
        # Start sync worker
        _start_sync_worker(config, sync_params, sync_lock)
        
    except Exception as e:
        _handle_sync_error(sync_lock, e)


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
    
    # Manual refresh button for progress updates
    if st.sidebar.button("🔄 진행 상황 새로고침", key="refresh_progress"):
        st.rerun()


def render_completed_status():
    """
    동기화 완료 상태 UI 렌더링
    """
    if st.session_state.sync_result:
        result = st.session_state.sync_result
        handler_logger.info(f"Sync completed successfully: {result.get('total_rows', 0)} rows processed")
    else:
        handler_logger.info("Sync completed successfully")

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
    if st.session_state.sync_error:
        error = st.session_state.sync_error
        handler_logger.error(f"Sync error displayed to user: {error.get('exception', 'Unknown error')}")

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
