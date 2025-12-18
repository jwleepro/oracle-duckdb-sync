import duckdb
from oracle_duckdb_sync.config import Config


class DuckDBSource:
    def __init__(self, config: Config):
        self.config = config
        self.conn = duckdb.connect(self.config.duckdb_path)

    def disconnect(self):
        """Close the DuckDB connection"""
        if self.conn:
            self.conn.close()
        self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

    def __del__(self):
        """Ensure cleanup on garbage collection"""
        self.disconnect()

    def ping(self):
        return self.conn.execute("SELECT 1").fetchall()

    def ensure_database(self):
        """DuckDB는 파일 기반이므로 별도 DB 생성이 필요없음.
        호환성을 위해 빈 메서드로 유지."""
        pass

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in DuckDB
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            bool: True if table exists, False otherwise
        """
        query = f"""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = '{table_name}'
        """
        result = self.conn.execute(query).fetchone()
        return result[0] > 0 if result else False

    def execute(self, query: str, params=None):
        if params:
            return self.conn.execute(query, params).fetchall()
        return self.conn.execute(query).fetchall()

    def map_oracle_type(self, oracle_type: str) -> str:
        oracle_type = oracle_type.upper()
        if "NUMBER" in oracle_type:
            return "DOUBLE"
        if "VARCHAR" in oracle_type or "CHAR" in oracle_type:
            return "VARCHAR"
        if "DATE" in oracle_type:
            return "TIMESTAMP"
        if "TIMESTAMP" in oracle_type:
            return "TIMESTAMP"
        return "VARCHAR"

    def insert_batch(self, table: str, data: list):
        if not data:
            return 0
        placeholders = ", ".join(["?" for _ in data[0]])
        query = f"INSERT INTO {table} VALUES ({placeholders})"
        self.conn.executemany(query, data)
        return len(data)

    def build_create_table_query(self, table_name: str, columns: list, primary_key: str):
        col_defs = ", ".join([f"{name} {dtype}" for name, dtype in columns])
        return f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {col_defs},
            PRIMARY KEY ({primary_key})
        )
        """
