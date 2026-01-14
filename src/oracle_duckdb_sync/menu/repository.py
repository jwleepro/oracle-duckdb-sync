"""
메뉴 저장소

DuckDB에 메뉴를 저장하고 조회하는 CRUD 레포지토리입니다.
"""

from typing import List, Optional

from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.menu.models import Menu


class MenuRepository:
    """
    메뉴 저장소

    DuckDB의 menus 테이블을 관리합니다.
    """

    TABLE_NAME = 'menus'

    def __init__(self, config: Config = None, duckdb_source: DuckDBSource = None):
        """
        Args:
            config: 애플리케이션 설정
            duckdb_source: DuckDB 소스 객체
        """
        self.logger = setup_logger('MenuRepository')

        if duckdb_source:
            self.duckdb = duckdb_source
        elif config:
            self.duckdb = DuckDBSource(config)
        else:
            raise ValueError("Either config or duckdb_source must be provided")

        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """menus 테이블이 없으면 생성"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            path VARCHAR(255) UNIQUE NOT NULL,
            icon VARCHAR(50),
            parent_id INTEGER,
            required_permission VARCHAR(100),
            "order" INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (parent_id) REFERENCES {self.TABLE_NAME}(id) ON DELETE CASCADE
        )
        """

        try:
            self.duckdb.conn.execute(create_table_sql)
            self.logger.debug(f"Table {self.TABLE_NAME} is ready")
        except Exception as e:
            self.logger.error(f"Failed to create {self.TABLE_NAME} table: {e}")
            raise

    def create(self, menu: Menu) -> Menu:
        """
        새 메뉴 생성

        Args:
            menu: 생성할 Menu 객체

        Returns:
            생성된 Menu 객체 (id 포함)
        """
        insert_sql = f"""
        INSERT INTO {self.TABLE_NAME}
        (name, path, icon, parent_id, required_permission, "order", is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            menu.name,
            menu.path,
            menu.icon,
            menu.parent_id,
            menu.required_permission,
            menu.order,
            menu.is_active
        )

        try:
            self.duckdb.conn.execute(insert_sql, params)

            # Get the auto-generated ID
            result = self.duckdb.conn.execute("SELECT last_insert_rowid()").fetchone()
            menu.id = result[0]

            self.logger.info(f"Created menu: {menu.name} at path {menu.path}")
            return menu

        except Exception as e:
            self.logger.error(f"Failed to create menu: {e}")
            raise

    def get_by_id(self, menu_id: int) -> Optional[Menu]:
        """
        ID로 메뉴 조회

        Args:
            menu_id: 메뉴 ID

        Returns:
            Menu 객체 또는 None
        """
        select_sql = f"""
        SELECT id, name, path, icon, parent_id, required_permission, "order", is_active
        FROM {self.TABLE_NAME}
        WHERE id = ?
        """

        try:
            result = self.duckdb.conn.execute(select_sql, (menu_id,)).fetchone()
            if result:
                return self._row_to_menu(result)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get menu by id: {e}")
            raise

    def get_by_path(self, path: str) -> Optional[Menu]:
        """
        경로로 메뉴 조회

        Args:
            path: 메뉴 경로

        Returns:
            Menu 객체 또는 None
        """
        select_sql = f"""
        SELECT id, name, path, icon, parent_id, required_permission, "order", is_active
        FROM {self.TABLE_NAME}
        WHERE path = ?
        """

        try:
            result = self.duckdb.conn.execute(select_sql, (path,)).fetchone()
            if result:
                return self._row_to_menu(result)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get menu by path: {e}")
            raise

    def get_all(self, include_inactive: bool = False) -> List[Menu]:
        """
        모든 메뉴 조회

        Args:
            include_inactive: 비활성 메뉴 포함 여부

        Returns:
            Menu 리스트 (order 순으로 정렬)
        """
        where_clause = "" if include_inactive else "WHERE is_active = TRUE"
        select_sql = f"""
        SELECT id, name, path, icon, parent_id, required_permission, "order", is_active
        FROM {self.TABLE_NAME}
        {where_clause}
        ORDER BY "order" ASC, name ASC
        """

        try:
            results = self.duckdb.conn.execute(select_sql).fetchall()
            return [self._row_to_menu(row) for row in results]

        except Exception as e:
            self.logger.error(f"Failed to get all menus: {e}")
            raise

    def get_top_level_menus(self, include_inactive: bool = False) -> List[Menu]:
        """
        최상위 메뉴만 조회

        Args:
            include_inactive: 비활성 메뉴 포함 여부

        Returns:
            최상위 Menu 리스트
        """
        where_clauses = ["parent_id IS NULL"]
        if not include_inactive:
            where_clauses.append("is_active = TRUE")

        where_clause = " AND ".join(where_clauses)

        select_sql = f"""
        SELECT id, name, path, icon, parent_id, required_permission, "order", is_active
        FROM {self.TABLE_NAME}
        WHERE {where_clause}
        ORDER BY "order" ASC, name ASC
        """

        try:
            results = self.duckdb.conn.execute(select_sql).fetchall()
            return [self._row_to_menu(row) for row in results]

        except Exception as e:
            self.logger.error(f"Failed to get top level menus: {e}")
            raise

    def get_children(self, parent_id: int, include_inactive: bool = False) -> List[Menu]:
        """
        특정 메뉴의 하위 메뉴 조회

        Args:
            parent_id: 상위 메뉴 ID
            include_inactive: 비활성 메뉴 포함 여부

        Returns:
            하위 Menu 리스트
        """
        where_clauses = [f"parent_id = {parent_id}"]
        if not include_inactive:
            where_clauses.append("is_active = TRUE")

        where_clause = " AND ".join(where_clauses)

        select_sql = f"""
        SELECT id, name, path, icon, parent_id, required_permission, "order", is_active
        FROM {self.TABLE_NAME}
        WHERE {where_clause}
        ORDER BY "order" ASC, name ASC
        """

        try:
            results = self.duckdb.conn.execute(select_sql).fetchall()
            return [self._row_to_menu(row) for row in results]

        except Exception as e:
            self.logger.error(f"Failed to get children menus: {e}")
            raise

    def update(self, menu: Menu) -> Menu:
        """
        메뉴 정보 업데이트

        Args:
            menu: 업데이트할 Menu 객체 (id 필수)

        Returns:
            업데이트된 Menu 객체
        """
        if not menu.id:
            raise ValueError("Menu must have an ID to update")

        update_sql = f"""
        UPDATE {self.TABLE_NAME}
        SET name = ?,
            path = ?,
            icon = ?,
            parent_id = ?,
            required_permission = ?,
            "order" = ?,
            is_active = ?
        WHERE id = ?
        """

        params = (
            menu.name,
            menu.path,
            menu.icon,
            menu.parent_id,
            menu.required_permission,
            menu.order,
            menu.is_active,
            menu.id
        )

        try:
            self.duckdb.conn.execute(update_sql, params)
            self.logger.info(f"Updated menu: {menu.name}")
            return menu

        except Exception as e:
            self.logger.error(f"Failed to update menu: {e}")
            raise

    def delete(self, menu_id: int) -> bool:
        """
        메뉴 삭제

        Args:
            menu_id: 메뉴 ID

        Returns:
            삭제 성공 여부
        """
        delete_sql = f"""
        DELETE FROM {self.TABLE_NAME}
        WHERE id = ?
        """

        try:
            self.duckdb.conn.execute(delete_sql, (menu_id,))
            self.logger.info(f"Deleted menu id: {menu_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete menu: {e}")
            raise

    def _row_to_menu(self, row: tuple) -> Menu:
        """
        DB 행을 Menu 객체로 변환

        Args:
            row: (id, name, path, icon, parent_id, required_permission, order, is_active)

        Returns:
            Menu 객체
        """
        return Menu(
            id=row[0],
            name=row[1],
            path=row[2],
            icon=row[3],
            parent_id=row[4],
            required_permission=row[5] or "",
            order=row[6] or 0,
            is_active=row[7]
        )
