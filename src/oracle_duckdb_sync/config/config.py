import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

@dataclass
class Config:
    oracle_host: str
    oracle_port: int
    oracle_service_name: str
    oracle_user: str
    oracle_password: str

    duckdb_path: str
    duckdb_database: str = "main"
    
    # Oracle Client settings
    oracle_client_directories: List[str] = None
    
    # Sync target table configuration
    sync_oracle_schema: str = ""
    sync_oracle_table: str = ""
    sync_duckdb_table: str = ""
    sync_primary_key: str = "ID"
    sync_time_column: str = "TIMESTAMP_COL"
    
    # DuckDB specific time column (separates Oracle schema concerns from DuckDB queries)
    duckdb_time_column: str = "TIMESTAMP_COL"

    # Sync performance settings
    sync_batch_size: int = 10000
    oracle_fetch_batch_size: int = 10000
    sync_max_duration_seconds: int = 3600
    test_sync_default_row_limit: int = 100000
    default_sync_start_time: str = "2020-01-01 00:00:00"

    # Progress reporting
    progress_refresh_interval_seconds: float = 0.5

    # Type detection threshold
    type_detection_threshold: float = 0.9

    # Retry settings
    sync_retry_attempts: int = 3
    sync_retry_delay_seconds: float = 0.1

    # Infinite loop prevention (safety limit: ~100M rows with default batch_size=10000)
    sync_max_iterations: int = 10000

    # State file paths
    state_directory: str = "./data"
    sync_state_file: str = "sync_state.json"
    schema_mapping_file: str = "schema_mappings.json"
    sync_progress_file: str = "sync_progress.json"

    @property
    def oracle_full_table_name(self) -> str:
        """스키마와 테이블명을 합친 전체 Oracle 테이블명 반환"""
        if self.sync_oracle_schema:
            return f"{self.sync_oracle_schema}.{self.sync_oracle_table}"
        return self.sync_oracle_table

    @property
    def sync_state_path(self) -> str:
        return os.path.join(self.state_directory, self.sync_state_file)

    @property
    def schema_mapping_path(self) -> str:
        return os.path.join(self.state_directory, self.schema_mapping_file)

    @property
    def sync_progress_path(self) -> str:
        return os.path.join(self.state_directory, self.sync_progress_file)

def load_config(load_dotenv_file: bool = True) -> Config:
    if load_dotenv_file:
        load_dotenv()

    # 필수 변수 (호스트, 계정 정보 등)
    required_vars = [
        "ORACLE_HOST", "ORACLE_SERVICE_NAME",
        "ORACLE_USER", "ORACLE_PASSWORD",
        "DUCKDB_PATH"
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required configuration: {missing[0]}")

    # Validate and convert oracle_port
    try:
        oracle_port = int(os.getenv("ORACLE_PORT", "1521"))
    except ValueError as e:
        raise ValueError(f"ORACLE_PORT must be a valid integer: {os.getenv('ORACLE_PORT')}") from e
    
    # Validate port range (1-65535)
    if not (1 <= oracle_port <= 65535):
        raise ValueError(f"ORACLE_PORT must be between 1 and 65535, got: {oracle_port}")

    # Get sync table configuration
    sync_oracle_table = os.getenv("SYNC_ORACLE_TABLE", "")
    sync_duckdb_table = os.getenv("SYNC_DUCKDB_TABLE", "")
    
    # If duckdb table not specified, use oracle table name in lowercase without schema
    if not sync_duckdb_table and sync_oracle_table:
        sync_duckdb_table = sync_oracle_table.lower()
    
    # Get DuckDB time column - REQUIRED configuration
    duckdb_time_column = os.getenv("DUCKDB_TIME_COLUMN")
    if not duckdb_time_column:
        raise ValueError(
            "DUCKDB_TIME_COLUMN must be explicitly configured in .env file. "
            "This specifies the time column name in DuckDB for queries and aggregations. "
            "Example: DUCKDB_TIME_COLUMN=CREATE_TIME"
        )

    # Parse Oracle Client directories
    oracle_client_dirs_env = os.getenv("ORACLE_CLIENT_DIRECTORIES")
    if oracle_client_dirs_env:
        oracle_client_directories = [d.strip() for d in oracle_client_dirs_env.split(",") if d.strip()]
    else:
        # Default fallback paths for Windows
        oracle_client_directories = [
            r'D:\instantclient_23_0',
            r'C:\instantclient_23_0',
            r'D:\oracle\instantclient',
            r'C:\oracle\instantclient'
        ]

    return Config(
        oracle_host=os.getenv("ORACLE_HOST"),
        oracle_port=oracle_port,
        oracle_service_name=os.getenv("ORACLE_SERVICE_NAME"),
        oracle_user=os.getenv("ORACLE_USER"),
        oracle_password=os.getenv("ORACLE_PASSWORD"),

        duckdb_path=os.getenv("DUCKDB_PATH"),
        duckdb_database=os.getenv("DUCKDB_DATABASE", "main"),
        
        oracle_client_directories=oracle_client_directories,
        
        sync_oracle_schema=os.getenv("SYNC_ORACLE_SCHEMA", ""),
        sync_oracle_table=sync_oracle_table,
        sync_duckdb_table=sync_duckdb_table,
        sync_primary_key=os.getenv("SYNC_PRIMARY_KEY", "ID"),
        sync_time_column=os.getenv("SYNC_TIME_COLUMN", "TIMESTAMP_COL"),
        duckdb_time_column=duckdb_time_column,

        # Performance settings
        sync_batch_size=int(os.getenv("SYNC_BATCH_SIZE", "10000")),
        oracle_fetch_batch_size=int(os.getenv("ORACLE_FETCH_BATCH_SIZE", "10000")),
        sync_max_duration_seconds=int(os.getenv("SYNC_MAX_DURATION_SECONDS", "3600")),
        test_sync_default_row_limit=int(os.getenv("TEST_SYNC_DEFAULT_ROW_LIMIT", "100000")),
        default_sync_start_time=os.getenv("DEFAULT_SYNC_START_TIME", "2020-01-01 00:00:00"),

        # Progress reporting
        progress_refresh_interval_seconds=float(os.getenv("PROGRESS_REFRESH_INTERVAL_SECONDS", "0.5")),

        # Type detection
        type_detection_threshold=float(os.getenv("TYPE_DETECTION_THRESHOLD", "0.9")),

        # Retry settings
        sync_retry_attempts=int(os.getenv("SYNC_RETRY_ATTEMPTS", "3")),
        sync_retry_delay_seconds=float(os.getenv("SYNC_RETRY_DELAY_SECONDS", "0.1")),
        
        # Infinite loop prevention
        sync_max_iterations=int(os.getenv("SYNC_MAX_ITERATIONS", "10000")),

        # State file paths
        state_directory=os.getenv("STATE_DIRECTORY", "./data"),
        sync_state_file=os.getenv("SYNC_STATE_FILE", "sync_state.json"),
        schema_mapping_file=os.getenv("SCHEMA_MAPPING_FILE", "schema_mappings.json"),
        sync_progress_file=os.getenv("SYNC_PROGRESS_FILE", "sync_progress.json")
    )
