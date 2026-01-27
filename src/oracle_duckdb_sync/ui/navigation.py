"""
네비게이션 컴포넌트

역할 기반 사이드바 메뉴를 렌더링합니다.
"""

from typing import List, Optional

import streamlit as st

from oracle_duckdb_sync.auth import AuthService, User
from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.menu import Menu, MenuService
from oracle_duckdb_sync.ui.components import (
    render_search_box,
    render_favorites_section,
    render_recent_pages_section,
    render_shortcuts_help,
    initialize_shortcuts,
    add_recent_page,
    get_page_title
)

logger = setup_logger('Navigation')


class NavigationMenu:
    """네비게이션 메뉴 관리 클래스"""

    def __init__(self, user: User, auth_service: AuthService, menu_service: MenuService):
        """
        네비게이션 메뉴 초기화

        Args:
            user: 현재 로그인한 사용자
            auth_service: 인증 서비스
            menu_service: 메뉴 서비스
        """
        self.user = user
        self.auth_service = auth_service
        self.menu_service = menu_service

    def render(self):
        """사이드바 네비게이션 렌더링"""
        st.sidebar.header("🧭 Navigation")

        # 사용자 정보 표시
        self._render_user_info()

        st.sidebar.markdown("---")

        # 메뉴 검색
        render_search_box(self.user)

        st.sidebar.markdown("---")

        # 사용자 메뉴
        self._render_user_menus()

        # 관리자 메뉴 (ADMIN 역할만)
        if self.user.role.value == 'ADMIN':
            st.sidebar.markdown("---")
            self._render_admin_menus()

        # 즐겨찾기 및 최근 방문 페이지
        render_favorites_section()
        render_recent_pages_section()

        # 키보드 단축키 도움말
        render_shortcuts_help()

        st.sidebar.markdown("---")

        # 로그아웃 버튼
        if st.sidebar.button("🚪 로그아웃", use_container_width=True):
            self._handle_logout()

    def _render_user_info(self):
        """사용자 정보 표시"""
        st.sidebar.markdown(f"**👤 {self.user.username}**")
        st.sidebar.caption(f"역할: {self.user.role.value}")

    def _render_user_menus(self):
        """사용자 메뉴 렌더링"""
        # 확장/축소 상태
        if 'menu_expanded' not in st.session_state:
            st.session_state.menu_expanded = {'user': True, 'admin': False}

        with st.sidebar.expander("📱 사용자 메뉴", expanded=st.session_state.menu_expanded['user']):
            self._render_menu_items([
                {'icon': '🏠', 'name': '대시보드', 'path': '/dashboard'},
                {'icon': '📊', 'name': '데이터 조회', 'path': '/data'},
                {'icon': '📈', 'name': '시각화', 'path': '/visualization'},
                {'icon': '🤖', 'name': 'AI 에이전트', 'path': '/agent'},
            ])

    def _render_admin_menus(self):
        """관리자 메뉴 렌더링"""
        with st.sidebar.expander("⚙️ 관리자 메뉴", expanded=st.session_state.menu_expanded['admin']):
            self._render_menu_items([
                {'icon': '🔄', 'name': '동기화 관리', 'path': '/admin/sync'},
                {'icon': '👥', 'name': '사용자 관리', 'path': '/admin/users'},
                {'icon': '📑', 'name': '메뉴 관리', 'path': '/admin/menus'},
                {'icon': '🗄️', 'name': '테이블 설정', 'path': '/admin/tables'},
            ])

    def _render_menu_items(self, menus: List[dict]):
        """
        메뉴 항목 렌더링

        Args:
            menus: 메뉴 항목 리스트
        """
        current_page = st.session_state.get('current_page', '/dashboard')

        for menu in menus:
            icon = menu['icon']
            name = menu['name']
            path = menu['path']

            # 현재 페이지 하이라이트
            button_type = "primary" if current_page == path else "secondary"

            if st.button(f"{icon} {name}", key=f"nav_{path}", use_container_width=True, type=button_type):
                st.session_state.current_page = path
                # 최근 방문 페이지에 추가
                add_recent_page(path, name)
                logger.info(f"User {self.user.username} navigated to {path}")
                st.rerun()

    def _handle_logout(self):
        """로그아웃 처리"""
        logger.info(f"User logged out: {self.user.username}")

        # 세션 상태 초기화
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.current_page = '/dashboard'

        st.success("로그아웃되었습니다.")
        st.rerun()


def render_sidebar_navigation(user: User):
    """
    사이드바 네비게이션 렌더링

    Args:
        user: 현재 로그인한 사용자
    """
    config = Config()
    auth_service = AuthService(config=config)
    menu_service = MenuService(config=config)

    nav = NavigationMenu(user, auth_service, menu_service)
    nav.render()
