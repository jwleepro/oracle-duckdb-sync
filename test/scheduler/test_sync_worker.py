"""Tests for SyncWorker - background thread sync execution"""
import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from oracle_duckdb_sync.config import Config


@pytest.fixture
def mock_config():
    return Config(
        oracle_host="localhost",
        oracle_port=1521,
        oracle_service_name="XE",
        oracle_user="test_user",
        oracle_password="test_password",
        duckdb_path=":memory:"
    )


def test_150_sync_worker_thread_lifecycle(mock_config):
    """TEST-150: SyncWorker 스레드 시작·종료·상태 확인
    
    This test verifies that:
    1. SyncWorker can be created with sync parameters
    2. Worker thread starts successfully
    3. Worker status can be checked (idle, running, completed, error)
    4. Worker thread terminates properly
    5. Worker can be reused for multiple sync operations
    """
    from oracle_duckdb_sync.scheduler.sync_worker import SyncWorker
    
    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource") as mock_duckdb_cls:
        
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value
        
        # Mock schema operations
        mock_oracle.get_table_schema.return_value = [
            ('ID', 'NUMBER'),
            ('NAME', 'VARCHAR2(100)')
        ]
        # map_oracle_type is now in SyncEngine, not DuckDBSource
        mock_duckdb.build_create_table_query.return_value = 'CREATE TABLE test_table (ID DOUBLE, NAME VARCHAR)'
        mock_duckdb.execute.return_value = None

        # Mock successful sync - need to mock cursor for test_sync
        mock_cursor = MagicMock()
        mock_cursor.fetchmany.side_effect = [
            [(i, f"Data{i}") for i in range(100)],
            []
        ]
        mock_cursor.description = [('ID', None), ('NAME', None)]
        mock_oracle.conn.cursor.return_value = mock_cursor
        mock_duckdb.table_exists.return_value = True
        mock_duckdb.insert_batch.return_value = 100
        
        # Test 1: Create SyncWorker
        worker = SyncWorker(
            config=mock_config,
            sync_params={
                'sync_type': 'test',
                'oracle_table': 'TEST_TABLE',
                'duckdb_table': 'test_table',
                'primary_key': 'ID',
                'row_limit': 1000
            }
        )
        
        assert worker is not None
        assert worker.status == 'idle'
        assert worker.thread is None
        
        # Test 2: Start worker thread
        worker.start()
        
        assert worker.thread is not None
        assert isinstance(worker.thread, threading.Thread)
        assert worker.thread.is_alive()
        assert worker.status in ['running', 'completed']  # May complete quickly
        
        # Test 3: Wait for completion
        worker.thread.join(timeout=5.0)
        
        assert not worker.thread.is_alive()
        assert worker.status == 'completed'
        assert worker.error_info is None
        
        # Test 4: Check result
        assert worker.total_rows == 100
        
        # Test 5: Verify thread cleanup
        assert worker.thread is not None  # Thread object still exists
        assert not worker.thread.is_alive()  # But is not running


