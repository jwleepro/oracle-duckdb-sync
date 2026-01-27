"""
동기화 관리 페이지

Oracle에서 DuckDB로 데이터 동기화를 관리합니다.
"""

import time

import streamlit as st

from oracle_duckdb_sync.config import load_config
from oracle_duckdb_sync.database import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.ui.handlers import (
    handle_full_sync,
    handle_test_sync,
    render_sync_status_ui,
)
from oracle_duckdb_sync.ui.pages.login import require_auth
from oracle_duckdb_sync.ui.session_state import SYNC_PROGRESS_REFRESH_INTERVAL

logger = setup_logger('SyncPage')


def check_progress():
    """동기화 진행 상황 체크 (app.py에서 복사)"""
    from oracle_duckdb_sync.ui.app import check_progress as app_check_progress
    app_check_progress()


@require_auth(required_permission="admin:*")
def render_sync_page():
    """동기화 관리 페이지 렌더링"""
    st.title("🔄 동기화 관리")

    try:
        config = load_config()

        if not config.sync_oracle_table:
            st.error("❌ SYNC_ORACLE_TABLE이 .env 파일에 설정되지 않았습니다.")
            return

        duckdb = DuckDBSource(config)

        # 현재 설정 표시
        render_sync_configuration(config)

        st.markdown("---")

        # 동기화 컨트롤
        render_sync_controls(config, duckdb)

        st.markdown("---")

        # 동기화 상태 표시
        render_sync_status()

    except Exception as e:
        logger.error(f"동기화 관리 페이지 렌더링 실패: {e}", exc_info=True)
        st.error(f"❌ 페이지를 로드할 수 없습니다: {e}")


def render_sync_configuration(config):
    """현재 동기화 설정 표시"""
    st.subheader("⚙️ 현재 설정")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📋 소스 테이블", config.sync_oracle_table)

    with col2:
        st.metric("🔑 Primary Key", config.sync_primary_key)

    with col3:
        st.metric("🕐 Time Column", config.duckdb_time_column)

    # 추가 설정 정보
    with st.expander("📝 상세 설정"):
        st.code(f"""
Oracle 연결: {config.oracle_host}:{config.oracle_port}/{config.oracle_service_name}
Oracle 사용자: {config.oracle_user}
Oracle 전체 테이블명: {config.oracle_full_table_name}

DuckDB 경로: {config.duckdb_path}
DuckDB 테이블명: {config.duckdb_table_name}
        """)


def render_sync_controls(config, duckdb: DuckDBSource):
    """동기화 컨트롤 UI"""
    st.subheader("🎮 동기화 실행")

    # 진행 상황 체크
    check_progress()

    # Auto-refresh during sync
    if st.session_state.sync_status == 'running':
        time.sleep(SYNC_PROGRESS_REFRESH_INTERVAL)
        st.rerun()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 🧪 테스트 동기화")
        st.caption("제한된 행 수로 동기화를 테스트합니다.")

        test_row_limit = st.number_input(
            "테스트 행 수",
            min_value=10000,
            max_value=100000,
            value=100000,
            step=10000,
            help="테스트로 가져올 최대 행 수 (기본: 10만)"
        )

        if st.button(
            "🧪 테스트 동기화 실행",
            disabled=(st.session_state.sync_status == 'running'),
            use_container_width=True,
            type="primary"
        ):
            table_name = config.oracle_full_table_name
            handle_test_sync(config, test_row_limit, table_name)
            st.rerun()

    with col2:
        st.markdown("##### 🚀 전체 동기화")
        st.caption("모든 데이터를 동기화합니다.")

        st.info(f"📊 현재 DuckDB 행 수: {get_duckdb_row_count(duckdb, config):,}행")

        if st.button(
            "🚀 전체 동기화 실행",
            disabled=(st.session_state.sync_status == 'running'),
            use_container_width=True,
            type="primary"
        ):
            table_name = config.oracle_full_table_name
            primary_key = config.sync_primary_key
            time_column = config.duckdb_time_column
            handle_full_sync(config, table_name, primary_key, time_column, duckdb)
            st.rerun()


def render_sync_status():
    """동기화 상태 표시"""
    st.subheader("📊 동기화 상태")

    # 현재 상태
    sync_status = st.session_state.get('sync_status', 'idle')

    col1, col2, col3 = st.columns(3)

    with col1:
        status_emoji = "🟢" if sync_status == 'idle' else "🔄" if sync_status == 'running' else "🔴"
        status_text = "대기 중" if sync_status == 'idle' else "진행 중" if sync_status == 'running' else "오류"
        st.metric(f"{status_emoji} 상태", status_text)

    with col2:
        if st.session_state.get('sync_progress'):
            progress = st.session_state.sync_progress
            rows_synced = progress.get('rows_synced', 0)
            st.metric("📝 동기화된 행", f"{rows_synced:,}")

    with col3:
        if st.session_state.get('sync_result'):
            result = st.session_state.sync_result
            if result.get('duration'):
                st.metric("⏱️ 소요 시간", f"{result['duration']:.2f}초")

    # 상세 상태 표시
    render_sync_status_ui()


def get_duckdb_row_count(duckdb: DuckDBSource, config) -> int:
    """DuckDB 테이블 행 수 조회"""
    try:
        from oracle_duckdb_sync.application import QueryService
        query_service = QueryService(duckdb)
        return query_service.get_table_row_count(config.duckdb_table_name)
    except Exception as e:
        logger.error(f"DuckDB 행 수 조회 실패: {e}")
        return 0


if __name__ == "__main__":
    render_sync_page()
