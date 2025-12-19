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
        # Ensure Oracle connection is established
        if not self.oracle.conn:
            self.oracle.connect()
        
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

    def test_sync(self, oracle_table: str, duckdb_table: str, primary_key: str, row_limit: int = 100000):
        """Perform test synchronization with limited rows from Oracle to DuckDB
        
        This is useful for testing the sync process with a large dataset before
        running a full sync. It creates the table schema and syncs only the
        specified number of rows.
        
        Steps:
        1. Query Oracle table schema
        2. Map Oracle column types to DuckDB types
        3. Create table in DuckDB (if not exists)
        4. Sync limited data in batches
        
        Args:
            oracle_table: Source Oracle table name
            duckdb_table: Target DuckDB table name
            primary_key: Primary key column name
            row_limit: Maximum number of rows to sync (default: 100000)
        
        Returns:
            int: Total number of rows synchronized
        """
        # Ensure Oracle connection is established
        if not self.oracle.conn:
            self.oracle.connect()
        
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
        
        # Step 4: Sync limited data
        self.logger.info(f"Starting test sync from {oracle_table} to {duckdb_table} (limit: {row_limit} rows)")
        query = f"SELECT * FROM {oracle_table} WHERE ROWNUM <= {row_limit}"
        return self._execute_sync(query, duckdb_table, batch_size=10000)

    def incremental_sync(self, oracle_table: str, duckdb_table: str, column: str, last_value: str, retries: int = 3):
        # Ensure Oracle connection is established
        if not self.oracle.conn:
            self.oracle.connect()
        
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


    def save_schema_mapping(self, table_name: str, schema: dict, version: str, file_path: str = "schema_mappings.json"):
        """Save schema mapping configuration with version tracking
        
        Args:
            table_name: Name of the table
            schema: Schema configuration dictionary
            version: Version string (e.g., "1.0", "2.0")
            file_path: Path to the schema mappings file
        """
        mappings = {}
        
        # Load existing mappings if file exists
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    mappings = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, IOError):
                pass  # File doesn't exist or is corrupted, start fresh
        
        # Initialize table entry if it doesn't exist
        if table_name not in mappings:
            mappings[table_name] = {"versions": {}}
        
        # Save the schema with version and timestamp
        import datetime
        mappings[table_name]["versions"][version] = {
            "schema": schema,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Update latest version pointer
        mappings[table_name]["latest_version"] = version
        
        # Write to file
        with open(file_path, "w") as f:
            json.dump(mappings, f, indent=2)

    def load_schema_mapping(self, table_name: str, version: str = None, file_path: str = "schema_mappings.json") -> dict:
        """Load schema mapping configuration
        
        Args:
            table_name: Name of the table
            version: Specific version to load (default: latest)
            file_path: Path to the schema mappings file
            
        Returns:
            dict: Schema mapping with version info, or None if not found
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r") as f:
                mappings = json.load(f)
            
            # Check if table exists in mappings
            if table_name not in mappings:
                return None
            
            table_mappings = mappings[table_name]
            
            # Determine which version to load
            if version is None:
                # Load latest version
                version = table_mappings.get("latest_version")
                if version is None:
                    return None
            
            # Check if version exists
            if version not in table_mappings.get("versions", {}):
                return None
            
            version_data = table_mappings["versions"][version]
            
            return {
                "version": version,
                "schema": version_data["schema"],
                "timestamp": version_data.get("timestamp")
            }
            
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            return None

    def get_schema_versions(self, table_name: str, file_path: str = "schema_mappings.json") -> list:
        """Get list of all versions for a table's schema mapping
        
        Args:
            table_name: Name of the table
            file_path: Path to the schema mappings file
            
        Returns:
            list: List of version strings, or empty list if not found
        """
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, "r") as f:
                mappings = json.load(f)
            
            if table_name not in mappings:
                return []
            
            versions = list(mappings[table_name].get("versions", {}).keys())
            return versions
            
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            return []


    def create_state_checkpoint(self, file_path: str = "sync_state.json") -> dict:
        """Create a checkpoint snapshot of current sync state
        
        Args:
            file_path: Path to the state file
            
        Returns:
            dict: Copy of current state, or empty dict if file doesn't exist
        """
        if not os.path.exists(file_path):
            return {}
        
        try:
            with open(file_path, "r") as f:
                state = json.load(f)
                # Return a deep copy to prevent modification
                return dict(state)
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            return {}

    def rollback_state(self, checkpoint: dict, file_path: str = "sync_state.json") -> bool:
        """Rollback sync state to a previous checkpoint
        
        Args:
            checkpoint: Checkpoint state dictionary to restore
            file_path: Path to the state file
            
        Returns:
            bool: True if rollback succeeded, False otherwise
        """
        try:
            with open(file_path, "w") as f:
                json.dump(checkpoint, f)
            return True
        except (IOError, OSError) as e:
            self.logger.error(f"Failed to rollback state: {e}")
            return False

    def save_partial_progress(self, table_name: str, rows_processed: int, last_row_id: int, 
                             file_path: str = "sync_progress.json"):
        """Save partial progress during sync operation
        
        Args:
            table_name: Name of the table being synced
            rows_processed: Number of rows processed so far
            last_row_id: ID of the last row processed
            file_path: Path to the progress file
        """
        progress = {}
        
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    progress = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, IOError):
                pass
        
        import datetime
        progress[table_name] = {
            "rows_processed": rows_processed,
            "last_row_id": last_row_id,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        with open(file_path, "w") as f:
            json.dump(progress, f)

    def load_partial_progress(self, table_name: str, file_path: str = "sync_progress.json") -> dict:
        """Load partial progress for a table
        
        Args:
            table_name: Name of the table
            file_path: Path to the progress file
            
        Returns:
            dict: Progress info with rows_processed, last_row_id, timestamp, or None
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r") as f:
                progress = json.load(f)
                return progress.get(table_name)
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            return None

    def clear_partial_progress(self, table_name: str, file_path: str = "sync_progress.json"):
        """Clear partial progress for a table after successful completion
        
        Args:
            table_name: Name of the table
            file_path: Path to the progress file
        """
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, "r") as f:
                progress = json.load(f)
            
            # Remove the table from progress
            if table_name in progress:
                del progress[table_name]
            
            # Write back
            with open(file_path, "w") as f:
                json.dump(progress, f)
                
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            pass
