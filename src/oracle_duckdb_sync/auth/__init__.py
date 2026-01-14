"""Authentication and authorization module for Oracle-DuckDB Sync."""

from oracle_duckdb_sync.auth.models import DEFAULT_ROLE_PERMISSIONS, Permission, Role, User, UserRole
from oracle_duckdb_sync.auth.password import hash_password, is_password_strong, verify_password
from oracle_duckdb_sync.auth.repository import RoleRepository, UserRepository
from oracle_duckdb_sync.auth.service import AuthService

__all__ = [
    # Models
    'User',
    'Role',
    'UserRole',
    'Permission',
    'DEFAULT_ROLE_PERMISSIONS',
    # Password
    'hash_password',
    'verify_password',
    'is_password_strong',
    # Repository
    'UserRepository',
    'RoleRepository',
    # Service
    'AuthService',
]
