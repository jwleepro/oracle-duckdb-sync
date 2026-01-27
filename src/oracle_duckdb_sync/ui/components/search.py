"""
메뉴 검색 컴포넌트

사용자가 메뉴를 검색하여 빠르게 페이지로 이동할 수 있습니다.
"""

import streamlit as st
from typing import List, Dict


def get_searchable_pages(user) -> List[Dict[str, str]]:
    """
    검색 가능한 페이지 목록 조회

    Args:
        user: 현재 사용자

    Returns:
        페이지 목록 (path, name, category, keywords)
    """
    pages = [
        {
            'path': '/dashboard',
            'name': '대시보드',
            'icon': '🏠',
            'category': '일반',
            'keywords': ['대시보드', 'dashboard', '홈', 'home', '메인']
        },
        {
            'path': '/data',
            'name': '데이터 조회',
            'icon': '📊',
            'category': '일반',
            'keywords': ['데이터', 'data', '조회', 'query', '테이블', 'table']
        },
        {
            'path': '/visualization',
            'name': '시각화',
            'icon': '📈',
            'category': '일반',
            'keywords': ['시각화', 'visualization', '차트', 'chart', '그래프', 'graph']
        },
        {
            'path': '/agent',
            'name': 'AI 에이전트',
            'icon': '🤖',
            'category': '일반',
            'keywords': ['에이전트', 'agent', 'ai', '인공지능', '챗봇', 'chatbot']
        }
    ]

    # 관리자 페이지 (ADMIN만)
    if user and user.is_admin():
        admin_pages = [
            {
                'path': '/admin/sync',
                'name': '동기화 관리',
                'icon': '🔄',
                'category': '관리자',
                'keywords': ['동기화', 'sync', '관리', 'manage', '실행', 'run']
            },
            {
                'path': '/admin/users',
                'name': '사용자 관리',
                'icon': '👥',
                'category': '관리자',
                'keywords': ['사용자', 'user', '계정', 'account', '권한', 'permission']
            },
            {
                'path': '/admin/menus',
                'name': '메뉴 관리',
                'icon': '📑',
                'category': '관리자',
                'keywords': ['메뉴', 'menu', '네비게이션', 'navigation']
            },
            {
                'path': '/admin/tables',
                'name': '테이블 설정',
                'icon': '🗄️',
                'category': '관리자',
                'keywords': ['테이블', 'table', '설정', 'config', '구성', 'configuration']
            }
        ]
        pages.extend(admin_pages)

    return pages


def search_pages(query: str, pages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    페이지 검색

    Args:
        query: 검색어
        pages: 검색 대상 페이지 목록

    Returns:
        검색 결과 페이지 목록
    """
    if not query:
        return pages

    query_lower = query.lower()
    results = []

    for page in pages:
        # 이름 매칭
        if query_lower in page['name'].lower():
            results.append(page)
            continue

        # 키워드 매칭
        for keyword in page['keywords']:
            if query_lower in keyword.lower():
                results.append(page)
                break

    return results


def render_search_box(user):
    """
    검색 박스 렌더링

    Args:
        user: 현재 사용자
    """
    st.sidebar.markdown("### 🔍 메뉴 검색")

    # 검색어 입력
    query = st.sidebar.text_input(
        "검색",
        placeholder="메뉴 이름 또는 키워드 입력...",
        label_visibility="collapsed",
        key="menu_search_query"
    )

    if query:
        # 검색 실행
        all_pages = get_searchable_pages(user)
        results = search_pages(query, all_pages)

        if results:
            st.sidebar.markdown(f"**검색 결과** ({len(results)}개)")

            for page in results:
                # 카테고리 표시
                category_badge = f"<span style='font-size: 10px; color: #888;'>[{page['category']}]</span>"

                col1, col2 = st.sidebar.columns([1, 5])

                with col1:
                    st.markdown(page['icon'], unsafe_allow_html=True)

                with col2:
                    if st.button(
                        f"{page['name']}",
                        key=f"search_result_{page['path']}",
                        use_container_width=True
                    ):
                        st.session_state.current_page = page['path']
                        st.session_state.menu_search_query = ""  # 검색어 초기화
                        st.rerun()

                st.sidebar.markdown(category_badge, unsafe_allow_html=True)
        else:
            st.sidebar.info("검색 결과가 없습니다.")

        # 검색 초기화 버튼
        if st.sidebar.button("🔄 초기화", use_container_width=True):
            st.session_state.menu_search_query = ""
            st.rerun()
