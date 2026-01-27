"""
대시보드 페이지

시스템 상태 요약 및 빠른 액션을 제공합니다.
"""

import streamlit as st

from oracle_duckdb_sync.config import load_config, load_config
from oracle_duckdb_sync.database import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.ui.pages.login import require_auth

logger = setup_logger('DashboardPage')


@require_auth()
def render_dashboard():
    """대시보드 페이지 렌더링"""
    st.title("🏠 대시보드")

    try:
        config = load_config()

        if not config.sync_oracle_table:
            st.error("❌ SYNC_ORACLE_TABLE이 .env 파일에 설정되지 않았습니다.")
            return

        duckdb = DuckDBSource(config)

        # 시스템 상태 요약
        render_system_status(config, duckdb)

        st.markdown("---")

        # 빠른 액션
        render_quick_actions()

    except Exception as e:
        logger.error(f"대시보드 렌더링 실패: {e}", exc_info=True)
        st.error(f"❌ 대시보드를 로드할 수 없습니다: {e}")


def render_system_status(config: Config, duckdb: DuckDBSource):
    """시스템 상태 표시"""
    st.subheader("📊 시스템 상태")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("설정된 테이블", config.sync_oracle_table)

    with col2:
        # 동기화 상태
        sync_status = st.session_state.get('sync_status', 'idle')
        status_emoji = "🟢" if sync_status == 'idle' else "🔄"
        status_text = "대기 중" if sync_status == 'idle' else "진행 중"
        st.metric(f"{status_emoji} 동기화 상태", status_text)

    with col3:
        # 테이블 수
        try:
            tables = duckdb.list_tables()
            st.metric("📋 테이블 수", len(tables))
        except Exception as e:
            logger.error(f"테이블 수 조회 실패: {e}")
            st.metric("📋 테이블 수", "N/A")

    # 최근 동기화 결과
    if st.session_state.get('sync_result'):
        result = st.session_state.sync_result
        with st.expander("📝 최근 동기화 결과", expanded=True):
            if result.get('success'):
                st.success(f"✅ 동기화 완료: {result.get('rows_synced', 0):,}행")
                if result.get('duration'):
                    st.info(f"⏱️ 소요 시간: {result['duration']:.2f}초")
            else:
                st.error(f"❌ 동기화 실패: {result.get('error', 'Unknown error')}")


def render_quick_actions():
    """빠른 액션 버튼"""
    st.subheader("⚡ 빠른 액션")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📊 데이터 조회", use_container_width=True):
            st.session_state.current_page = '/data'
            st.rerun()

    with col2:
        if st.button("📈 시각화", use_container_width=True):
            st.session_state.current_page = '/visualization'
            st.rerun()

    with col3:
        if st.button("🤖 AI 에이전트", use_container_width=True):
            st.session_state.current_page = '/agent'
            st.rerun()

    with col4:
        user = st.session_state.get('user')
        if user and user.role.value == 'ADMIN':
            if st.button("🔄 동기화 관리", use_container_width=True):
                st.session_state.current_page = '/admin/sync'
                st.rerun()


if __name__ == "__main__":
    render_dashboard()
