"""
사용자 및 권한 저장소

DuckDB에 사용자 계정을 저장하고 조회하는 CRUD 레포지토리입니다.
"""

from datetime import datetime
from typing import List, Optional

from oracle_duckdb_sync.auth.models import Role, User, UserRole
from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger


class UserRepository:
    """
    사용자 저장소

    DuckDB의 users 테이블을 관리합니다.
    """

    TABLE_NAME = 'users'

    def __init__(self, config: Config = None, duckdb_source: DuckDBSource = None):
        """
        Args:
            config: 애플리케이션 설정
            duckdb_source: DuckDB 소스 객체 (테스트 시 사용)
        """
        self.logger = setup_logger('UserRepository')

        if duckdb_source:
            self.duckdb = duckdb_source
        elif config:
            self.duckdb = DuckDBSource(config)
        else:
            raise ValueError("Either config or duckdb_source must be provided")

        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """users 테이블이 없으면 생성"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            id INTEGER PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'user',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        """

        try:
            self.duckdb.conn.execute(create_table_sql)
            self.logger.debug(f"Table {self.TABLE_NAME} is ready")
        except Exception as e:
            self.logger.error(f"Failed to create {self.TABLE_NAME} table: {e}")
            raise

    def create(self, user: User) -> User:
        """
        새 사용자 생성

        Args:
            user: 생성할 User 객체

        Returns:
            생성된 User 객체 (id 포함)
        """
        insert_sql = f"""
        INSERT INTO {self.TABLE_NAME}
        (username, password_hash, role, is_active, created_at)
        VALUES (?, ?, ?, ?, ?)
        """

        created_at = user.created_at or datetime.now()

        params = (
            user.username,
            user.password_hash,
            user.role.value if isinstance(user.role, UserRole) else user.role,
            user.is_active,
            created_at
        )

        try:
            self.duckdb.conn.execute(insert_sql, params)

            # Get the auto-generated ID
            result = self.duckdb.conn.execute("SELECT last_insert_rowid()").fetchone()
            user.id = result[0]
            user.created_at = created_at

            self.logger.info(f"Created user: {user.username} with role {user.role.value}")
            return user

        except Exception as e:
            self.logger.error(f"Failed to create user: {e}")
            raise

    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        ID로 사용자 조회

        Args:
            user_id: 사용자 ID

        Returns:
            User 객체 또는 None
        """
        select_sql = f"""
        SELECT id, username, password_hash, role, is_active, created_at, last_login
        FROM {self.TABLE_NAME}
        WHERE id = ?
        """

        try:
            result = self.duckdb.conn.execute(select_sql, (user_id,)).fetchone()
            if result:
                return self._row_to_user(result)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get user by id: {e}")
            raise

    def get_by_username(self, username: str) -> Optional[User]:
        """
        사용자명으로 조회

        Args:
            username: 사용자명

        Returns:
            User 객체 또는 None
        """
        select_sql = f"""
        SELECT id, username, password_hash, role, is_active, created_at, last_login
        FROM {self.TABLE_NAME}
        WHERE username = ?
        """

        try:
            result = self.duckdb.conn.execute(select_sql, (username,)).fetchone()
            if result:
                return self._row_to_user(result)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get user by username: {e}")
            raise

    def exists(self, username: str) -> bool:
        """
        사용자 존재 여부 확인

        Args:
            username: 사용자명

        Returns:
            존재 여부
        """
        return self.get_by_username(username) is not None

    def get_all(self, include_inactive: bool = False) -> List[User]:
        """
        모든 사용자 조회

        Args:
            include_inactive: 비활성 사용자 포함 여부

        Returns:
            User 리스트
        """
        where_clause = "" if include_inactive else "WHERE is_active = TRUE"
        select_sql = f"""
        SELECT id, username, password_hash, role, is_active, created_at, last_login
        FROM {self.TABLE_NAME}
        {where_clause}
        ORDER BY created_at DESC
        """

        try:
            results = self.duckdb.conn.execute(select_sql).fetchall()
            return [self._row_to_user(row) for row in results]

        except Exception as e:
            self.logger.error(f"Failed to get all users: {e}")
            raise

    def update(self, user: User) -> User:
        """
        사용자 정보 업데이트

        Args:
            user: 업데이트할 User 객체 (id 필수)

        Returns:
            업데이트된 User 객체
        """
        if not user.id:
            raise ValueError("User must have an ID to update")

        update_sql = f"""
        UPDATE {self.TABLE_NAME}
        SET username = ?,
            password_hash = ?,
            role = ?,
            is_active = ?,
            last_login = ?
        WHERE id = ?
        """

        params = (
            user.username,
            user.password_hash,
            user.role.value if isinstance(user.role, UserRole) else user.role,
            user.is_active,
            user.last_login,
            user.id
        )

        try:
            self.duckdb.conn.execute(update_sql, params)
            self.logger.info(f"Updated user: {user.username}")
            return user

        except Exception as e:
            self.logger.error(f"Failed to update user: {e}")
            raise

    def update_last_login(self, user_id: int):
        """
        마지막 로그인 시각 업데이트

        Args:
            user_id: 사용자 ID
        """
        update_sql = f"""
        UPDATE {self.TABLE_NAME}
        SET last_login = ?
        WHERE id = ?
        """

        try:
            self.duckdb.conn.execute(update_sql, (datetime.now(), user_id))
            self.logger.debug(f"Updated last login for user id: {user_id}")

        except Exception as e:
            self.logger.error(f"Failed to update last login: {e}")
            raise

    def delete(self, user_id: int) -> bool:
        """
        사용자 삭제

        Args:
            user_id: 사용자 ID

        Returns:
            삭제 성공 여부
        """
        delete_sql = f"""
        DELETE FROM {self.TABLE_NAME}
        WHERE id = ?
        """

        try:
            self.duckdb.conn.execute(delete_sql, (user_id,))
            self.logger.info(f"Deleted user id: {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete user: {e}")
            raise

    def deactivate(self, user_id: int):
        """
        사용자 비활성화 (soft delete)

        Args:
            user_id: 사용자 ID
        """
        update_sql = f"""
        UPDATE {self.TABLE_NAME}
        SET is_active = FALSE
        WHERE id = ?
        """

        try:
            self.duckdb.conn.execute(update_sql, (user_id,))
            self.logger.info(f"Deactivated user id: {user_id}")

        except Exception as e:
            self.logger.error(f"Failed to deactivate user: {e}")
            raise

    def _row_to_user(self, row: tuple) -> User:
        """
        DB 행을 User 객체로 변환

        Args:
            row: (id, username, password_hash, role, is_active, created_at, last_login)

        Returns:
            User 객체
        """
        return User(
            id=row[0],
            username=row[1],
            password_hash=row[2],
            role=UserRole(row[3]),
            is_active=row[4],
            created_at=row[5],
            last_login=row[6]
        )


class RoleRepository:
    """
    역할 저장소

    DuckDB의 roles 테이블을 관리합니다.
    """

    TABLE_NAME = 'roles'

    def __init__(self, config: Config = None, duckdb_source: DuckDBSource = None):
        """
        Args:
            config: 애플리케이션 설정
            duckdb_source: DuckDB 소스 객체
        """
        self.logger = setup_logger('RoleRepository')

        if duckdb_source:
            self.duckdb = duckdb_source
        elif config:
            self.duckdb = DuckDBSource(config)
        else:
            raise ValueError("Either config or duckdb_source must be provided")

        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """roles 테이블이 없으면 생성"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            id INTEGER PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            permissions TEXT,
            description TEXT
        )
        """

        try:
            self.duckdb.conn.execute(create_table_sql)
            self.logger.debug(f"Table {self.TABLE_NAME} is ready")
        except Exception as e:
            self.logger.error(f"Failed to create {self.TABLE_NAME} table: {e}")
            raise

    def create(self, role: Role) -> Role:
        """역할 생성"""
        import json

        insert_sql = f"""
        INSERT INTO {self.TABLE_NAME}
        (name, permissions, description)
        VALUES (?, ?, ?)
        """

        params = (
            role.name,
            json.dumps(role.permissions),
            role.description
        )

        try:
            self.duckdb.conn.execute(insert_sql, params)
            result = self.duckdb.conn.execute("SELECT last_insert_rowid()").fetchone()
            role.id = result[0]

            self.logger.info(f"Created role: {role.name}")
            return role

        except Exception as e:
            self.logger.error(f"Failed to create role: {e}")
            raise

    def get_by_name(self, name: str) -> Optional[Role]:
        """이름으로 역할 조회"""
        select_sql = f"""
        SELECT id, name, permissions, description
        FROM {self.TABLE_NAME}
        WHERE name = ?
        """

        try:
            result = self.duckdb.conn.execute(select_sql, (name,)).fetchone()
            if result:
                return self._row_to_role(result)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get role by name: {e}")
            raise

    def _row_to_role(self, row: tuple) -> Role:
        """DB 행을 Role 객체로 변환"""
        import json

        permissions = json.loads(row[2]) if row[2] else []

        return Role(
            id=row[0],
            name=row[1],
            permissions=permissions,
            description=row[3]
        )
