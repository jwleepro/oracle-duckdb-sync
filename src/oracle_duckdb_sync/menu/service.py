"""
메뉴 서비스

권한 기반 메뉴 필터링 및 관리 로직을 담당합니다.
"""

from typing import List, Optional

from oracle_duckdb_sync.auth.models import User
from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.menu.models import DEFAULT_MENUS, Menu
from oracle_duckdb_sync.menu.repository import MenuRepository


class MenuService:
    """
    메뉴 서비스

    사용자 권한에 따른 메뉴 필터링과 메뉴 관리를 담당합니다.
    """

    def __init__(self, config: Config = None, duckdb_source: DuckDBSource = None):
        """
        Args:
            config: 애플리케이션 설정
            duckdb_source: DuckDB 소스 객체
        """
        self.logger = setup_logger('MenuService')
        self.menu_repo = MenuRepository(config=config, duckdb_source=duckdb_source)

    def get_menus_for_user(self, user: User) -> List[Menu]:
        """
        사용자 권한에 맞는 메뉴 조회

        Args:
            user: 사용자 객체

        Returns:
            접근 가능한 Menu 리스트
        """
        # 모든 활성 메뉴 조회
        all_menus = self.menu_repo.get_all(include_inactive=False)

        # 권한 필터링
        accessible_menus = []
        for menu in all_menus:
            if self._can_access_menu(user, menu):
                accessible_menus.append(menu)

        self.logger.debug(f"User {user.username} has access to {len(accessible_menus)} menus")
        return accessible_menus

    def get_top_level_menus_for_user(self, user: User) -> List[Menu]:
        """
        사용자 권한에 맞는 최상위 메뉴만 조회

        Args:
            user: 사용자 객체

        Returns:
            접근 가능한 최상위 Menu 리스트
        """
        top_menus = self.menu_repo.get_top_level_menus(include_inactive=False)

        accessible_menus = []
        for menu in top_menus:
            if self._can_access_menu(user, menu):
                accessible_menus.append(menu)

        return accessible_menus

    def get_menu_tree_for_user(self, user: User) -> List[dict]:
        """
        사용자 권한에 맞는 메뉴 트리 구조 생성

        Args:
            user: 사용자 객체

        Returns:
            계층 구조의 메뉴 트리 (딕셔너리 리스트)
        """
        # 최상위 메뉴 조회
        top_menus = self.get_top_level_menus_for_user(user)

        # 각 최상위 메뉴에 대해 하위 메뉴 추가
        menu_tree = []
        for menu in top_menus:
            menu_dict = menu.to_dict()
            menu_dict['children'] = self._get_accessible_children(user, menu.id)
            menu_tree.append(menu_dict)

        return menu_tree

    def _get_accessible_children(self, user: User, parent_id: int) -> List[dict]:
        """
        사용자가 접근 가능한 하위 메뉴 조회 (재귀)

        Args:
            user: 사용자 객체
            parent_id: 상위 메뉴 ID

        Returns:
            접근 가능한 하위 메뉴 리스트
        """
        children = self.menu_repo.get_children(parent_id, include_inactive=False)

        accessible_children = []
        for child in children:
            if self._can_access_menu(user, child):
                child_dict = child.to_dict()
                # 재귀적으로 하위 메뉴 조회
                child_dict['children'] = self._get_accessible_children(user, child.id)
                accessible_children.append(child_dict)

        return accessible_children

    def _can_access_menu(self, user: User, menu: Menu) -> bool:
        """
        사용자가 메뉴에 접근 가능한지 확인

        Args:
            user: 사용자 객체
            menu: 메뉴 객체

        Returns:
            접근 가능 여부
        """
        # 권한이 필요하지 않은 메뉴는 누구나 접근 가능
        if not menu.requires_permission():
            return True

        # 관리자는 모든 메뉴 접근 가능
        if user.is_admin():
            return True

        # TODO: AuthService를 통한 세밀한 권한 체크
        # 현재는 간단한 역할 기반 체크
        from oracle_duckdb_sync.auth.models import DEFAULT_ROLE_PERMISSIONS

        role_permissions = DEFAULT_ROLE_PERMISSIONS.get(user.role, [])

        # admin:* 권한이 있으면 모든 메뉴 접근 가능
        if 'admin:*' in role_permissions:
            return True

        # 필요한 권한이 있는지 확인
        return menu.required_permission in role_permissions

    def create_menu(self, menu: Menu) -> Menu:
        """메뉴 생성"""
        return self.menu_repo.create(menu)

    def update_menu(self, menu: Menu) -> Menu:
        """메뉴 업데이트"""
        return self.menu_repo.update(menu)

    def delete_menu(self, menu_id: int) -> bool:
        """메뉴 삭제"""
        return self.menu_repo.delete(menu_id)

    def get_menu_by_id(self, menu_id: int) -> Optional[Menu]:
        """ID로 메뉴 조회"""
        return self.menu_repo.get_by_id(menu_id)

    def get_menu_by_path(self, path: str) -> Optional[Menu]:
        """경로로 메뉴 조회"""
        return self.menu_repo.get_by_path(path)

    def get_all_menus(self, include_inactive: bool = False) -> List[Menu]:
        """모든 메뉴 조회"""
        return self.menu_repo.get_all(include_inactive=include_inactive)

    def initialize_default_menus(self) -> int:
        """
        기본 메뉴 초기화

        Returns:
            생성된 메뉴 수
        """
        created_count = 0

        # 기본 메뉴를 순회하면서 생성
        admin_menu_id = None

        for menu in DEFAULT_MENUS:
            # 이미 존재하는 메뉴는 건너뛰기
            existing = self.menu_repo.get_by_path(menu.path)
            if existing:
                # 관리자 메뉴 ID 저장 (하위 메뉴 참조용)
                if menu.path == "/admin":
                    admin_menu_id = existing.id
                continue

            # 관리자 하위 메뉴인 경우 parent_id 설정
            if menu.path.startswith("/admin/") and admin_menu_id:
                menu.parent_id = admin_menu_id

            try:
                created_menu = self.menu_repo.create(menu)
                created_count += 1

                # 관리자 메뉴 ID 저장
                if menu.path == "/admin":
                    admin_menu_id = created_menu.id

                self.logger.info(f"Created default menu: {menu.name}")

            except Exception as e:
                self.logger.error(f"Failed to create default menu {menu.name}: {e}")

        self.logger.info(f"Initialized {created_count} default menus")
        return created_count
