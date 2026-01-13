"""
Import validation script - tests if all modules can be imported.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_001_imports():
    """TEST-001~004: pytest 기본 실행 및 주요 모듈 import 확인"""
    errors = []
    success = []

    test_cases = [
        ("DuckDBSource", "from oracle_duckdb_sync.database.duckdb_source import DuckDBSource"),
        ("OracleSource", "from oracle_duckdb_sync.database.oracle_source import OracleSource"),
        ("SyncEngine", "from oracle_duckdb_sync.database.sync_engine import SyncEngine"),
        ("QueryService", "from oracle_duckdb_sync.application.query_service import QueryService"),
        ("Config", "from oracle_duckdb_sync.config import Config, load_config"),
        ("Converter", "from oracle_duckdb_sync.data.converter import detect_and_convert_types"),
        ("QueryCore", "from oracle_duckdb_sync.data.query_core import get_available_tables"),
        ("Query", "from oracle_duckdb_sync.data.query import query_duckdb_table"),
        ("LTTB", "from oracle_duckdb_sync.data.lttb import lttb_downsample"),
        ("Logger", "from oracle_duckdb_sync.log.logger import setup_logger"),
        ("StreamlitCache", "from oracle_duckdb_sync.adapters.streamlit_cache import StreamlitCacheProvider"),
        ("Handlers", "from oracle_duckdb_sync.ui.handlers import handle_test_sync"),
        ("SessionState", "from oracle_duckdb_sync.ui.session_state import initialize_session_state"),
        ("Visualization", "from oracle_duckdb_sync.ui.visualization import render_data_visualization"),
    ]

    print("Testing module imports...\n")

    for name, import_stmt in test_cases:
        try:
            exec(import_stmt)
            success.append(name)
            print(f"✓ {name}")
        except Exception as e:
            errors.append((name, str(e)))
            print(f"✗ {name}: {e}")

    print(f"\n{'='*60}")
    print(f"Results: {len(success)} OK, {len(errors)} ERRORS")
    print(f"{'='*60}\n")

    if errors:
        print("IMPORT ERRORS:\n")
        for name, error in errors:
            print(f"{name}:")
            print(f"  {error}\n")
        return 1
    else:
        print("✓ All imports successful!")

        # Test DuckDBSource has get_connection method
        print("\nTesting DuckDBSource.get_connection() method...")
        from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
        if hasattr(DuckDBSource, 'get_connection'):
            print("✓ DuckDBSource.get_connection() method exists")
        else:
            print("✗ DuckDBSource.get_connection() method NOT FOUND")
            return 1

        return 0

if __name__ == '__main__':
    sys.exit(test_001_imports())
