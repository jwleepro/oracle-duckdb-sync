"""
인증 서비스

사용자 인증, 권한 검사 등의 비즈니스 로직을 담당합니다.
"""

from typing import Optional, Tuple

from oracle_duckdb_sync.auth.models import User, UserRole
from oracle_duckdb_sync.auth.password import hash_password, is_password_strong, verify_password
from oracle_duckdb_sync.auth.repository import UserRepository
from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger


class AuthService:
    """
    인증 서비스

    사용자 생성, 로그인, 권한 검사 등을 담당합니다.
    """

    def __init__(self, config: Config = None, duckdb_source: DuckDBSource = None):
        """
        Args:
            config: 애플리케이션 설정
            duckdb_source: DuckDB 소스 객체
        """
        self.logger = setup_logger('AuthService')
        self.user_repo = UserRepository(config=config, duckdb_source=duckdb_source)

    def create_user(
        self,
        username: str,
        password: str,
        role: UserRole = UserRole.USER,
        enforce_strong_password: bool = True
    ) -> Tuple[bool, str, Optional[User]]:
        """
        새 사용자 생성

        Args:
            username: 사용자명
            password: 평문 비밀번호
            role: 사용자 역할
            enforce_strong_password: 강한 비밀번호 강제 여부

        Returns:
            (성공 여부, 메시지, User 객체 또는 None)
        """
        # 사용자명 중복 체크
        if self.user_repo.exists(username):
            return False, f"사용자명 '{username}'이(가) 이미 존재합니다.", None

        # 비밀번호 강도 체크
        if enforce_strong_password:
            is_strong, msg = is_password_strong(password)
            if not is_strong:
                return False, msg, None

        # 비밀번호 해싱
        password_hash = hash_password(password)

        # 사용자 생성
        try:
            user = User(
                username=username,
                password_hash=password_hash,
                role=role
            )
            created_user = self.user_repo.create(user)
            self.logger.info(f"User created: {username} with role {role.value}")
            return True, "사용자가 생성되었습니다.", created_user

        except Exception as e:
            self.logger.error(f"Failed to create user: {e}")
            return False, f"사용자 생성 실패: {str(e)}", None

    def authenticate(self, username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """
        사용자 인증

        Args:
            username: 사용자명
            password: 평문 비밀번호

        Returns:
            (인증 성공 여부, 메시지, User 객체 또는 None)
        """
        # 사용자 조회
        user = self.user_repo.get_by_username(username)

        if not user:
            self.logger.warning(f"Login attempt with non-existent username: {username}")
            return False, "사용자명 또는 비밀번호가 올바르지 않습니다.", None

        # 활성화 여부 체크
        if not user.is_active:
            self.logger.warning(f"Login attempt with inactive user: {username}")
            return False, "비활성화된 계정입니다. 관리자에게 문의하세요.", None

        # 비밀번호 검증
        if not verify_password(password, user.password_hash):
            self.logger.warning(f"Failed login attempt for user: {username}")
            return False, "사용자명 또는 비밀번호가 올바르지 않습니다.", None

        # 로그인 성공 - 마지막 로그인 시각 업데이트
        try:
            self.user_repo.update_last_login(user.id)
            self.logger.info(f"User authenticated: {username}")
            return True, "로그인 성공", user

        except Exception as e:
            self.logger.error(f"Failed to update last login: {e}")
            # 로그인은 성공했으므로 True 반환
            return True, "로그인 성공", user

    def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
        enforce_strong_password: bool = True
    ) -> Tuple[bool, str]:
        """
        비밀번호 변경

        Args:
            user_id: 사용자 ID
            old_password: 기존 비밀번호
            new_password: 새 비밀번호
            enforce_strong_password: 강한 비밀번호 강제 여부

        Returns:
            (성공 여부, 메시지)
        """
        # 사용자 조회
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False, "사용자를 찾을 수 없습니다."

        # 기존 비밀번호 확인
        if not verify_password(old_password, user.password_hash):
            self.logger.warning(f"Password change failed for user {user.username}: wrong old password")
            return False, "기존 비밀번호가 올바르지 않습니다."

        # 새 비밀번호 강도 체크
        if enforce_strong_password:
            is_strong, msg = is_password_strong(new_password)
            if not is_strong:
                return False, msg

        # 비밀번호 해싱 및 업데이트
        try:
            user.password_hash = hash_password(new_password)
            self.user_repo.update(user)
            self.logger.info(f"Password changed for user: {user.username}")
            return True, "비밀번호가 변경되었습니다."

        except Exception as e:
            self.logger.error(f"Failed to change password: {e}")
            return False, f"비밀번호 변경 실패: {str(e)}"

    def update_user_role(self, user_id: int, new_role: UserRole) -> Tuple[bool, str]:
        """
        사용자 역할 변경

        Args:
            user_id: 사용자 ID
            new_role: 새로운 역할

        Returns:
            (성공 여부, 메시지)
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False, "사용자를 찾을 수 없습니다."

        try:
            old_role = user.role
            user.role = new_role
            self.user_repo.update(user)
            self.logger.info(f"User role changed: {user.username} from {old_role.value} to {new_role.value}")
            return True, f"사용자 역할이 {new_role.value}(으)로 변경되었습니다."

        except Exception as e:
            self.logger.error(f"Failed to update user role: {e}")
            return False, f"역할 변경 실패: {str(e)}"

    def deactivate_user(self, user_id: int) -> Tuple[bool, str]:
        """
        사용자 비활성화

        Args:
            user_id: 사용자 ID

        Returns:
            (성공 여부, 메시지)
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False, "사용자를 찾을 수 없습니다."

        try:
            self.user_repo.deactivate(user_id)
            self.logger.info(f"User deactivated: {user.username}")
            return True, "사용자가 비활성화되었습니다."

        except Exception as e:
            self.logger.error(f"Failed to deactivate user: {e}")
            return False, f"비활성화 실패: {str(e)}"

    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """
        사용자 삭제

        Args:
            user_id: 사용자 ID

        Returns:
            (성공 여부, 메시지)
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False, "사용자를 찾을 수 없습니다."

        try:
            self.user_repo.delete(user_id)
            self.logger.info(f"User deleted: {user.username}")
            return True, "사용자가 삭제되었습니다."

        except Exception as e:
            self.logger.error(f"Failed to delete user: {e}")
            return False, f"삭제 실패: {str(e)}"

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """사용자 ID로 조회"""
        return self.user_repo.get_by_id(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """사용자명으로 조회"""
        return self.user_repo.get_by_username(username)

    def list_users(self, include_inactive: bool = False) -> list[User]:
        """모든 사용자 조회"""
        return self.user_repo.get_all(include_inactive=include_inactive)

    def has_permission(self, user: User, permission: str) -> bool:
        """
        사용자 권한 검사

        Args:
            user: 사용자 객체
            permission: 검사할 권한

        Returns:
            권한 보유 여부
        """
        # 관리자는 모든 권한 보유
        if user.is_admin():
            return True

        # TODO: Role 테이블과 연동하여 세밀한 권한 체크
        # 현재는 UserRole 기반 간단한 권한 체크
        from oracle_duckdb_sync.auth.models import DEFAULT_ROLE_PERMISSIONS

        role_permissions = DEFAULT_ROLE_PERMISSIONS.get(user.role, [])
        return permission in role_permissions