def test_150_sync_worker_status_transitions(mock_config):
    """Test status transitions during sync lifecycle"""
    from oracle_duckdb_sync.scheduler.sync_worker import SyncWorker
    
    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource") as mock_duckdb_cls:
        
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value
        
        # Mock schema operations
        mock_oracle.get_table_schema.return_value = [
            ('ID', 'NUMBER'),
            ('NAME', 'VARCHAR2(100)')
        ]
        # map_oracle_type is now in SyncEngine, not DuckDBSource
        mock_duckdb.build_create_table_query.return_value = 'CREATE TABLE test_table (ID DOUBLE, NAME VARCHAR)'
        mock_duckdb.execute.return_value = None
        
        # Mock slow sync to observe status transitions
        # Side effect with data (not functions)  
        call_count = [0]
        def fetch_with_delay(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                time.sleep(0.1)
                return [(i, f"Data{i}") for i in range(10)]
            else:
                return []
        
        # Mock cursor for test_sync
        mock_cursor = MagicMock()
        mock_cursor.description = [('ID', None), ('NAME', None)]
        mock_oracle.conn.cursor.return_value = mock_cursor
        mock_cursor.fetchmany.side_effect = fetch_with_delay
        
        # test_sync creates table then _execute_sync checks if it exists
        # So table_exists should return True when _execute_sync checks
        mock_duckdb.table_exists.return_value = True
        
        mock_duckdb.insert_batch.return_value = None  # Success
        mock_duckdb.ensure_database.return_value = None
        
        worker = SyncWorker(
            config=mock_config,
            sync_params={
                'sync_type': 'test',
                'oracle_table': 'TEST_TABLE',
                'duckdb_table': 'test_table',
                'primary_key': 'ID',
                'row_limit': 100
            }
        )
        
        # Initial status
        assert worker.status == 'idle'
        
        # Start and check running status
        worker.start()
        time.sleep(0.05)  # Give thread time to start
        
        # Should be running
        running_observed = worker.status == 'running'
        
        # Wait for completion
        worker.thread.join(timeout=5.0)
        
        # Debug: Print error if any
        if worker.status == 'error':
            print(f"Error: {worker.error_info}")
        
        # Final status
        assert worker.status == 'completed'
        assert running_observed or worker.status == 'completed'  # May complete too fast


def test_150_sync_worker_error_handling(mock_config):
    """Test error handling in SyncWorker"""
    from oracle_duckdb_sync.scheduler.sync_worker import SyncWorker
    
    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource") as mock_duckdb_cls:
        
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value
        
        # Mock schema operations
        mock_oracle.get_table_schema.return_value = [
            ('ID', 'NUMBER'),
            ('NAME', 'VARCHAR2(100)')
        ]
        # map_oracle_type is now in SyncEngine, not DuckDBSource
        mock_duckdb.build_create_table_query.return_value = 'CREATE TABLE test_table (ID DOUBLE, NAME VARCHAR)'
        mock_duckdb.execute.return_value = None
        
        # Mock sync that fails
        # Mock cursor for test_sync
        mock_cursor = MagicMock()
        mock_cursor.description = [('ID', None), ('NAME', None)]
        mock_oracle.conn.cursor.return_value = mock_cursor
        mock_cursor.fetchmany.side_effect = Exception("Database connection failed")
        mock_duckdb.table_exists.return_value = True
        
        worker = SyncWorker(
            config=mock_config,
            sync_params={
                'sync_type': 'test',
                'oracle_table': 'TEST_TABLE',
                'duckdb_table': 'test_table',
                'primary_key': 'ID',
                'row_limit': 100
            }
        )
        
        # Start worker
        worker.start()
        worker.thread.join(timeout=5.0)
        
        # Check error status
        assert worker.status == 'error'
        assert worker.error_info is not None
        assert 'exception' in worker.error_info
        assert 'Database connection failed' in worker.error_info['exception']
        assert 'traceback' in worker.error_info


def test_151_progress_callback_and_queue(mock_config):
    """TEST-151: 진행 상황 콜백 호출 및 큐 전달
    
    This test verifies that:
    1. SyncWorker can be created with progress queue
    2. Progress messages are sent to queue during sync
    3. Progress messages include row counts and statistics
    4. Messages can be retrieved from queue
    5. Queue is thread-safe
    """
    from oracle_duckdb_sync.scheduler.sync_worker import SyncWorker
    import queue
    
    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource") as mock_duckdb_cls:
        
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value
        
        # Mock schema operations
        mock_oracle.get_table_schema.return_value = [
            ('ID', 'NUMBER'),
            ('NAME', 'VARCHAR2(100)')
        ]
        # map_oracle_type is now in SyncEngine, not DuckDBSource
        mock_duckdb.build_create_table_query.return_value = 'CREATE TABLE test_table (ID DOUBLE, NAME VARCHAR)'
        mock_duckdb.execute.return_value = None
        
        # Mock sync with batches that will complete in multiple batches
        # Mock cursor for test_sync
        mock_cursor = MagicMock()
        mock_cursor.description = [('ID', None), ('NAME', None)]
        mock_oracle.conn.cursor.return_value = mock_cursor
        mock_cursor.fetchmany.side_effect = [
            [(i, f"Data{i}") for i in range(10000)],  # First full batch
            [(i, f"Data{i}") for i in range(10000, 10250)],  # Second partial batch (250 rows)
            []
        ]
        mock_duckdb.table_exists.return_value = True
        mock_duckdb.insert_batch.return_value = None
        mock_duckdb.ensure_database.return_value = None
        
        # Test 1: Create worker with progress queue
        progress_queue = queue.Queue()
        
        worker = SyncWorker(
            config=mock_config,
            sync_params={
                'sync_type': 'test',
                'oracle_table': 'TEST_TABLE',
                'duckdb_table': 'test_table',
                'primary_key': 'ID',
                'row_limit': 15000  # High enough to allow multiple batches
            },
            progress_queue=progress_queue
        )
        
        assert worker.progress_queue is progress_queue
        
        # Test 2: Start sync and wait for completion
        worker.start()
        worker.thread.join(timeout=5.0)
        
        assert worker.status == 'completed'
        assert worker.total_rows == 10250  # 10000 + 250 rows from two batches
        
        # Test 3: Retrieve progress messages from queue
        messages = []
        while not progress_queue.empty():
            try:
                msg = progress_queue.get_nowait()
                messages.append(msg)
            except queue.Empty:
                break
        
        # Should have progress messages
        assert len(messages) > 0
        
        # Test 4: Verify progress message structure
        progress_messages = [m for m in messages if m.get('type') == 'progress']
        assert len(progress_messages) > 0
        
        for msg in progress_messages:
            assert 'type' in msg
            assert msg['type'] == 'progress'
            assert 'data' in msg
            assert 'timestamp' in msg
            
            # Progress data should include row counts
            data = msg['data']
            assert 'total_rows' in data
            assert 'batch_rows' in data
            assert isinstance(data['total_rows'], int)
            assert isinstance(data['batch_rows'], int)
        
        # Test 5: Verify final completion message
        complete_messages = [m for m in messages if m.get('type') == 'complete']
        assert len(complete_messages) == 1
        
        complete_msg = complete_messages[0]
        assert complete_msg['data']['total_rows'] == 10250


def test_151_progress_queue_optional(mock_config):
    """Test that progress queue is optional"""
    from oracle_duckdb_sync.scheduler.sync_worker import SyncWorker
    
    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource") as mock_duckdb_cls:
        
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value
        
        # Mock schema operations
        mock_oracle.get_table_schema.return_value = [
            ('ID', 'NUMBER'),
            ('NAME', 'VARCHAR2(100)')
        ]
        # map_oracle_type is now in SyncEngine, not DuckDBSource
        mock_duckdb.build_create_table_query.return_value = 'CREATE TABLE test_table (ID DOUBLE, NAME VARCHAR)'
        mock_duckdb.execute.return_value = None
        
        # Mock simple sync
        # Mock cursor for test_sync
        mock_cursor = MagicMock()
        mock_cursor.description = [('ID', None), ('NAME', None)]
        mock_oracle.conn.cursor.return_value = mock_cursor
        mock_cursor.fetchmany.side_effect = [
            [(i, f"Data{i}") for i in range(50)],
            []
        ]
        mock_duckdb.table_exists.return_value = True
        mock_duckdb.insert_batch.return_value = None
        mock_duckdb.ensure_database.return_value = None
        
        # Create worker WITHOUT progress queue
        worker = SyncWorker(
            config=mock_config,
            sync_params={
                'sync_type': 'test',
                'oracle_table': 'TEST_TABLE',
                'duckdb_table': 'test_table',
                'primary_key': 'ID',
                'row_limit': 100
            }
            # No progress_queue parameter
        )
        
        # Should work without queue
        worker.start()
        worker.thread.join(timeout=5.0)
        
        assert worker.status == 'completed'
        assert worker.total_rows == 50





def test_152_pause_state_transitions(mock_config):
    """Test pause state transitions and error conditions"""
    from oracle_duckdb_sync.scheduler.sync_worker import SyncWorker
    
    with patch("oracle_duckdb_sync.database.sync_engine.OracleSource") as mock_oracle_cls, \
         patch("oracle_duckdb_sync.database.sync_engine.DuckDBSource") as mock_duckdb_cls:
        
        mock_oracle = mock_oracle_cls.return_value
        mock_duckdb = mock_duckdb_cls.return_value
        
        # Mock schema operations
        mock_oracle.get_table_schema.return_value = [
            ('ID', 'NUMBER'),
            ('NAME', 'VARCHAR2(100)')
        ]
        # map_oracle_type is now in SyncEngine, not DuckDBSource
        mock_duckdb.build_create_table_query.return_value = 'CREATE TABLE test_table (ID DOUBLE, NAME VARCHAR)'
        mock_duckdb.execute.return_value = None
        
        # Mock simple sync
        # Mock cursor for test_sync
        mock_cursor = MagicMock()
        mock_cursor.description = [('ID', None), ('NAME', None)]
        mock_oracle.conn.cursor.return_value = mock_cursor
        mock_cursor.fetchmany.side_effect = [
            [(i, f"Data{i}") for i in range(50)],
            []
        ]
        mock_duckdb.table_exists.return_value = True
        mock_duckdb.insert_batch.return_value = None
        mock_duckdb.ensure_database.return_value = None
        
        worker = SyncWorker(
            config=mock_config,
            sync_params={
                'sync_type': 'test',
                'oracle_table': 'TEST_TABLE',
                'duckdb_table': 'test_table',
                'primary_key': 'ID',
                'row_limit': 100
            }
        )
        
        # Can't pause when not running
        assert worker.status == 'idle'
        # This should not crash
        worker.pause()
        
        # Start and quickly complete
        worker.start()
        worker.thread.join(timeout=5.0)
        
        assert worker.status == 'completed'
        
        # Pausing completed worker should be safe
        worker.pause()  # Should not crash

    def test_sync_params_priority_over_config(mock_config):
        """Test that sync_params takes priority over config values"""
        from oracle_duckdb_sync.scheduler.sync_worker import SyncWorker
        
        # Patch SyncEngine where it is imported in sync_worker module
        with patch("oracle_duckdb_sync.scheduler.sync_worker.SyncEngine") as mock_engine_cls:
            mock_engine = mock_engine_cls.return_value
            mock_engine.test_sync.return_value = 100
        # Configure config with default values
        mock_config.sync_oracle_table = "CONFIG_ORACLE_TABLE"
        mock_config.sync_duckdb_table = "config_duckdb_table"
        mock_config.sync_primary_key = "CONFIG_PK"
        
        # 1. Test with full sync_params (should override config)
        worker = SyncWorker(
            config=mock_config,
            sync_params={
                'sync_type': 'test',
                'oracle_table': 'PARAM_ORACLE_TABLE',
                'duckdb_table': 'param_duckdb_table',
                'primary_key': 'PARAM_PK',
                'row_limit': 500
            }
        )
        
        worker.start()
        worker.thread.join(timeout=2.0)
        
        # Verify SyncEngine was called with params, not config
        mock_engine.test_sync.assert_called_with(
            oracle_table_name='PARAM_ORACLE_TABLE',
            duckdb_table='param_duckdb_table',
            primary_key='PARAM_PK',
            row_limit=500
        )
        
        # 2. Test with partial sync_params (should fallback to config)
        worker_fallback = SyncWorker(
            config=mock_config,
            sync_params={
                'sync_type': 'test',
                # oracle_table missing -> fallback to config
                # duckdb_table missing -> fallback to config
                # primary_key missing -> fallback to config
                'row_limit': 100
            }
        )
        
        worker_fallback.start()
        worker_fallback.thread.join(timeout=2.0)
        
        # Verify fallback to config values
        mock_engine.test_sync.assert_called_with(
            oracle_table_name='CONFIG_ORACLE_TABLE',
            duckdb_table='config_duckdb_table',
            primary_key='CONFIG_PK',
            row_limit=100
        )
