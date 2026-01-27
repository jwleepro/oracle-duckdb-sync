"""
키보드 단축키 컴포넌트

키보드 단축키를 통한 빠른 네비게이션을 지원합니다.
"""

import streamlit as st
from streamlit.components.v1 import html


def get_shortcut_config():
    """
    단축키 설정 조회

    Returns:
        단축키 설정 딕셔너리
    """
    return {
        'h': {'path': '/dashboard', 'name': '대시보드 (Home)'},
        'd': {'path': '/data', 'name': '데이터 조회 (Data)'},
        'v': {'path': '/visualization', 'name': '시각화 (Visualization)'},
        'a': {'path': '/agent', 'name': 'AI 에이전트 (Agent)'},
        's': {'path': '/admin/sync', 'name': '동기화 관리 (Sync)', 'admin_only': True},
        'u': {'path': '/admin/users', 'name': '사용자 관리 (Users)', 'admin_only': True},
        'm': {'path': '/admin/menus', 'name': '메뉴 관리 (Menus)', 'admin_only': True},
        't': {'path': '/admin/tables', 'name': '테이블 설정 (Tables)', 'admin_only': True},
    }


def render_keyboard_shortcuts():
    """
    키보드 단축키 이벤트 리스너 렌더링

    JavaScript를 사용하여 키보드 이벤트를 감지하고 Streamlit과 통신
    """
    shortcuts_config = get_shortcut_config()

    # JavaScript 코드
    js_code = """
    <script>
    // 이미 리스너가 등록되어 있는지 확인
    if (!window.shortcutListenerRegistered) {
        window.shortcutListenerRegistered = true;

        document.addEventListener('keydown', function(event) {
            // Ctrl 또는 Cmd 키와 함께 눌렀을 때만 동작
            if ((event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey) {
                const key = event.key.toLowerCase();
                const shortcuts = """ + str(list(shortcuts_config.keys())) + """;

                if (shortcuts.includes(key)) {
                    event.preventDefault();

                    // Streamlit 세션 상태 업데이트를 위한 커스텀 이벤트
                    const customEvent = new CustomEvent('shortcut', {
                        detail: { key: key }
                    });
                    document.dispatchEvent(customEvent);

                    // 페이지 리로드 (단축키 실행)
                    const input = document.querySelector('input[aria-label="shortcut_key"]');
                    if (input) {
                        input.value = key;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
            }

            // 도움말 표시 (Ctrl/Cmd + /)
            if ((event.ctrlKey || event.metaKey) && event.key === '/') {
                event.preventDefault();
                const helpButton = document.querySelector('button[aria-label="shortcuts_help"]');
                if (helpButton) {
                    helpButton.click();
                }
            }
        });
    }
    </script>
    """

    html(js_code, height=0)


def handle_keyboard_shortcut(key: str, user):
    """
    키보드 단축키 처리

    Args:
        key: 눌린 키
        user: 현재 사용자
    """
    shortcuts_config = get_shortcut_config()

    if key not in shortcuts_config:
        return False

    shortcut = shortcuts_config[key]

    # 관리자 전용 단축키 체크
    if shortcut.get('admin_only', False):
        if not user or not user.is_admin():
            st.warning(f"⚠️ '{shortcut['name']}' 페이지는 관리자만 접근할 수 있습니다.")
            return False

    # 페이지 이동
    st.session_state.current_page = shortcut['path']
    return True


def render_shortcuts_help():
    """
    단축키 도움말 표시

    사이드바에 사용 가능한 단축키 목록 표시
    """
    shortcuts_config = get_shortcut_config()

    st.sidebar.markdown("---")

    # 도움말 토글
    if 'show_shortcuts_help' not in st.session_state:
        st.session_state.show_shortcuts_help = False

    col1, col2 = st.sidebar.columns([4, 1])
    with col1:
        st.markdown("### ⌨️ 키보드 단축키")
    with col2:
        if st.button(
            "❓",
            key="shortcuts_help",
            help="단축키 도움말",
            use_container_width=False
        ):
            st.session_state.show_shortcuts_help = not st.session_state.show_shortcuts_help

    if st.session_state.show_shortcuts_help:
        st.sidebar.markdown("""
        **단축키 사용법:**
        - `Ctrl` (또는 `Cmd`) + `키`를 눌러 페이지 이동
        - `Ctrl/Cmd + /`: 이 도움말 표시

        **사용 가능한 단축키:**
        """)

        for key, config in shortcuts_config.items():
            admin_badge = " 🔒" if config.get('admin_only', False) else ""
            st.sidebar.markdown(f"- `Ctrl+{key.upper()}`: {config['name']}{admin_badge}")

        st.sidebar.markdown("---")


def initialize_shortcuts(user):
    """
    키보드 단축키 초기화

    Args:
        user: 현재 사용자
    """
    # 단축키 이벤트 리스너 렌더링
    render_keyboard_shortcuts()

    # 숨겨진 입력 필드 (JavaScript에서 값 설정)
    shortcut_key = st.text_input(
        "shortcut_key",
        value="",
        key="shortcut_key_input",
        label_visibility="collapsed"
    )

    # 단축키 처리
    if shortcut_key:
        if handle_keyboard_shortcut(shortcut_key, user):
            # 입력 필드 초기화
            st.session_state.shortcut_key_input = ""
            st.rerun()
