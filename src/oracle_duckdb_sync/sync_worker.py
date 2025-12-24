"""SyncWorker - Background thread for non-blocking sync operations"""
import threading
import traceback
import time
import datetime
from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.sync_engine import SyncEngine
from oracle_duckdb_sync.logger import setup_logger


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
        self.sync_params = sync_params
        self.progress_queue = progress_queue
        self.status = 'idle'  # idle, running, completed, error
        self.thread = None
        self.error_info = None
        self.total_rows = 0
        self.start_time = None
        self.logger = setup_logger('SyncWorker')  # Initialize logger
    
    def start(self):
        """Start the sync operation in a background thread"""
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Worker is already running")
        
        self.status = 'running'
        self.error_info = None
        self.total_rows = 0
        
        self.thread = threading.Thread(target=self._run_sync, daemon=True)
        self.thread.start()
    
    def _run_sync(self):
        """Internal method that runs in the background thread"""
        self.start_time = time.time()
        
        try:
            # Create sync engine with progress callback if queue is provided
            sync_engine = SyncEngine(self.config)
            
            # Create progress callback
            progress_callback = self._create_progress_callback() if self.progress_queue else None
            
            # Determine sync type and execute
            sync_type = self.sync_params.get('sync_type', 'test')
            oracle_table = self.config.sync_oracle_table
            duckdb_table = self.config.sync_duckdb_table
            primary_key = self.config.sync_primary_key
            
            # Note: We need to modify sync methods to accept progress_callback
            # For now, we'll use a wrapper approach with monkey patching
            if progress_callback:
                self._wrap_sync_engine_with_callback(sync_engine, progress_callback)
            
            if sync_type == 'test':
                row_limit = self.sync_params.get('row_limit', 10000)
                self.total_rows = sync_engine.test_sync(
                    oracle_table=oracle_table,
                    duckdb_table=duckdb_table,
                    primary_key=primary_key,
                    row_limit=row_limit
                )
            elif sync_type == 'full':
                self.total_rows = sync_engine.full_sync(
                    oracle_table=oracle_table,
                    duckdb_table=duckdb_table,
                    primary_key=primary_key
                )
            elif sync_type == 'incremental':
                time_column = self.sync_params['time_column']
                last_value = self.sync_params['last_value']
                self.total_rows = sync_engine.incremental_sync(
                    oracle_table=oracle_table,
                    duckdb_table=duckdb_table,
                    column=time_column,
                    last_value=last_value
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
