import time
from typing import Optional

from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.database.oracle_source import OracleSource
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.state.file_manager import StateFileManager


class SyncEngine:
    def __init__(self, config: Config):
        self.config = config
        self.oracle = OracleSource(config)
        self.duckdb = DuckDBSource(config)
        self.logger = setup_logger("sync_engine")
        self.state_manager = StateFileManager(self.logger)

    @staticmethod
    def map_oracle_type(oracle_type: str) -> str:
        """Map Oracle data type to DuckDB data type.

        This method belongs to SyncEngine (data sync layer) because:
        - Type mapping is only needed during data synchronization
        - DuckDB should not have Oracle-specific knowledge
        - After sync, DuckDB operates independently of Oracle

        Args:
            oracle_type: Oracle data type (e.g., "NUMBER", "VARCHAR2(100)")

        Returns:
            DuckDB data type (e.g., "DOUBLE", "VARCHAR", "TIMESTAMP")
        """
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

    def _prepare_sync(self, oracle_table: str, duckdb_table: str):
        """Extract common schema preparation logic used by full_sync and test_sync.

        This method handles:
        1. Oracle connection validation
        2. Schema retrieval from Oracle
        3. Type mapping from Oracle to DuckDB

        Args:
            oracle_table: Source Oracle table name
            duckdb_table: Target DuckDB table name (unused in current implementation but kept for future use)

        Returns:
            tuple: (schema, duckdb_columns) where:
                - schema: List of (column_name, oracle_type) tuples
                - duckdb_columns: List of (column_name, duckdb_type) tuples

        Raises:
            ValueError: If Oracle is not connected or table not found
        """
        # Ensure Oracle connection is established
        if not self.oracle.conn:
            self.oracle.connect()

        # Get Oracle table schema
        self.logger.info(f"Getting schema for table {oracle_table}")
        schema = self.oracle.get_table_schema(oracle_table)

        if not schema:
            raise ValueError(f"Table {oracle_table} not found or has no columns")

        # Map Oracle types to DuckDB types
        duckdb_columns = [
            (col_name, self.map_oracle_type(oracle_type))
            for col_name, oracle_type in schema
        ]

        return schema, duckdb_columns

    def full_sync(self, oracle_table_name: str, duckdb_table: str, primary_key: str):
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
        # Step 1 & 2: Get schema and prepare columns
        schema, duckdb_columns = self._prepare_sync(oracle_table_name, duckdb_table)

        # Step 3: Create table in DuckDB
        self.logger.info(f"Creating table {duckdb_table} in DuckDB")
        create_ddl = self.duckdb.build_create_table_query(
            duckdb_table,
            duckdb_columns,
            primary_key
        )
        self.duckdb.execute(create_ddl)

        # Step 4: Sync data
        self.logger.info(f"Starting full sync from {oracle_table_name} to {duckdb_table}")
        return self.sync_in_batches(oracle_table_name, duckdb_table)

    def test_sync(self, oracle_table_name: str, duckdb_table: str, primary_key: str, row_limit: int = 100000):
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
        # Step 1 & 2: Get schema and prepare columns
        schema, duckdb_columns = self._prepare_sync(oracle_table_name, duckdb_table)

        # Step 3: Create table in DuckDB (drop if exists for test)
        self.logger.info(f"Creating table {duckdb_table} in DuckDB")

        # Drop test table if it exists to avoid duplicate key errors
        if self.duckdb.table_exists(duckdb_table):
            self.logger.info(f"Dropping existing test table {duckdb_table}")
            self.duckdb.execute(f"DROP TABLE IF EXISTS {duckdb_table}")

        # Create table WITHOUT primary key for test (faster inserts)
        col_defs = ", ".join([f"{name} {duckdb_type}" for name, duckdb_type in duckdb_columns])
        create_ddl = f"CREATE TABLE {duckdb_table} ({col_defs})"
        self.logger.info("Creating test table WITHOUT PRIMARY KEY for faster inserts")
        self.duckdb.execute(create_ddl)

        # Step 4: Sync limited data with proper row limit enforcement
        if row_limit is None:
            row_limit = self.config.test_sync_default_row_limit
        self.logger.info(f"Starting test sync from {oracle_table_name} to {duckdb_table} (limit: {row_limit} rows)")
        return self._execute_limited_sync(oracle_table_name, duckdb_table, row_limit, duckdb_columns, batch_size=self.config.sync_batch_size)

    def incremental_sync(self, oracle_table_name: str, duckdb_table: str, column: str, last_value: str, primary_key: Optional[str] = None, retries: Optional[int] = None):
        """Perform incremental synchronization from Oracle to DuckDB

        Incremental sync uses INSERT only (no UPSERT) because:
        - New data from Oracle should not have duplicates
        - State is only updated on successful completion
        - Failed syncs can be retried without duplication

        Args:
            oracle_table_name: Source Oracle table name
            duckdb_table: Target DuckDB table name
            column: Timestamp column for incremental detection
            last_value: Last synchronized timestamp value
            primary_key: Not used in incremental sync (always None for INSERT-only)
            retries: Number of retry attempts on failure

        Returns:
            int: Total number of rows synchronized
        """
        # Ensure Oracle connection is established
        if not self.oracle.conn:
            self.oracle.connect()

        if retries is None:
            retries = self.config.sync_retry_attempts
        query = self.oracle.build_incremental_query(oracle_table_name, column, last_value)
        last_exception = None
        for attempt in range(retries):
            try:
                # Use INSERT only (primary_key=None) for incremental sync
                total_rows = self._execute_sync(query, duckdb_table, primary_key=None)

                # Only save state if sync was successful
                if total_rows >= 0:
                    # Get the latest timestamp from DuckDB after successful insert
                    max_time_query = f"SELECT MAX({column}) FROM {duckdb_table}"
                    result = self.duckdb.conn.execute(max_time_query).fetchone()

                    if result and result[0]:
                        new_last_value = str(result[0])
                        self.save_state(oracle_table_name, new_last_value)
                        self.logger.info(f"Incremental sync state saved: {oracle_table_name} -> {new_last_value}")

                return total_rows
            except Exception as e:
                last_exception = e
                if attempt < retries - 1:
                    self.logger.warning(f"Incremental sync attempt {attempt + 1} failed, retrying...")
                    time.sleep(self.config.sync_retry_delay_seconds)
                    continue

        # If all retries failed, do NOT save state
        self.logger.error(f"Incremental sync failed after {retries} attempts. State NOT updated.")
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Incremental sync failed after {retries} attempts")

    def sync_in_batches(self, oracle_table_name: str, duckdb_table: str, batch_size: Optional[int] = None, max_duration: Optional[int] = None):
        if batch_size is None:
            batch_size = self.config.sync_batch_size
        if max_duration is None:
            max_duration = self.config.sync_max_duration_seconds
        query = f"SELECT * FROM {oracle_table_name}"
        return self._execute_sync(query, duckdb_table, batch_size, max_duration)

    def _execute_sync(self, query: str, duckdb_table: str, batch_size: Optional[int] = None, max_duration: Optional[int] = None, primary_key: Optional[str] = None):
        """Execute sync query with optional UPSERT support

        Args:
            query: SQL query to execute
            duckdb_table: Target DuckDB table name
            batch_size: Number of rows per batch
            max_duration: Maximum duration in seconds
            primary_key: Primary key column for UPSERT (optional)

        Returns:
            int: Total number of rows synchronized
        """
        if batch_size is None:
            batch_size = self.config.sync_batch_size
        if max_duration is None:
            max_duration = self.config.sync_max_duration_seconds
        self.duckdb.ensure_database()

        # Check if target table exists
        if not self.duckdb.table_exists(duckdb_table):
            raise ValueError(
                f"Table '{duckdb_table}' does not exist in DuckDB. "
                f"Please run full_sync() first to create the table schema."
            )

        start_time = time.time()
        total_count = 0
        batch_number = 0
        # Prevent infinite loops (configurable safety limit)
        max_iterations = self.config.sync_max_iterations

        # Use fetch_generator for thread-safe iteration
        for data in self.oracle.fetch_generator(query, batch_size=batch_size):
            batch_start_time = time.time()
            batch_number += 1

            # Check max iterations
            if batch_number > max_iterations:
                raise RuntimeError(f"Exceeded maximum iterations ({max_iterations})")

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > max_duration:
                raise TimeoutError(f"Sync exceeded maximum duration ({max_duration}s)")

            self.logger.info(f"[BATCH {batch_number}] Fetched {len(data)} rows (Total so far: {total_count})")

            # Use UPSERT if primary_key is provided
            if primary_key:
                # Get column names from table schema
                schema_query = f"DESCRIBE {duckdb_table}"
                schema_result = self.duckdb.conn.execute(schema_query).fetchall()
                column_names = [row[0] for row in schema_result]

                self.duckdb.insert_batch(duckdb_table, data, column_names=column_names, primary_key=primary_key, logger=self.logger)
            else:
                self.duckdb.insert_batch(duckdb_table, data)

            total_count += len(data)

            # Log batch timing
            batch_elapsed = time.time() - batch_start_time
            self.logger.info(f"[BATCH {batch_number}] Processed {len(data)} rows in {batch_elapsed:.3f}s (Total: {total_count})")

            self._log_progress(duckdb_table, total_count, len(data))

        # Log statistics
        elapsed_time = time.time() - start_time
        self.logger.info(f"Sync completed: {total_count} rows processed in {elapsed_time:.2f} seconds")
        if elapsed_time > 0:
            rows_per_second = total_count / elapsed_time
            self.logger.info(f"Processing rate: {rows_per_second:.2f} rows/second")

        return total_count

    def _validate_sync_preconditions(self, duckdb_table: str) -> None:
        """Validate database connections and table existence.

        Args:
            duckdb_table: Target DuckDB table name

        Raises:
            ValueError: If table doesn't exist in DuckDB
        """
        self.duckdb.ensure_database()

        # Check if target table exists
        if not self.duckdb.table_exists(duckdb_table):
            raise ValueError(
                f"Table '{duckdb_table}' does not exist in DuckDB. "
                f"Please run full_sync() first to create the table schema."
            )

        # Ensure Oracle connection
        if not self.oracle.conn:
            self.oracle.connect()

    def _log_sync_summary(self, total_count: int, row_limit: int, elapsed_time: float) -> None:
        """Log sync operation summary statistics.

        Args:
            total_count: Total number of rows processed
            row_limit: Maximum row limit that was set
            elapsed_time: Total time taken for sync operation
        """
        self.logger.info("=" * 80)
        self.logger.info("[SUMMARY] Test sync completed!")
        self.logger.info(f"[SUMMARY] Total rows processed: {total_count}")
        self.logger.info(f"[SUMMARY] Row limit: {row_limit}")
        self.logger.info(f"[SUMMARY] Total time: {elapsed_time:.2f} seconds")
        if elapsed_time > 0:
            rows_per_second = total_count / elapsed_time
            self.logger.info(f"[SUMMARY] Processing rate: {rows_per_second:.2f} rows/second")
        self.logger.info("=" * 80)

    def _fetch_batch_from_oracle(self, cursor, batch_size: int, batch_number: int) -> list:
        """Fetch a batch of rows from Oracle cursor.

        Args:
            cursor: Oracle cursor to fetch from
            batch_size: Number of rows to fetch
            batch_number: Current batch number for logging

        Returns:
            list: Fetched rows from Oracle
        """
        self.logger.info("[ORACLE] Fetching batch from Oracle...")
        fetch_start = time.time()
        rows = cursor.fetchmany(batch_size)
        fetch_time = time.time() - fetch_start

        if not rows:
            self.logger.info("[ORACLE] No more rows to fetch. End of data.")
        else:
            self.logger.info(f"[ORACLE] Fetched {len(rows)} rows from Oracle in {fetch_time:.2f}s")

        return rows

    def _convert_datetime_values(self, rows: list) -> list:
        """Convert Oracle datetime objects to serializable format.

        Args:
            rows: List of rows containing Oracle datetime objects

        Returns:
            list: Rows with datetime objects converted to strings
        """
        self.logger.info("[PROCESS] Converting datetime objects...")
        from oracle_duckdb_sync.database.oracle_source import datetime_handler
        data = [tuple(datetime_handler(v) for v in row) for row in rows]
        self.logger.info(f"[PROCESS] Converted {len(data)} rows")
        return data

    def _insert_batch_to_duckdb(self, duckdb_table: str, data: list, duckdb_columns: list) -> None:
        """Insert a batch of data into DuckDB table.

        Args:
            duckdb_table: Target DuckDB table name
            data: List of tuples containing row data
            duckdb_columns: List of (column_name, duckdb_type) tuples
        """
        # Extract column names for Pandas DataFrame
        column_names = [col_name for col_name, _ in duckdb_columns]

        # Insert batch with Pandas DataFrame (100x faster)
        self.logger.info(f"[DUCKDB] Starting insert of {len(data)} rows into DuckDB table '{duckdb_table}'...")
        insert_start = time.time()
        self.duckdb.insert_batch(duckdb_table, data, column_names=column_names, logger=self.logger)
        insert_time = time.time() - insert_start
        self.logger.info(f"[DUCKDB] Total insert completed in {insert_time:.2f}s")

    def _process_batches_with_limit(
        self,
        cursor,
        duckdb_table: str,
        duckdb_columns: list,
        row_limit: int,
        batch_size: int,
        max_duration: int,
        start_time: float
    ) -> int:
        """Process and insert batches of data from Oracle cursor to DuckDB.

        Args:
            cursor: Oracle cursor with executed query
            duckdb_table: Target DuckDB table name
            duckdb_columns: List of (column_name, duckdb_type) tuples
            row_limit: Maximum number of rows to process
            batch_size: Number of rows per batch
            max_duration: Maximum duration in seconds
            start_time: Start time of sync operation

        Returns:
            int: Total number of rows processed
        """
        total_count = 0
        batch_number = 0

        # Fetch and insert in batches, respecting the row_limit
        while total_count < row_limit:
            batch_start_time = time.time()
            batch_number += 1

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > max_duration:
                raise TimeoutError(f"Sync exceeded maximum duration ({max_duration}s)")

            # Calculate how many rows to fetch in this batch
            remaining = row_limit - total_count
            current_batch_size = min(batch_size, remaining)

            self.logger.info(f"[BATCH {batch_number}] Preparing to fetch {current_batch_size} rows (total so far: {total_count}, remaining: {remaining})")

            # Fetch batch from cursor
            rows = self._fetch_batch_from_oracle(cursor, current_batch_size, batch_number)

            if not rows:
                break

            # Convert datetime objects
            data = self._convert_datetime_values(rows)

            # Insert batch to DuckDB
            self._insert_batch_to_duckdb(duckdb_table, data, duckdb_columns)

            total_count += len(data)

            # Log batch timing
            batch_elapsed = time.time() - batch_start_time
            self.logger.info(f"[BATCH {batch_number}] Processed {len(data)} rows in {batch_elapsed:.3f}s (Total: {total_count})")
            self.logger.info(f"[PROGRESS] Total rows processed: {total_count}/{row_limit} ({total_count/row_limit*100:.1f}%)")
            self._log_progress(duckdb_table, total_count, len(data))

            # CRITICAL: Stop if we reached the limit
            if total_count >= row_limit:
                self.logger.info(f"[COMPLETE] Reached row limit: {total_count} >= {row_limit}. Stopping.")
                break

            # Stop if we got less than requested (end of data)
            if len(data) < current_batch_size:
                self.logger.info(f"[COMPLETE] Got less than requested ({len(data)} < {current_batch_size}). End of data.")
                break

        return total_count

    def _build_sync_query(self, oracle_table: str, row_limit: int) -> str:
        """Build optimized SELECT query with optional row limit.

        Args:
            oracle_table: Source Oracle table name
            row_limit: Maximum number of rows to fetch

        Returns:
            str: SQL query string with ROWNUM limit
        """
        # Oracle requires subquery for proper ROWNUM limiting
        return f"SELECT * FROM (SELECT * FROM {oracle_table}) WHERE ROWNUM <= {row_limit}"

    def _execute_limited_sync(self, oracle_table: str, duckdb_table: str, row_limit: int, duckdb_columns: list, batch_size: Optional[int] = None, max_duration: Optional[int] = None):
        """Execute sync with strict row limit enforcement

        Args:
            oracle_table: Source Oracle table name
            duckdb_table: Target DuckDB table name
            row_limit: Maximum number of rows to sync
            duckdb_columns: List of (column_name, duckdb_type) tuples
            batch_size: Number of rows per batch
            max_duration: Maximum duration in seconds

        Returns:
            int: Total number of rows synchronized
        """
        if batch_size is None:
            batch_size = self.config.sync_batch_size
        if max_duration is None:
            max_duration = self.config.sync_max_duration_seconds
        self._validate_sync_preconditions(duckdb_table)

        self.logger.info("=" * 80)
        self.logger.info(f"Starting limited sync: {oracle_table} -> {duckdb_table}")
        self.logger.info(f"Row limit: {row_limit}, Batch size: {batch_size}")
        self.logger.info("=" * 80)

        start_time = time.time()
        total_count = 0

        # Build query with ROWNUM limit
        query = self._build_sync_query(oracle_table, row_limit)

        # Create a fresh cursor for this limited sync
        cursor = self.oracle.conn.cursor()

        try:
            # Execute query once
            self.logger.info(f"[ORACLE] Executing query: {query}")
            cursor.execute(query)
            self.logger.info("[ORACLE] Query executed successfully")

            total_count = self._process_batches_with_limit(
                cursor, duckdb_table, duckdb_columns,
                row_limit, batch_size, max_duration, start_time
            )

        finally:
            # Always close the cursor
            self.logger.info("[CLEANUP] Closing Oracle cursor...")
            cursor.close()
            self.logger.info("[CLEANUP] Cursor closed")

        # Log statistics
        elapsed_time = time.time() - start_time
        self._log_sync_summary(total_count, row_limit, elapsed_time)

        return total_count

    def _log_progress(self, table: str, total_count: int, batch_count: int):
        """Log sync progress"""
        self.logger.info(
            f"Sync progress - Table: {table}, Total rows: {total_count}, Batch size: {batch_count}"
        )

    def save_state(self, table_name: str, last_value: str, file_path: Optional[str] = None):
        """Save sync state for a table using StateFileManager"""
        if file_path is None:
            file_path = self.config.sync_state_path
        # Load existing state
        state = self.state_manager.load_json(file_path, default_data={})

        # Update state for this table
        state[table_name] = last_value

        # Save updated state
        self.state_manager.save_json(file_path, state)

    def load_state(self, table_name: str, file_path: Optional[str] = None) -> Optional[str]:
        """Load sync state for a table using StateFileManager"""
        if file_path is None:
            file_path = self.config.sync_state_path
        state = self.state_manager.load_json(file_path, default_data={})
        return state.get(table_name)


    def save_schema_mapping(self, table_name: str, schema: dict, version: str, file_path: Optional[str] = None):
        """Save schema mapping configuration with version tracking

        Args:
            table_name: Name of the table
            schema: Schema configuration dictionary
            version: Version string (e.g., "1.0", "2.0")
            file_path: Path to the schema mappings file
        """
        if file_path is None:
            file_path = self.config.schema_mapping_path
        # Load existing mappings
        mappings = self.state_manager.load_json(file_path, default_data={})

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
        self.state_manager.save_json(file_path, mappings)

    def load_schema_mapping(self, table_name: str, version: Optional[str] = None, file_path: Optional[str] = None) -> dict:
        """Load schema mapping configuration

        Args:
            table_name: Name of the table
            version: Specific version to load (default: latest)
            file_path: Path to the schema mappings file

        Returns:
            dict: Schema mapping with version info, or None if not found
        """
        if file_path is None:
            file_path = self.config.schema_mapping_path
        # Load mappings using StateFileManager
        mappings = self.state_manager.load_json(file_path, default_data={})

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

    def get_schema_versions(self, table_name: str, file_path: Optional[str] = None) -> list:
        """Get list of all versions for a table's schema mapping

        Args:
            table_name: Name of the table
            file_path: Path to the schema mappings file

        Returns:
            list: List of version strings, or empty list if not found
        """
        if file_path is None:
            file_path = self.config.schema_mapping_path
        mappings = self.state_manager.load_json(file_path, default_data={})

        if table_name not in mappings:
            return []

        versions = list(mappings[table_name].get("versions", {}).keys())
        return versions


    def create_state_checkpoint(self, file_path: Optional[str] = None) -> dict:
        """Create a checkpoint snapshot of current sync state

        Args:
            file_path: Path to the state file

        Returns:
            dict: Copy of current state, or empty dict if file doesn't exist
        """
        if file_path is None:
            file_path = self.config.sync_state_path
        state = self.state_manager.load_json(file_path, default_data={})
        # Return a deep copy to prevent modification
        return dict(state)

    def rollback_state(self, checkpoint: dict, file_path: Optional[str] = None) -> bool:
        """Rollback sync state to a previous checkpoint

        Args:
            checkpoint: Checkpoint state dictionary to restore
            file_path: Path to the state file

        Returns:
            bool: True if rollback succeeded, False otherwise
        """
        if file_path is None:
            file_path = self.config.sync_state_path
        return self.state_manager.save_json(file_path, checkpoint)

    def save_partial_progress(self, table_name: str, rows_processed: int, last_row_id: int,
                             file_path: Optional[str] = None):
        """Save partial progress during sync operation

        Args:
            table_name: Name of the table being synced
            rows_processed: Number of rows processed so far
            last_row_id: ID of the last row processed
            file_path: Path to the progress file
        """
        if file_path is None:
            file_path = self.config.sync_progress_path
        # Load existing progress
        progress = self.state_manager.load_json(file_path, default_data={})

        import datetime
        progress[table_name] = {
            "rows_processed": rows_processed,
            "last_row_id": last_row_id,
            "timestamp": datetime.datetime.now().isoformat()
        }

        # Save updated progress
        self.state_manager.save_json(file_path, progress)

    def load_partial_progress(self, table_name: str, file_path: Optional[str] = None) -> dict:
        """Load partial progress for a table

        Args:
            table_name: Name of the table
            file_path: Path to the progress file

        Returns:
            dict: Progress info with rows_processed, last_row_id, timestamp, or None
        """
        if file_path is None:
            file_path = self.config.sync_progress_path
        progress = self.state_manager.load_json(file_path, default_data={})
        return progress.get(table_name)

    def clear_partial_progress(self, table_name: str, file_path: Optional[str] = None):
        """Clear partial progress for a table after successful completion

        Args:
            table_name: Name of the table
            file_path: Path to the progress file
        """
        if file_path is None:
            file_path = self.config.sync_progress_path
        # Load existing progress
        progress = self.state_manager.load_json(file_path, default_data={})

        # Remove the table from progress
        if table_name in progress:
            del progress[table_name]

        # Write back
        self.state_manager.save_json(file_path, progress)
