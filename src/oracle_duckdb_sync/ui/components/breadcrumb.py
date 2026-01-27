"""
브레드크럼 네비게이션 컴포넌트

현재 페이지의 경로를 시각적으로 표시합니다.
"""

import streamlit as st


def render_breadcrumb(current_path: str):
    """
    브레드크럼 네비게이션 렌더링

    Args:
        current_path: 현재 페이지 경로 (예: '/admin/users')
    """
    # 경로를 파트로 분리
    parts = [p for p in current_path.split('/') if p]

    if not parts:
        return

    # 경로 이름 매핑
    path_names = {
        'dashboard': '🏠 대시보드',
        'data': '📊 데이터 조회',
        'visualization': '📈 시각화',
        'agent': '🤖 AI 에이전트',
        'admin': '⚙️ 관리자',
        'sync': '🔄 동기화',
        'users': '👥 사용자',
        'menus': '📑 메뉴',
        'tables': '🗄️ 테이블'
    }

    # 브레드크럼 HTML 생성
    breadcrumb_html = '<div style="padding: 10px 0; font-size: 14px;">'
    breadcrumb_html += '<span style="color: #888;">📍 </span>'

    # 홈 링크
    breadcrumb_html += '<span style="color: #888;">홈</span>'

    # 각 파트 추가
    accumulated_path = ''
    for i, part in enumerate(parts):
        accumulated_path += f'/{part}'
        separator = ' <span style="color: #888;">›</span> '
        name = path_names.get(part, part.title())

        # 마지막 항목은 굵게 표시
        if i == len(parts) - 1:
            breadcrumb_html += f'{separator}<strong>{name}</strong>'
        else:
            breadcrumb_html += f'{separator}{name}'

    breadcrumb_html += '</div>'

    # HTML 렌더링
    st.markdown(breadcrumb_html, unsafe_allow_html=True)


def get_page_title(path: str) -> str:
    """
    경로에서 페이지 제목 추출

    Args:
        path: 페이지 경로

    Returns:
        페이지 제목
    """
    titles = {
        '/dashboard': '대시보드',
        '/data': '데이터 조회',
        '/visualization': '시각화',
        '/agent': 'AI 에이전트',
        '/admin/sync': '동기화 관리',
        '/admin/users': '사용자 관리',
        '/admin/menus': '메뉴 관리',
        '/admin/tables': '테이블 설정'
    }

    return titles.get(path, '페이지')
