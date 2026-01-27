"""
로그인 페이지

사용자 인증을 처리하는 Streamlit 페이지입니다.
"""

import streamlit as st

from oracle_duckdb_sync.auth import AuthService
from oracle_duckdb_sync.config import load_config
from oracle_duckdb_sync.log.logger import setup_logger

# Logger 설정
logger = setup_logger('LoginPage')


def render_login_page():
    """로그인 페이지 렌더링"""
    st.title("🔐 로그인")

    # 이미 로그인된 경우
    if st.session_state.get('authenticated', False):
        st.success(f"✅ {st.session_state.get('user').username}님으로 로그인되어 있습니다.")
        if st.button("로그아웃"):
            handle_logout()
            st.rerun()
        return

    # 로그인 폼
    with st.form("login_form"):
        st.markdown("### 계정 정보를 입력하세요")

        username = st.text_input("사용자명", placeholder="admin")
        password = st.text_input("비밀번호", type="password", placeholder="••••••••")

        col1, col2 = st.columns([1, 3])
        with col1:
            submit = st.form_submit_button("로그인", use_container_width=True)

        if submit:
            handle_login(username, password)


def handle_login(username: str, password: str):
    """
    로그인 처리

    Args:
        username: 사용자명
        password: 비밀번호
    """
    if not username or not password:
        st.error("사용자명과 비밀번호를 입력하세요.")
        return

    # 설정 로드
    config = load_config()

    # 인증 서비스 생성
    auth_service = AuthService(config=config)

    # 인증 시도
    success, message, user = auth_service.authenticate(username, password)

    if success:
        # 세션에 사용자 정보 저장
        st.session_state.authenticated = True
        st.session_state.user = user
        logger.info(f"User logged in: {username}")

        st.success(f"✅ {message}")
        st.balloons()

        # 페이지 리로드
        st.rerun()
    else:
        logger.warning(f"Failed login attempt: {username}")
        st.error(f"❌ {message}")


def handle_logout():
    """로그아웃 처리"""
    if st.session_state.get('authenticated', False):
        username = st.session_state.get('user').username if st.session_state.get('user') else 'Unknown'
        logger.info(f"User logged out: {username}")

    # 세션 정보 삭제
    st.session_state.authenticated = False
    st.session_state.user = None
    st.success("로그아웃되었습니다.")


def require_auth(required_permission: str = None):
    """
    인증 필수 데코레이터

    페이지 함수에 적용하여 로그인하지 않은 사용자를 차단합니다.

    Args:
        required_permission: 필요한 권한 (선택적)

    Returns:
        데코레이터 함수
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 로그인 체크
            if not st.session_state.get('authenticated', False):
                st.warning("⚠️ 로그인이 필요합니다.")
                render_login_page()
                st.stop()

            # 권한 체크
            if required_permission:
                user = st.session_state.get('user')
                config = load_config()
                auth_service = AuthService(config=config)

                if not auth_service.has_permission(user, required_permission):
                    st.error("❌ 이 페이지에 접근할 권한이 없습니다.")
                    logger.warning(f"Permission denied: {user.username} tried to access with {required_permission}")
                    st.stop()

            return func(*args, **kwargs)
        return wrapper
    return decorator


# 페이지 메인
if __name__ == "__main__":
    render_login_page()
