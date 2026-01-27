"""
Oracle-DuckDB Sync Dashboard - Main Entry Point

역할 기반 메뉴와 라우팅을 지원하는 메인 애플리케이션입니다.
"""

import streamlit as st

from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.ui.navigation import render_sidebar_navigation
from oracle_duckdb_sync.ui.pages.login import render_login_page
from oracle_duckdb_sync.ui.router import get_router
from oracle_duckdb_sync.ui.session_state import initialize_session_state
from oracle_duckdb_sync.ui.components import (
    render_breadcrumb,
    initialize_shortcuts,
    render_favorite_button,
    get_page_title,
    add_recent_page
)

# Logger 설정
app_logger = setup_logger('MainApp')


def main():
    """메인 애플리케이션"""
    # 페이지 설정
    st.set_page_config(
        page_title="Oracle-DuckDB Sync Dashboard",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 세션 상태 초기화
    initialize_session_state()

    # 로그인 체크
    if not st.session_state.get('authenticated', False):
        render_login_page()
        return

    # 사용자 정보
    user = st.session_state.get('user')
    if not user:
        st.error("❌ 사용자 정보를 찾을 수 없습니다. 다시 로그인하세요.")
        st.session_state.authenticated = False
        st.rerun()
        return

    # 네비게이션 렌더링
    render_sidebar_navigation(user)

    # 현재 페이지
    current_page = st.session_state.get('current_page', '/dashboard')

    # 키보드 단축키 초기화
    initialize_shortcuts(user)

    # 브레드크럼 네비게이션
    render_breadcrumb(current_page)

    # 즐겨찾기 버튼
    col1, col2, col3 = st.columns([6, 2, 2])
    with col3:
        page_title = get_page_title(current_page)
        render_favorite_button(current_page, page_title)

    # 최근 방문 페이지에 추가
    add_recent_page(current_page, page_title)

    # 라우터로 페이지 렌더링
    router = get_router()
    success = router.navigate(current_page, user)

    if not success:
        st.error(f"❌ 페이지를 로드할 수 없습니다: {current_page}")
        app_logger.error(f"Failed to render page: {current_page}")

        # 대시보드로 돌아가기 버튼
        if st.button("🏠 대시보드로 돌아가기"):
            st.session_state.current_page = '/dashboard'
            st.rerun()


if __name__ == "__main__":
    main()
