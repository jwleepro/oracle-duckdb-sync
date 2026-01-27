"""
메뉴 관리 페이지

관리자가 메뉴를 생성, 수정, 삭제하는 페이지입니다.
"""

import streamlit as st

from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.menu import Menu, MenuService
from oracle_duckdb_sync.ui.pages.login import require_auth

# Logger 설정
logger = setup_logger('AdminMenusPage')


@require_auth(required_permission="admin:*")
def render_admin_menus_page():
    """메뉴 관리 페이지 렌더링"""
    st.title("📑 메뉴 관리")

    # 설정 및 서비스 초기화
    config = Config()
    menu_service = MenuService(config=config)

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📋 메뉴 목록", "➕ 메뉴 생성", "🔄 기본 메뉴 초기화"])

    with tab1:
        render_menu_list(menu_service)

    with tab2:
        render_create_menu_form(menu_service)

    with tab3:
        render_initialize_menus(menu_service)


def render_menu_list(menu_service: MenuService):
    """메뉴 목록 렌더링"""
    st.subheader("메뉴 목록")

    # 메뉴 목록 조회
    menus = menu_service.get_all_menus(include_inactive=True)

    if not menus:
        st.info("등록된 메뉴가 없습니다.")
        return

    # 메뉴 목록 표시
    for menu in menus:
        status_icon = '🟢' if menu.is_active else '🔴'
        parent_text = f" (하위: {menu.parent_id})" if menu.has_parent() else ""

        with st.expander(f"{status_icon} {menu.icon} {menu.name}{parent_text}"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**메뉴 ID**: {menu.id}")
                st.markdown(f"**이름**: {menu.name}")
                st.markdown(f"**경로**: `{menu.path}`")
                st.markdown(f"**아이콘**: {menu.icon}")

            with col2:
                st.markdown(f"**상위 메뉴 ID**: {menu.parent_id or '없음 (최상위)'}")
                st.markdown(f"**필요 권한**: {menu.required_permission or '없음'}")
                st.markdown(f"**정렬 순서**: {menu.order}")
                st.markdown(f"**상태**: {'활성' if menu.is_active else '비활성'}")

            # 수정 폼
            st.markdown("---")
            st.markdown("##### 메뉴 수정")

            with st.form(f"edit_menu_{menu.id}"):
                col1, col2 = st.columns(2)

                with col1:
                    new_name = st.text_input("이름", value=menu.name, key=f"edit_name_{menu.id}")
                    new_path = st.text_input("경로", value=menu.path, key=f"edit_path_{menu.id}")
                    new_icon = st.text_input("아이콘", value=menu.icon, key=f"edit_icon_{menu.id}")
                    new_order = st.number_input("정렬 순서", value=menu.order, key=f"edit_order_{menu.id}")

                with col2:
                    new_parent_id = st.number_input(
                        "상위 메뉴 ID (0이면 최상위)",
                        value=menu.parent_id or 0,
                        min_value=0,
                        key=f"edit_parent_{menu.id}"
                    )
                    new_permission = st.text_input(
                        "필요 권한",
                        value=menu.required_permission,
                        key=f"edit_permission_{menu.id}"
                    )
                    new_is_active = st.checkbox(
                        "활성화",
                        value=menu.is_active,
                        key=f"edit_active_{menu.id}"
                    )

                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    update = st.form_submit_button("수정", use_container_width=True)
                with col2:
                    delete = st.form_submit_button("삭제", type="secondary", use_container_width=True)

                if update:
                    handle_update_menu(
                        menu_service,
                        menu.id,
                        new_name,
                        new_path,
                        new_icon,
                        new_parent_id if new_parent_id > 0 else None,
                        new_permission,
                        new_order,
                        new_is_active
                    )

                if delete:
                    handle_delete_menu(menu_service, menu.id, menu.name)


def render_create_menu_form(menu_service: MenuService):
    """메뉴 생성 폼 렌더링"""
    st.subheader("새 메뉴 생성")

    with st.form("create_menu_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("메뉴 이름", placeholder="대시보드")
            path = st.text_input("경로", placeholder="/dashboard")
            icon = st.text_input("아이콘", placeholder="🏠", value="📄")
            order = st.number_input("정렬 순서", value=0, min_value=0)

        with col2:
            parent_id = st.number_input("상위 메뉴 ID (0이면 최상위)", value=0, min_value=0)
            permission = st.text_input("필요 권한", placeholder="sync:read")
            is_active = st.checkbox("활성화", value=True)

        submit = st.form_submit_button("생성", use_container_width=True)

        if submit:
            handle_create_menu(
                menu_service,
                name,
                path,
                icon,
                parent_id if parent_id > 0 else None,
                permission,
                order,
                is_active
            )


def render_initialize_menus(menu_service: MenuService):
    """기본 메뉴 초기화"""
    st.subheader("기본 메뉴 초기화")

    st.info("""
    기본 메뉴를 자동으로 생성합니다:
    - 대시보드
    - 동기화
    - 로그 조회
    - 관리자 메뉴 (사용자 관리, 메뉴 관리, 테이블 설정)

    이미 존재하는 메뉴는 건너뜁니다.
    """)

    if st.button("기본 메뉴 초기화", type="primary", use_container_width=True):
        handle_initialize_menus(menu_service)


def handle_create_menu(
    menu_service: MenuService,
    name: str,
    path: str,
    icon: str,
    parent_id: int,
    permission: str,
    order: int,
    is_active: bool
):
    """메뉴 생성 처리"""
    if not name or not path:
        st.error("메뉴 이름과 경로는 필수입니다.")
        return

    menu = Menu(
        name=name,
        path=path,
        icon=icon,
        parent_id=parent_id,
        required_permission=permission,
        order=order,
        is_active=is_active
    )

    try:
        created_menu = menu_service.create_menu(menu)
        st.success(f"✅ 메뉴 '{created_menu.name}'가 생성되었습니다.")
        logger.info(f"Menu created: {created_menu.name} at {created_menu.path}")
        st.rerun()
    except Exception as e:
        st.error(f"❌ 생성 실패: {str(e)}")
        logger.error(f"Failed to create menu: {e}")


def handle_update_menu(
    menu_service: MenuService,
    menu_id: int,
    name: str,
    path: str,
    icon: str,
    parent_id: int,
    permission: str,
    order: int,
    is_active: bool
):
    """메뉴 수정 처리"""
    if not name or not path:
        st.error("메뉴 이름과 경로는 필수입니다.")
        return

    menu = Menu(
        id=menu_id,
        name=name,
        path=path,
        icon=icon,
        parent_id=parent_id,
        required_permission=permission,
        order=order,
        is_active=is_active
    )

    try:
        menu_service.update_menu(menu)
        st.success(f"✅ 메뉴 '{menu.name}'가 수정되었습니다.")
        logger.info(f"Menu updated: {menu.name}")
        st.rerun()
    except Exception as e:
        st.error(f"❌ 수정 실패: {str(e)}")
        logger.error(f"Failed to update menu: {e}")


def handle_delete_menu(menu_service: MenuService, menu_id: int, menu_name: str):
    """메뉴 삭제 처리"""
    st.warning(f"⚠️ 정말로 메뉴 '{menu_name}'를 삭제하시겠습니까?")

    try:
        menu_service.delete_menu(menu_id)
        st.success(f"✅ 메뉴 '{menu_name}'가 삭제되었습니다.")
        logger.info(f"Menu deleted: {menu_name}")
        st.rerun()
    except Exception as e:
        st.error(f"❌ 삭제 실패: {str(e)}")
        logger.error(f"Failed to delete menu: {e}")


def handle_initialize_menus(menu_service: MenuService):
    """기본 메뉴 초기화 처리"""
    try:
        created_count = menu_service.initialize_default_menus()
        st.success(f"✅ {created_count}개의 기본 메뉴가 생성되었습니다.")
        logger.info(f"Initialized {created_count} default menus")
        st.rerun()
    except Exception as e:
        st.error(f"❌ 초기화 실패: {str(e)}")
        logger.error(f"Failed to initialize menus: {e}")


# 페이지 메인
if __name__ == "__main__":
    render_admin_menus_page()
