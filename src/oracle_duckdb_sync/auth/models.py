"""
인증 관련 데이터 모델

사용자 계정 및 권한 관리를 위한 모델입니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class UserRole(Enum):
    """사용자 역할"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


@dataclass
class User:
    """
    사용자 계정 데이터 클래스

    Attributes:
        id: 사용자 고유 ID (자동 생성)
        username: 로그인 ID
        password_hash: 해시된 비밀번호
        role: 사용자 역할
        is_active: 활성화 여부
        created_at: 생성 시각
        last_login: 마지막 로그인 시각
    """
    username: str
    password_hash: str
    role: UserRole = UserRole.USER
    is_active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환 (비밀번호 제외)"""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role.value if isinstance(self.role, UserRole) else self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

    def is_admin(self) -> bool:
        """관리자 여부"""
        return self.role == UserRole.ADMIN

    def can_manage_users(self) -> bool:
        """사용자 관리 권한"""
        return self.role == UserRole.ADMIN

    def can_sync(self) -> bool:
        """동기화 실행 권한"""
        return self.role in (UserRole.ADMIN, UserRole.USER)

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """딕셔너리로부터 생성"""
        return cls(
            id=data.get('id'),
            username=data['username'],
            password_hash=data['password_hash'],
            role=UserRole(data['role']) if isinstance(data['role'], str) else data['role'],
            is_active=data.get('is_active', True),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') and isinstance(data['created_at'], str) else data.get('created_at'),
            last_login=datetime.fromisoformat(data['last_login']) if data.get('last_login') and isinstance(data['last_login'], str) else data.get('last_login')
        )


@dataclass
class Role:
    """
    권한 역할 데이터 클래스

    Attributes:
        id: 역할 고유 ID
        name: 역할명 (admin, user, viewer 등)
        permissions: 권한 목록 (JSON 문자열로 저장)
        description: 역할 설명
    """
    name: str
    permissions: List[str] = field(default_factory=list)
    id: Optional[int] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'name': self.name,
            'permissions': self.permissions,
            'description': self.description
        }

    def has_permission(self, permission: str) -> bool:
        """특정 권한 보유 여부"""
        return permission in self.permissions

    @classmethod
    def from_dict(cls, data: dict) -> 'Role':
        """딕셔너리로부터 생성"""
        import json

        permissions = data.get('permissions', [])
        if isinstance(permissions, str):
            permissions = json.loads(permissions)

        return cls(
            id=data.get('id'),
            name=data['name'],
            permissions=permissions,
            description=data.get('description')
        )


# 기본 권한 정의
class Permission:
    """권한 상수"""
    # 동기화 관련
    SYNC_READ = "sync:read"
    SYNC_WRITE = "sync:write"
    SYNC_DELETE = "sync:delete"

    # 사용자 관리
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"

    # 설정 관리
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"

    # 로그 조회
    LOG_READ = "log:read"

    # 관리자 전체 권한
    ADMIN_ALL = "admin:*"


# 역할별 기본 권한 매핑
DEFAULT_ROLE_PERMISSIONS = {
    UserRole.ADMIN: [Permission.ADMIN_ALL],
    UserRole.USER: [
        Permission.SYNC_READ,
        Permission.SYNC_WRITE,
        Permission.CONFIG_READ,
        Permission.LOG_READ
    ],
    UserRole.VIEWER: [
        Permission.SYNC_READ,
        Permission.CONFIG_READ,
        Permission.LOG_READ
    ]
}
