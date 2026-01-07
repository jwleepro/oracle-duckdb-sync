"""SyncWorker - Background thread for non-blocking sync operations"""
import threading
import traceback
import time
import datetime
from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.sync_engine import SyncEngine
from oracle_duckdb_sync.log.logger import setup_logger


class SyncWorker:
    """Worker that runs sync operations in a background thread
    
    This allows the UI to remain responsive while sync operations run.
    Supports status monitoring, error handling, and progress reporting.
    """
    
    def __init__(self, config: Config, sync_params: dict, progress_queue=None):
        """Initialize SyncWorker
        
        Args:
            config: Configuration object
            progress_queue: Optional queue.Queue for progress messages
        """
        self.config = config
        self.sync_params = sync_params or {}
        self.progress_queue = progress_queue
        self.status = 'idle'  # idle, running, paused, completed, error
        self.thread = None
        self.error_info = None
        self.total_rows = 0
        self.start_time = None
        self.logger = setup_logger('SyncWorker')
        
        # Pause/resume control
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._stop_flag = threading.Event()  # Initialize logger
    
    def start(self):
        """Start the sync operation in a background thread"""
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Worker is already running")
        
        self.status = 'running'
        self.error_info = None
        self.total_rows = 0
        
        self.thread = threading.Thread(target=self._run_sync, daemon=True)
        self.thread.start()

    def pause(self):
        """Pause the sync operation"""
        if self.status == 'running':
            self._pause_event.clear()
            self.status = 'paused'
            self.logger.info("Sync paused")
    
    def resume(self):
        """Resume the sync operation"""
        if self.status == 'paused':
            self._pause_event.set()
            self.status = 'running'
            self.logger.info("Sync resumed")
    
    def stop(self):
        """Stop the sync operation"""
        self._stop_flag.set()
        self._pause_event.set()  # Unpause if paused so thread can exit
        self.logger.info("Sync stop requested")
    
    def _run_sync(self):
        """Internal method that runs in the background thread"""
        self.start_time = time.time()
        
        try:
            # Create sync engine with progress callback if queue is provided
            sync_engine = SyncEngine(self.config)
            
            # Create progress callback
            progress_callback = self._create_progress_callback() if self.progress_queue else None
            
            def get_param(key, default=None):
                if isinstance(self.sync_params, dict):
                    return self.sync_params.get(key, default)
                return getattr(self.sync_params, key, default)

            # Determine sync type and execute
            sync_type = get_param('sync_type', 'test')

            oracle_table_name = get_param('oracle_table') or get_param('table_name')
            if not oracle_table_name:
                oracle_schema = self.config.sync_oracle_schema
                oracle_table = self.config.sync_oracle_table
                if oracle_schema and oracle_table:
                    oracle_table_name = f"{oracle_schema}.{oracle_table}"
                else:
                    oracle_table_name = oracle_table

            duckdb_table = get_param('duckdb_table') or self.config.sync_duckdb_table
            if not duckdb_table and oracle_table_name:
                duckdb_table = oracle_table_name.split('.')[-1].lower()

            primary_key = get_param('primary_key') or self.config.sync_primary_key

            if not oracle_table_name:
                raise ValueError("Oracle table name is required for sync")
            if not duckdb_table:
                raise ValueError("DuckDB table name is required for sync")
            
            # Note: We need to modify sync methods to accept progress_callback
            # For now, we'll use a wrapper approach with monkey patching
            if progress_callback:
                self._wrap_sync_engine_with_callback(sync_engine, progress_callback)
            
            if sync_type == 'test':
                row_limit = get_param('row_limit', 10000)
                self.total_rows = sync_engine.test_sync(
                    oracle_table_name=oracle_table_name,
                    duckdb_table=duckdb_table,
                    primary_key=primary_key,
                    row_limit=row_limit
                )
            elif sync_type == 'full':
                self.total_rows = sync_engine.full_sync(
                    oracle_table_name=oracle_table_name,
                    duckdb_table=duckdb_table,
                    primary_key=primary_key
                )
            elif sync_type == 'incremental':
                time_column = get_param('time_column', self.config.sync_time_column)
                last_value = get_param('last_value')
                if not time_column:
                    raise ValueError("time_column is required for incremental sync")
                if last_value is None:
                    raise ValueError("last_value is required for incremental sync")
                self.total_rows = sync_engine.incremental_sync(
                    oracle_table_name=oracle_table_name,
                    duckdb_table=duckdb_table,
                    column=time_column,
                    last_value=last_value,
                    primary_key=primary_key
                )
            else:
                raise ValueError(f"Unknown sync_type: {sync_type}")
            
            # Send completion message
            if self.progress_queue:
                self._send_message('complete', {
                    'total_rows': self.total_rows
                })
            
            # Mark as completed
            self.status = 'completed'
            
        except Exception as e:
            # Capture error information
            error_traceback = traceback.format_exc()
            self.error_info = {
                'exception': str(e),
                'traceback': error_traceback
            }
            self.status = 'error'
            
            # Log error to file
            self.logger.error(f"Sync operation failed: {e}")
            self.logger.error(f"Traceback:\n{error_traceback}")
            
            # Send error message
            if self.progress_queue:
                self._send_message('error', self.error_info)
    
    def _create_progress_callback(self):
        """Create a progress callback function with ETA calculation"""
        def callback(total_rows, batch_rows):
            """Progress callback that sends messages to queue"""
            elapsed = time.time() - self.start_time
            rows_per_second = total_rows / elapsed if elapsed > 0 else 0
            
            # Calculate ETA if we know total expected rows
            eta = None
            percentage = 0
            if hasattr(self, 'expected_rows') and self.expected_rows > 0:
                percentage = total_rows / self.expected_rows
                remaining_rows = self.expected_rows - total_rows
                if rows_per_second > 0:
                    eta_seconds = remaining_rows / rows_per_second
                    eta = time.strftime('%H:%M:%S', time.gmtime(eta_seconds))
            
            self._send_message('progress', {
                'total_rows': total_rows,
                'batch_rows': batch_rows,
                'elapsed_time': elapsed,
                'rows_per_second': rows_per_second,
                'percentage': percentage,
                'eta': eta
            })
        
        return callback
    
    def _send_message(self, msg_type, data):
        """Send a message to the progress queue"""
        if self.progress_queue:
            message = {
                'type': msg_type,
                'data': data,
                'timestamp': datetime.datetime.now().strftime('%H:%M:%S')
            }
            self.progress_queue.put_nowait(message)
    
    def _wrap_sync_engine_with_callback(self, sync_engine, callback):
        """Wrap sync engine's _log_progress to call our callback"""
        original_log_progress = sync_engine._log_progress
        
        def wrapped_log_progress(table, total_count, batch_count):
            # Call original
            original_log_progress(table, total_count, batch_count)
            # Call our callback
            callback(total_count, batch_count)
        
        sync_engine._log_progress = wrapped_log_progress
