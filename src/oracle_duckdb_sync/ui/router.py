"""
페이지 라우팅 시스템

역할 기반 페이지 라우팅 및 동적 페이지 로딩을 처리합니다.
"""

import importlib
from typing import Callable, Optional

import streamlit as st

from oracle_duckdb_sync.auth import User
from oracle_duckdb_sync.config import load_config
from oracle_duckdb_sync.log.logger import setup_logger

logger = setup_logger('Router')


class PageRouter:
    """페이지 라우팅 관리 클래스"""

    def __init__(self):
        """라우터 초기화"""
        self.routes: dict[str, tuple[str, str, Optional[str]]] = {}
        self._register_default_routes()

    def _register_default_routes(self):
        """기본 라우트 등록"""
        # 사용자 페이지
        self.register('/dashboard', 'oracle_duckdb_sync.ui.pages.user.dashboard', 'render_dashboard')
        self.register('/data', 'oracle_duckdb_sync.ui.pages.user.data_view', 'render_data_view')
        self.register('/visualization', 'oracle_duckdb_sync.ui.pages.user.visualization', 'render_visualization')
        self.register('/agent', 'oracle_duckdb_sync.ui.pages.user.agent_chat', 'render_agent_chat')

        # 관리자 페이지
        self.register('/admin/sync', 'oracle_duckdb_sync.ui.pages.admin.sync', 'render_sync_page', 'admin:*')
        self.register(
            '/admin/users', 'oracle_duckdb_sync.ui.pages.admin.users',
            'render_admin_users_page', 'user:read'
        )
        self.register('/admin/menus', 'oracle_duckdb_sync.ui.pages.admin.menus', 'render_admin_menus_page', 'admin:*')
        self.register(
            '/admin/tables', 'oracle_duckdb_sync.ui.pages.admin.tables',
            'render_admin_tables_page', 'admin:*'
        )

    def register(
        self, path: str, module_path: str, function_name: str,
        required_permission: Optional[str] = None
    ):
        """
        라우트 등록

        Args:
            path: URL 경로 (예: '/dashboard')
            module_path: 모듈 경로 (예: 'oracle_duckdb_sync.ui.pages.user.dashboard')
            function_name: 렌더링 함수 이름 (예: 'render_dashboard')
            required_permission: 필요한 권한 (선택)
        """
        self.routes[path] = (module_path, function_name, required_permission)
        logger.debug(f"Route registered: {path} -> {module_path}.{function_name}")

    def navigate(self, path: str, user: Optional[User] = None) -> bool:
        """
        페이지 탐색 및 렌더링

        Args:
            path: 이동할 경로
            user: 현재 사용자 (권한 체크용)

        Returns:
            성공 여부
        """
        if path not in self.routes:
            st.error(f"❌ 페이지를 찾을 수 없습니다: {path}")
            logger.warning(f"Route not found: {path}")
            return False

        module_path, function_name, required_permission = self.routes[path]

        # 권한 체크
        if required_permission and user:
            from oracle_duckdb_sync.auth import AuthService

            config = load_config()
            auth_service = AuthService(config=config)

            if not auth_service.has_permission(user, required_permission):
                st.error("❌ 이 페이지에 접근할 권한이 없습니다.")
                logger.warning(f"Permission denied: {user.username} tried to access {path}")
                return False

        # 페이지 렌더링
        try:
            module = importlib.import_module(module_path)
            render_function: Callable = getattr(module, function_name)
            render_function()
            return True
        except ModuleNotFoundError as e:
            st.error(f"❌ 페이지 모듈을 찾을 수 없습니다: {module_path}")
            logger.error(f"Module not found: {module_path} - {e}")
            return False
        except AttributeError as e:
            st.error(f"❌ 렌더링 함수를 찾을 수 없습니다: {function_name}")
            logger.error(f"Function not found: {function_name} in {module_path} - {e}")
            return False
        except Exception as e:
            st.error(f"❌ 페이지 렌더링 중 오류가 발생했습니다: {str(e)}")
            logger.error(f"Error rendering page {path}: {e}", exc_info=True)
            return False

    def get_routes(self) -> dict[str, tuple[str, str, Optional[str]]]:
        """
        등록된 모든 라우트 반환

        Returns:
            라우트 딕셔너리
        """
        return self.routes.copy()


# 전역 라우터 인스턴스
_router: Optional[PageRouter] = None


def get_router() -> PageRouter:
    """
    전역 라우터 인스턴스 반환

    Returns:
        PageRouter 인스턴스
    """
    global _router
    if _router is None:
        _router = PageRouter()
    return _router
