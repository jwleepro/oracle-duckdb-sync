"""
메뉴 관리 데이터 모델

권한 기반 메뉴 시스템을 위한 모델입니다.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Menu:
    """
    메뉴 데이터 클래스

    Attributes:
        id: 메뉴 고유 ID (자동 생성)
        name: 메뉴 표시 이름
        path: 메뉴 경로 (예: '/sync', '/admin/users')
        icon: 메뉴 아이콘 (Streamlit emoji 또는 FontAwesome)
        parent_id: 상위 메뉴 ID (계층 구조를 위한, None이면 최상위)
        required_permission: 필요한 권한 (없으면 누구나 접근 가능)
        order: 메뉴 정렬 순서
        is_active: 활성화 여부
    """
    name: str
    path: str
    icon: str = "📄"
    parent_id: Optional[int] = None
    required_permission: str = ""
    order: int = 0
    is_active: bool = True
    id: Optional[int] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'name': self.name,
            'path': self.path,
            'icon': self.icon,
            'parent_id': self.parent_id,
            'required_permission': self.required_permission,
            'order': self.order,
            'is_active': self.is_active
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Menu':
        """딕셔너리로부터 생성"""
        return cls(
            id=data.get('id'),
            name=data['name'],
            path=data['path'],
            icon=data.get('icon', '📄'),
            parent_id=data.get('parent_id'),
            required_permission=data.get('required_permission', ''),
            order=data.get('order', 0),
            is_active=data.get('is_active', True)
        )

    def has_parent(self) -> bool:
        """상위 메뉴 존재 여부"""
        return self.parent_id is not None

    def requires_permission(self) -> bool:
        """권한이 필요한지 여부"""
        return bool(self.required_permission)


# 기본 메뉴 정의
DEFAULT_MENUS = [
    # 최상위 메뉴
    Menu(
        name="대시보드",
        path="/",
        icon="🏠",
        order=1,
        required_permission=""  # 누구나 접근 가능
    ),
    Menu(
        name="동기화",
        path="/sync",
        icon="🔄",
        order=2,
        required_permission="sync:read"
    ),
    Menu(
        name="로그 조회",
        path="/logs",
        icon="📋",
        order=3,
        required_permission="log:read"
    ),
    Menu(
        name="관리자",
        path="/admin",
        icon="⚙️",
        order=10,
        required_permission="admin:*"
    ),
    # 관리자 하위 메뉴
    Menu(
        name="사용자 관리",
        path="/admin/users",
        icon="👥",
        order=11,
        required_permission="user:read"
        # parent_id는 런타임에 설정
    ),
    Menu(
        name="메뉴 관리",
        path="/admin/menus",
        icon="📑",
        order=12,
        required_permission="admin:*"
        # parent_id는 런타임에 설정
    ),
    Menu(
        name="테이블 설정",
        path="/admin/tables",
        icon="🗄️",
        order=13,
        required_permission="config:write"
        # parent_id는 런타임에 설정
    ),
]
