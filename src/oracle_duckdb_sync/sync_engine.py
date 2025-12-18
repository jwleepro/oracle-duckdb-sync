import time
import json
import os
import logging
from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.oracle_source import OracleSource
from oracle_duckdb_sync.duckdb_source import DuckDBSource
from oracle_duckdb_sync.logger import setup_logger

class SyncEngine:
    def __init__(self, config: Config):
        self.config = config
        self.oracle = OracleSource(config)
        self.duckdb = DuckDBSource(config)
        self.logger = setup_logger("sync_engine")


    def close(self):
        """Clean up all resources"""
        if hasattr(self, 'oracle'):
            self.oracle.disconnect()
        if hasattr(self, 'duckdb'):
            self.duckdb.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        self.close()

    def full_sync(self, oracle_table: str, duckdb_table: str, primary_key: str):
        """Perform full synchronization from Oracle to DuckDB
        
        Steps:
        1. Query Oracle table schema
        2. Map Oracle column types to DuckDB types
        3. Create table in DuckDB (if not exists)
        4. Sync all data in batches
        
        Args:
            oracle_table: Source Oracle table name
            duckdb_table: Target DuckDB table name
            primary_key: Primary key column name
        
        Returns:
            int: Total number of rows synchronized
        """
        # Step 1: Get Oracle table schema
        self.logger.info(f"Getting schema for table {oracle_table}")
        schema = self.oracle.get_table_schema(oracle_table)
        
        if not schema:
            raise ValueError(f"Table {oracle_table} not found or has no columns")
        
        # Step 2: Map Oracle types to DuckDB types
        duckdb_columns = []
        for col_name, oracle_type in schema:
            duckdb_type = self.duckdb.map_oracle_type(oracle_type)
            duckdb_columns.append((col_name, duckdb_type))
        
        # Step 3: Create table in DuckDB
        self.logger.info(f"Creating table {duckdb_table} in DuckDB")
        create_ddl = self.duckdb.build_create_table_query(
            duckdb_table, 
            duckdb_columns, 
            primary_key
        )
        self.duckdb.execute(create_ddl)
        
        # Step 4: Sync data
        self.logger.info(f"Starting full sync from {oracle_table} to {duckdb_table}")
        return self.sync_in_batches(oracle_table, duckdb_table)

    def incremental_sync(self, oracle_table: str, duckdb_table: str, column: str, last_value: str, retries: int = 3):
        query = self.oracle.build_incremental_query(oracle_table, column, last_value)
        last_exception = None
        for attempt in range(retries):
            try:
                return self._execute_sync(query, duckdb_table)
            except Exception as e:
                last_exception = e
                if attempt < retries - 1:
                    time.sleep(0.1)
                    continue
        raise last_exception

    def sync_in_batches(self, oracle_table: str, duckdb_table: str, batch_size: int = 10000, max_duration: int = 3600):
        query = f"SELECT * FROM {oracle_table}"
        return self._execute_sync(query, duckdb_table, batch_size, max_duration)

    def _execute_sync(self, query: str, duckdb_table: str, batch_size: int = 10000, max_duration: int = 3600):
        self.duckdb.ensure_database()
        
        # Check if target table exists
        if not self.duckdb.table_exists(duckdb_table):
            raise ValueError(
                f"Table '{duckdb_table}' does not exist in DuckDB. "
                f"Please run full_sync() first to create the table schema."
            )
        
        start_time = time.time()
        total_count = 0
        
        # Infinite loop prevention
        max_iterations = 10000
        iteration_count = 0
        
        while True:
            iteration_count += 1
            
            # Check max iterations
            if iteration_count > max_iterations:
                raise RuntimeError(f"Exceeded maximum iterations ({max_iterations})")
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > max_duration:
                raise TimeoutError(f"Sync exceeded maximum duration ({max_duration}s)")
            
            data = self.oracle.fetch_batch(query, batch_size=batch_size)
            if not data:
                break
            self.duckdb.insert_batch(duckdb_table, data)
            total_count += len(data)
            self._log_progress(duckdb_table, total_count, len(data))
            if len(data) < batch_size:
                break

        # Log statistics
        elapsed_time = time.time() - start_time
        self.logger.info(f"Sync completed: {total_count} rows processed in {elapsed_time:.2f} seconds")
        if elapsed_time > 0:
            rows_per_second = total_count / elapsed_time
            self.logger.info(f"Processing rate: {rows_per_second:.2f} rows/second")

        return total_count

    def _log_progress(self, table: str, total_count: int, batch_count: int):
        """Log sync progress"""
        self.logger.info(
            f"Sync progress - Table: {table}, Total rows: {total_count}, Batch size: {batch_count}"
        )

    def save_state(self, table_name: str, last_value: str, file_path: str = "sync_state.json"):
        state = {}
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    state = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, IOError):
                pass  # File doesn't exist or is corrupted, start fresh
        state[table_name] = last_value
        with open(file_path, "w") as f:
            json.dump(state, f)

    def load_state(self, table_name: str, file_path: str = "sync_state.json") -> str:
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r") as f:
                state = json.load(f)
                return state.get(table_name)
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            return None