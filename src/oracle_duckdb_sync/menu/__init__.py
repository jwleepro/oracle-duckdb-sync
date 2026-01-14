"""Menu management module for Oracle-DuckDB Sync."""

from oracle_duckdb_sync.menu.models import DEFAULT_MENUS, Menu
from oracle_duckdb_sync.menu.repository import MenuRepository
from oracle_duckdb_sync.menu.service import MenuService

__all__ = [
    'Menu',
    'DEFAULT_MENUS',
    'MenuRepository',
    'MenuService',
]
