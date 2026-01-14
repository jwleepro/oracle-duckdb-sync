"""
사용자 관리 페이지

관리자가 사용자 계정을 생성, 수정, 삭제하는 페이지입니다.
"""

import streamlit as st

from oracle_duckdb_sync.auth import AuthService, UserRole
from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.ui.pages.login import require_auth

# Logger 설정
logger = setup_logger('AdminUsersPage')


@require_auth(required_permission="user:read")
def render_admin_users_page():
    """사용자 관리 페이지 렌더링"""
    st.title("👥 사용자 관리")

    # 설정 및 서비스 초기화
    config = Config()
    auth_service = AuthService(config=config)

    # 탭 구성
    tab1, tab2 = st.tabs(["📋 사용자 목록", "➕ 사용자 생성"])

    with tab1:
        render_user_list(auth_service)

    with tab2:
        render_create_user_form(auth_service)


def render_user_list(auth_service: AuthService):
    """사용자 목록 렌더링"""
    st.subheader("사용자 목록")

    # 사용자 목록 조회
    users = auth_service.list_users(include_inactive=True)

    if not users:
        st.info("등록된 사용자가 없습니다.")
        return

    # 사용자 목록 표시
    for user in users:
        with st.expander(f"{'🟢' if user.is_active else '🔴'} {user.username} ({user.role.value})"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**사용자 ID**: {user.id}")
                st.markdown(f"**사용자명**: {user.username}")
                st.markdown(f"**역할**: {user.role.value}")
                st.markdown(f"**상태**: {'활성' if user.is_active else '비활성'}")

            with col2:
                if user.created_at:
                    st.markdown(f"**생성일**: {user.created_at.strftime('%Y-%m-%d %H:%M')}")
                if user.last_login:
                    st.markdown(f"**마지막 로그인**: {user.last_login.strftime('%Y-%m-%d %H:%M')}")

            # 관리 버튼
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)

            # 역할 변경
            with col1:
                new_role = st.selectbox(
                    "역할 변경",
                    options=[role.value for role in UserRole],
                    index=[role.value for role in UserRole].index(user.role.value),
                    key=f"role_{user.id}"
                )
                if st.button("역할 변경", key=f"change_role_{user.id}"):
                    handle_change_role(auth_service, user.id, UserRole(new_role))

            # 비밀번호 재설정
            with col2:
                new_password = st.text_input(
                    "새 비밀번호",
                    type="password",
                    key=f"password_{user.id}"
                )
                if st.button("비밀번호 재설정", key=f"reset_password_{user.id}"):
                    handle_reset_password(auth_service, user.id, new_password)

            # 활성화/비활성화
            with col3:
                if user.is_active:
                    if st.button("비활성화", key=f"deactivate_{user.id}"):
                        handle_deactivate_user(auth_service, user.id)
                else:
                    if st.button("활성화", key=f"activate_{user.id}"):
                        handle_activate_user(auth_service, user.id)

            # 삭제
            with col4:
                if st.button("🗑️ 삭제", key=f"delete_{user.id}", type="secondary"):
                    handle_delete_user(auth_service, user.id, user.username)


def render_create_user_form(auth_service: AuthService):
    """사용자 생성 폼 렌더링"""
    st.subheader("새 사용자 생성")

    with st.form("create_user_form"):
        username = st.text_input("사용자명", placeholder="user123")
        password = st.text_input("비밀번호", type="password", placeholder="••••••••")
        password_confirm = st.text_input("비밀번호 확인", type="password", placeholder="••••••••")

        role = st.selectbox(
            "역할",
            options=[role.value for role in UserRole],
            index=1  # 기본값: USER
        )

        enforce_strong = st.checkbox("강한 비밀번호 강제", value=True)

        submit = st.form_submit_button("생성", use_container_width=True)

        if submit:
            handle_create_user(auth_service, username, password, password_confirm, UserRole(role), enforce_strong)


def handle_create_user(
    auth_service: AuthService,
    username: str,
    password: str,
    password_confirm: str,
    role: UserRole,
    enforce_strong: bool
):
    """사용자 생성 처리"""
    # 입력 검증
    if not username or not password:
        st.error("사용자명과 비밀번호를 입력하세요.")
        return

    if password != password_confirm:
        st.error("비밀번호가 일치하지 않습니다.")
        return

    # 사용자 생성
    success, message, user = auth_service.create_user(
        username=username,
        password=password,
        role=role,
        enforce_strong_password=enforce_strong
    )

    if success:
        st.success(f"✅ {message}")
        logger.info(f"User created: {username} with role {role.value}")
        st.rerun()
    else:
        st.error(f"❌ {message}")


def handle_change_role(auth_service: AuthService, user_id: int, new_role: UserRole):
    """역할 변경 처리"""
    success, message = auth_service.update_user_role(user_id, new_role)

    if success:
        st.success(f"✅ {message}")
        st.rerun()
    else:
        st.error(f"❌ {message}")


def handle_reset_password(auth_service: AuthService, user_id: int, new_password: str):
    """비밀번호 재설정 처리"""
    if not new_password:
        st.error("새 비밀번호를 입력하세요.")
        return

    # 관리자는 사용자의 비밀번호를 직접 변경할 수 있도록 구현 필요
    # TODO: AuthService에 admin_reset_password 메서드 추가
    user = auth_service.get_user_by_id(user_id)
    if not user:
        st.error("사용자를 찾을 수 없습니다.")
        return

    from oracle_duckdb_sync.auth.password import hash_password

    user.password_hash = hash_password(new_password)
    auth_service.user_repo.update(user)

    st.success("✅ 비밀번호가 재설정되었습니다.")
    logger.info(f"Password reset for user id: {user_id}")
    st.rerun()


def handle_deactivate_user(auth_service: AuthService, user_id: int):
    """사용자 비활성화 처리"""
    success, message = auth_service.deactivate_user(user_id)

    if success:
        st.success(f"✅ {message}")
        st.rerun()
    else:
        st.error(f"❌ {message}")


def handle_activate_user(auth_service: AuthService, user_id: int):
    """사용자 활성화 처리"""
    user = auth_service.get_user_by_id(user_id)
    if not user:
        st.error("사용자를 찾을 수 없습니다.")
        return

    user.is_active = True
    auth_service.user_repo.update(user)

    st.success("✅ 사용자가 활성화되었습니다.")
    logger.info(f"User activated: {user.username}")
    st.rerun()


def handle_delete_user(auth_service: AuthService, user_id: int, username: str):
    """사용자 삭제 처리"""
    # 확인 다이얼로그
    st.warning(f"⚠️ 정말로 사용자 '{username}'를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")

    if st.button(f"예, '{username}' 삭제", key=f"confirm_delete_{user_id}"):
        success, message = auth_service.delete_user(user_id)

        if success:
            st.success(f"✅ {message}")
            st.rerun()
        else:
            st.error(f"❌ {message}")


# 페이지 메인
if __name__ == "__main__":
    render_admin_users_page()
