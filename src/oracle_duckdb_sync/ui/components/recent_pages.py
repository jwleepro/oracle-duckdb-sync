"""
최근 방문 페이지 컴포넌트

사용자가 최근에 방문한 페이지를 추적하고 표시합니다.
"""

import streamlit as st
from datetime import datetime


def initialize_recent_pages():
    """최근 방문 페이지 세션 상태 초기화"""
    if 'recent_pages' not in st.session_state:
        st.session_state.recent_pages = []


def add_recent_page(path: str, name: str, max_items: int = 5):
    """
    최근 방문 페이지 추가

    Args:
        path: 페이지 경로
        name: 페이지 이름
        max_items: 최대 저장 개수
    """
    initialize_recent_pages()

    # 중복 제거 (기존 항목 제거)
    st.session_state.recent_pages = [
        page for page in st.session_state.recent_pages
        if page['path'] != path
    ]

    # 새 항목 추가 (맨 앞에)
    st.session_state.recent_pages.insert(0, {
        'path': path,
        'name': name,
        'timestamp': datetime.now()
    })

    # 최대 개수 유지
    if len(st.session_state.recent_pages) > max_items:
        st.session_state.recent_pages = st.session_state.recent_pages[:max_items]


def get_recent_pages(max_items: int = 5):
    """
    최근 방문 페이지 목록 조회

    Args:
        max_items: 최대 반환 개수

    Returns:
        최근 방문 페이지 목록
    """
    initialize_recent_pages()
    return st.session_state.recent_pages[:max_items]


def render_recent_pages_section():
    """
    최근 방문 페이지 섹션 렌더링

    사이드바에 최근 방문 페이지 표시
    """
    recent_pages = get_recent_pages()

    if not recent_pages:
        return

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🕒 최근 방문")

    for page in recent_pages:
        # 현재 페이지는 표시 안 함
        if page['path'] == st.session_state.get('current_page'):
            continue

        if st.sidebar.button(
            page['name'],
            key=f"recent_{page['path']}_{page['timestamp'].timestamp()}",
            use_container_width=True
        ):
            st.session_state.current_page = page['path']
            st.rerun()


def clear_recent_pages():
    """최근 방문 페이지 목록 초기화"""
    if 'recent_pages' in st.session_state:
        st.session_state.recent_pages = []
