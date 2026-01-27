"""
즐겨찾기 메뉴 컴포넌트

사용자가 자주 사용하는 페이지를 즐겨찾기로 저장하고 빠르게 접근할 수 있습니다.
"""

import streamlit as st


def initialize_favorites():
    """즐겨찾기 세션 상태 초기화"""
    if 'favorites' not in st.session_state:
        st.session_state.favorites = []


def add_favorite(path: str, name: str):
    """
    즐겨찾기 추가

    Args:
        path: 페이지 경로
        name: 페이지 이름
    """
    initialize_favorites()

    # 중복 체크
    for fav in st.session_state.favorites:
        if fav['path'] == path:
            return False

    st.session_state.favorites.append({
        'path': path,
        'name': name
    })
    return True


def remove_favorite(path: str):
    """
    즐겨찾기 제거

    Args:
        path: 페이지 경로
    """
    initialize_favorites()

    st.session_state.favorites = [
        fav for fav in st.session_state.favorites
        if fav['path'] != path
    ]


def is_favorite(path: str) -> bool:
    """
    즐겨찾기 여부 확인

    Args:
        path: 페이지 경로

    Returns:
        즐겨찾기 여부
    """
    initialize_favorites()

    for fav in st.session_state.favorites:
        if fav['path'] == path:
            return True
    return False


def toggle_favorite(path: str, name: str):
    """
    즐겨찾기 토글

    Args:
        path: 페이지 경로
        name: 페이지 이름
    """
    if is_favorite(path):
        remove_favorite(path)
    else:
        add_favorite(path, name)


def render_favorites_section():
    """
    즐겨찾기 섹션 렌더링

    사이드바에 즐겨찾기 목록 표시
    """
    initialize_favorites()

    if not st.session_state.favorites:
        return

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⭐ 즐겨찾기")

    for fav in st.session_state.favorites:
        col1, col2 = st.sidebar.columns([5, 1])

        with col1:
            if st.button(
                fav['name'],
                key=f"fav_{fav['path']}",
                use_container_width=True
            ):
                st.session_state.current_page = fav['path']
                st.rerun()

        with col2:
            if st.button(
                "❌",
                key=f"remove_fav_{fav['path']}",
                help="즐겨찾기 제거"
            ):
                remove_favorite(fav['path'])
                st.rerun()


def render_favorite_button(path: str, name: str):
    """
    즐겨찾기 버튼 렌더링

    페이지 상단에 즐겨찾기 추가/제거 버튼 표시

    Args:
        path: 페이지 경로
        name: 페이지 이름
    """
    is_fav = is_favorite(path)
    button_text = "⭐ 즐겨찾기 제거" if is_fav else "☆ 즐겨찾기 추가"

    if st.button(button_text, key=f"toggle_fav_{path}"):
        toggle_favorite(path, name)
        st.rerun()
