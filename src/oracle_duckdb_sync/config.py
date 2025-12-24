import os
from dataclasses import dataclass
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
    
    # Sync target table configuration
    sync_oracle_schema: str = ""
    sync_oracle_table: str = ""
    sync_duckdb_table: str = ""
    sync_primary_key: str = "ID"
    sync_time_column: str = "TIMESTAMP_COL"

def load_config() -> Config:
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
    if not sync_duckdb_table:
        raise ValueError("SYNC_DUCKDB_TABLE must be specified in .env file")

    return Config(
        oracle_host=os.getenv("ORACLE_HOST"),
        oracle_port=oracle_port,
        oracle_service_name=os.getenv("ORACLE_SERVICE_NAME"),
        oracle_user=os.getenv("ORACLE_USER"),
        oracle_password=os.getenv("ORACLE_PASSWORD"),

        duckdb_path=os.getenv("DUCKDB_PATH"),
        duckdb_database=os.getenv("DUCKDB_DATABASE", "main"),
        
        sync_oracle_schema=os.getenv("SYNC_ORACLE_SCHEMA", ""),
        sync_oracle_table=sync_oracle_table,
        sync_duckdb_table=sync_duckdb_table,
        sync_primary_key=os.getenv("SYNC_PRIMARY_KEY", "ID"),
        sync_time_column=os.getenv("SYNC_TIME_COLUMN", "TIMESTAMP_COL")
    )
