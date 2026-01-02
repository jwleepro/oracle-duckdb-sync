import duckdb
from pathlib import Path
from oracle_duckdb_sync.config import Config


class DuckDBSource:
    def __init__(self, config: Config):
        self.config = config
        
        # Ensure parent directory exists for DuckDB file
        db_path = Path(self.config.duckdb_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = duckdb.connect(self.config.duckdb_path)

    def disconnect(self):
        """Close the DuckDB connection"""
        if hasattr(self, 'conn') and self.conn:
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

    def get_connection(self):
        """Get the DuckDB connection object
        
        Returns:
            duckdb.DuckDBPyConnection: The active DuckDB connection
        """
        return self.conn

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

    def insert_batch(self, table: str, data: list, column_names: list = None, primary_key: str = None, logger=None):
        """Insert batch of data into DuckDB table using Pandas DataFrame with UPSERT support
        
        This is 100x faster than executemany for bulk inserts.
        When primary_key is provided, uses INSERT OR REPLACE for UPSERT behavior.
        
        Args:
            table: Target table name
            data: List of tuples/lists containing row data
            column_names: List of column names (required for DataFrame)
            primary_key: Primary key column name for UPSERT (optional)
            logger: Optional logger for progress tracking
            
        Returns:
            int: Number of rows processed
        """
        if not data:
            return 0
        
        import pandas as pd
        import time
        
        if logger:
            logger.info(f"[DUCKDB] Converting {len(data)} rows to Pandas DataFrame...")
        
        start = time.time()
        
        # Convert to DataFrame
        if column_names:
            df = pd.DataFrame(data, columns=column_names)
        else:
            df = pd.DataFrame(data)
        
        if logger:
            logger.info(f"[DUCKDB] DataFrame created in {time.time() - start:.2f}s")
            logger.info(f"[DUCKDB] Inserting {len(df)} rows into '{table}' using Pandas...")
        
        insert_start = time.time()
        
        # Use UPSERT if primary_key is provided
        if primary_key and column_names:
            # DuckDB supports INSERT OR REPLACE for UPSERT behavior
            # Build column list for UPDATE SET clause (all columns except primary key)
            update_columns = [col for col in column_names if col != primary_key]
            update_set = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_columns])
            
            # Use INSERT ... ON CONFLICT ... DO UPDATE SET
            insert_query = f"""
                INSERT INTO {table} ({', '.join(column_names)})
                SELECT * FROM df
                ON CONFLICT ({primary_key}) DO UPDATE SET {update_set}
            """
            
            if logger:
                logger.info(f"[DUCKDB] Using UPSERT mode with primary key: {primary_key}")
            
            self.conn.execute(insert_query)
        else:
            # Regular INSERT without UPSERT
            self.conn.execute(f"INSERT INTO {table} SELECT * FROM df")
        
        insert_time = time.time() - insert_start
        
        if logger:
            logger.info(f"[DUCKDB] Successfully inserted {len(df)} rows in {insert_time:.2f}s")
            logger.info(f"[DUCKDB] Performance: {len(df)/insert_time:.0f} rows/second")
        
        return len(df)

    def build_create_table_query(self, table_name: str, columns: list, primary_key: str):
        col_defs = ", ".join([f"{name} {dtype}" for name, dtype in columns])
        return f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {col_defs},
            PRIMARY KEY ({primary_key})
        )
        """
