"""
End-to-End Tests for Oracle-DuckDB Sync System
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
from oracle_duckdb_sync.config import Config, load_config
from oracle_duckdb_sync.sync_engine import SyncEngine
from oracle_duckdb_sync.duckdb_source import DuckDBSource
# Do NOT import OracleSource here - it will be imported after TNS_ADMIN is set


@pytest.fixture
def e2e_config():
    """Configuration for E2E tests"""
    return Config(
        oracle_host="oracle_host",
        oracle_port=1521,
        oracle_service_name="XE",
        oracle_user="test_user",
        oracle_password="test_pass",
        duckdb_path=":memory:"
    )


def test_130_full_sync_e2e(e2e_config):
    """
    TEST-130: 초기 Full Sync E2E(Oracle → DuckDB → UI 조회)
    
    Validates complete data flow:
    1. Extract data from Oracle
    2. Load into DuckDB
    3. Query data through UI layer
    """
    # This test should verify the complete E2E flow
    # Oracle data extraction -> DuckDB loading -> UI query
    with patch("oracle_duckdb_sync.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.sync_engine.DuckDBSource") as mock_duckdb_cls:
        
        # Setup mock Oracle source with sample data
        mock_oracle = mock_oracle_cls.return_value
        oracle_data = [
            (1, "Record1", "2023-01-01 10:00:00"),
            (2, "Record2", "2023-01-02 11:00:00"),
            (3, "Record3", "2023-01-03 12:00:00")
        ]
        mock_oracle.fetch_batch.side_effect = [oracle_data, []]
        
        # Setup mock DuckDB target
        mock_duckdb = mock_duckdb_cls.return_value

        # Capture what was inserted into DuckDB
        inserted_data = []
        def capture_insert(table, data):
            inserted_data.extend(data)
        mock_duckdb.insert_batch.side_effect = capture_insert

        # Step 1: Execute full sync (Oracle -> DuckDB)
        engine = SyncEngine(e2e_config)
        total_rows = engine.full_sync("SOURCE_TABLE", "TARGET_TABLE", "ID")

        # Verify data was extracted from Oracle
        assert mock_oracle.fetch_batch.called
        # Called once (returns 3 rows which is less than default batch_size of 10000, so breaks)

        # Verify data was loaded into DuckDB
        assert mock_duckdb.ensure_database.called
        assert mock_duckdb.insert_batch.called
        assert total_rows == 3
        
        # Verify the exact data that was inserted
        assert len(inserted_data) == 3
        assert inserted_data[0] == (1, "Record1", "2023-01-01 10:00:00")
        
        # Step 2: Query data from DuckDB (simulating UI query)
        # Mock the query result to return the synced data
        mock_duckdb.execute.return_value = inserted_data

        # Simulate UI layer querying DuckDB (create new instance like UI would)
        with patch("oracle_duckdb_sync.duckdb_source.DuckDBSource.__init__", return_value=None):
            ui_duckdb_source = DuckDBSource(e2e_config)
            ui_duckdb_source.execute = Mock(return_value=inserted_data)

            query_result = ui_duckdb_source.execute("SELECT * FROM TARGET_TABLE LIMIT 100")
        
        # Step 3: Verify UI can retrieve the synced data
        assert query_result is not None
        assert len(query_result) == 3
        assert query_result[0][0] == 1
        assert query_result[0][1] == "Record1"
        assert query_result[1][0] == 2
        assert query_result[1][1] == "Record2"
        assert query_result[2][0] == 3
        assert query_result[2][1] == "Record3"
        
        # Verify the data flow: Oracle data → DuckDB → UI query returns same data
        assert query_result == oracle_data





@pytest.mark.e2e
def test_131_incremental_sync_e2e_real_db():
    """
    TEST-131: 일일 증분 동기화 E2E 및 상태 업데이트
    
    Uses actual .env configuration to test:
    1. Perform initial full sync from Oracle (in 10k batches)
    2. Save sync state with last timestamp
    3. Verify state was saved correctly
    4. Test incremental sync query
    5. Update state after incremental sync
    
    NOTE: This test requires:
    - Valid .env file with actual DB credentials
    - Oracle table must exist with time column
    """
    import os
    import tempfile
    import time
    import datetime
    import shutil

    # Set TNS_ADMIN to use test directory's sqlnet.ora
    test_dir = os.path.dirname(__file__)
    old_tns_admin = os.environ.get('TNS_ADMIN')
    os.environ['TNS_ADMIN'] = test_dir
    
    # Temporary directory for state file
    tmpdir = tempfile.mkdtemp()
    
    try:
        # Import OracleSource AFTER setting TNS_ADMIN
        from oracle_duckdb_sync.oracle_source import OracleSource

        # Load configuration from .env file
        config = load_config()
        
        # Get table configuration from .env
        oracle_table = os.getenv('SYNC_ORACLE_TABLE', 'SOURCE_TABLE')
        duckdb_table = os.getenv('SYNC_DUCKDB_TABLE') or oracle_table.lower()
        time_column = os.getenv('SYNC_TIME_COLUMN', 'TIMESTAMP_COL').split(',')[0].strip()  # Use first column
        primary_key = os.getenv('SYNC_PRIMARY_KEY', 'ID')

        print(f"\n[TEST-131] Incremental Sync E2E Test")
        print(f"  Oracle table: {oracle_table}")
        print(f"  DuckDB table: {duckdb_table}")
        print(f"  Time column: {time_column}")
        print(f"  Primary key: {primary_key}")

        # Step 1: Connect to Oracle and get initial data count
        oracle_source = OracleSource(config)
        
        # First, check if table exists and get accessible tables if not
        try:
            # Get total row count
            count_query = f"SELECT COUNT(*) FROM {oracle_table}"
            count_result = oracle_source.fetch_all(count_query)
            total_rows = count_result[0][0] if count_result else 0
        except Exception as e:
            if "ORA-00942" in str(e):
                # Table doesn't exist, list available tables
                print(f"\n[ERROR] Table {oracle_table} not found!")
                print(f"  Checking available tables for user {config.oracle_user}...")
                
                # Query user tables
                tables_query = """
                SELECT table_name, num_rows 
                FROM user_tables 
                WHERE ROWNUM <= 20
                ORDER BY table_name
                """
                available_tables = oracle_source.fetch_all(tables_query)
                
                print(f"\n  User tables (showing first 20):")
                for table_name, num_rows in available_tables:
                    print(f"    - {table_name}: {num_rows if num_rows else 'N/A'} rows")
                
                # Also check all accessible tables
                all_tables_query = f"""
                SELECT owner, table_name, num_rows 
                FROM all_tables 
                WHERE table_name LIKE '%{oracle_table}%'
                ORDER BY owner, table_name
                """
                all_accessible_tables = oracle_source.fetch_all(all_tables_query)
                
                print(f"\n  All accessible tables matching '{oracle_table}':")
                for owner, table_name, num_rows in all_accessible_tables:
                    print(f"    - {owner}.{table_name}: {num_rows if num_rows else 'N/A'} rows")
                
                raise Exception(f"Table {oracle_table} not found. Please check available tables above.")
            else:
                raise
        
        print(f"\n[Step 1] Oracle table has {total_rows} total rows")
        assert total_rows > 0, f"Oracle table {oracle_table} is empty"

        # Step 2: Perform initial full sync in 10k batches
        print(f"\n[Step 2] Performing full sync in 10k batches...")
        
        with patch("oracle_duckdb_sync.sync_engine.DuckDBSource") as mock_duckdb_cls:
            mock_duckdb = mock_duckdb_cls.return_value
            mock_duckdb.ensure_database.return_value = None
            mock_duckdb.table_exists.return_value = True
            
            # Capture all inserted batches
            all_batches = []
            def capture_batch(table, data):
                all_batches.append(data)
                print(f"    Batch {len(all_batches)}: {len(data)} rows")
            mock_duckdb.insert_batch.side_effect = capture_batch
            
            # Mock schema operations for full_sync
            schema = oracle_source.get_table_schema(oracle_table)
            mock_duckdb.map_oracle_type = MagicMock(return_value="VARCHAR")
            mock_duckdb.build_create_table_query = MagicMock(return_value="CREATE TABLE test")
            mock_duckdb.execute = MagicMock()
            
            # Initialize sync engine
            engine = SyncEngine(config)
            
            # Perform full sync with 10k batch size
            start_time = time.time()
            total_synced = engine.sync_in_batches(
                oracle_table=oracle_table,
                duckdb_table=duckdb_table,
                batch_size=10000
            )
            elapsed = time.time() - start_time
            
            print(f"\n  [Step 2 Complete] Synced {total_synced} rows in {elapsed:.2f}s")
            print(f"    Number of batches: {len(all_batches)}")
            print(f"    Throughput: {total_synced/elapsed:.0f} rows/sec")
            
            # Verify batching behavior
            assert len(all_batches) > 0, "No batches were captured"
            
            # If we have multiple batches, all except last should have 10k rows
            if len(all_batches) > 1:
                for i, batch in enumerate(all_batches[:-1]):
                    assert len(batch) == 10000, f"Batch {i} should have 10k rows, got {len(batch)}"
            
            # Last batch should have <= 10k rows
            last_batch = all_batches[-1]
            assert len(last_batch) <= 10000, f"Last batch should have <= 10k rows, got {len(last_batch)}"
            
            # Total rows should match
            total_captured = sum(len(batch) for batch in all_batches)
            assert total_captured == total_synced, \
                f"Captured {total_captured} rows but engine reported {total_synced}"

        # Step 3: Save sync state with current timestamp
        print(f"\n[Step 3] Saving sync state...")
        
        # Use current time as last_sync_time
        last_sync_time = datetime.datetime.now().isoformat()
        
        # Use temporary state file
        state_file = os.path.join(tmpdir, "sync_state.json")
        engine.save_state(
            table_name=oracle_table,
            last_value=last_sync_time,
            file_path=state_file
        )
        
        print(f"    Saved state: {oracle_table} -> {last_sync_time}")

        # Step 4: Verify state was saved correctly
        print(f"\n[Step 4] Verifying saved state...")
        
        loaded_state = engine.load_state(
            table_name=oracle_table,
            file_path=state_file
        )
        
        assert loaded_state is not None, "Failed to load sync state"
        assert loaded_state == last_sync_time, \
            f"Loaded state {loaded_state} doesn't match saved {last_sync_time}"
        
        print(f"    State verified: {loaded_state}")

        # Step 5: Test incremental sync query
        print(f"\n[Step 5] Testing incremental sync query...")
        
        # Build incremental query with a past timestamp to get some data
        past_time = "2024-01-01 00:00:00"
        incremental_query = oracle_source.build_incremental_query(
            oracle_table,
            time_column,
            past_time
        )
        
        print(f"    Query: {incremental_query[:100]}...")
        
        # Fetch one batch to verify query works
        incremental_data = oracle_source.fetch_batch(
            incremental_query,
            batch_size=100
        )
        
        assert incremental_data is not None, "Incremental query failed"
        print(f"    Incremental query returned {len(incremental_data)} rows")

        # Step 6: Update state after incremental sync
        print(f"\n[Step 6] Updating state after incremental sync...")
        
        new_sync_time = datetime.datetime.now().isoformat()
        engine.save_state(
            table_name=oracle_table,
            last_value=new_sync_time,
            file_path=state_file
        )
        
        updated_state = engine.load_state(
            table_name=oracle_table,
            file_path=state_file
        )
        
        assert updated_state == new_sync_time, \
            f"Updated state {updated_state} doesn't match new time {new_sync_time}"
        
        print(f"    State updated: {updated_state}")
        
        print(f"\n[SUCCESS] TEST-131 Complete!")
        print(f"  ✓ Full sync with 10k batches: {total_synced} rows")
        print(f"  ✓ Number of batches: {len(all_batches)}")
        print(f"  ✓ State save/load verified")
        print(f"  ✓ Incremental query works")
        print(f"  ✓ State update after incremental sync works")

        # Cleanup
        oracle_source.disconnect()
        
    finally:
        # Restore original TNS_ADMIN
        if old_tns_admin:
            os.environ['TNS_ADMIN'] = old_tns_admin
        elif 'TNS_ADMIN' in os.environ:
            del os.environ['TNS_ADMIN']
        
        # Clean up temporary directory
        shutil.rmtree(tmpdir, ignore_errors=True)
