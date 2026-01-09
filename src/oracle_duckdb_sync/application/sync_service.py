"""
Sync Service - UI-independent synchronization orchestration.

This service handles all sync-related business logic without
depending on any UI framework.
"""

import threading
from dataclasses import dataclass
from queue import Queue
from typing import Any, Callable, Optional

from ..config.config import Config
from ..log.logger import setup_logger
from ..scheduler.sync_worker import SyncWorker
from ..state import SyncLock

logger = setup_logger(__name__)


@dataclass
class SyncStatus:
    """Encapsulates synchronization status."""
    state: str  # 'idle', 'running', 'completed', 'error'
    progress: Optional[dict[str, Any]] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None


class SyncService:
    """
    Application service for data synchronization.

    This service is UI-agnostic and manages the sync lifecycle.
    """

    def __init__(self, config: Config):
        self.config = config
        self._current_worker: Optional[SyncWorker] = None
        self._current_lock: Optional[SyncLock] = None
        self._progress_queue: Optional[Queue] = None
        self._status = SyncStatus(state='idle')

    def get_status(self) -> SyncStatus:
        """Get current synchronization status."""
        return self._status

    def start_sync(self,
                   sync_params: dict[str, Any],
                   progress_callback: Optional[Callable] = None) -> bool:
        """
        Start synchronization process.

        Args:
            sync_params: Synchronization parameters
            progress_callback: Optional callback for progress updates

        Returns:
            True if sync started successfully, False otherwise
        """
        if sync_params is None:
            logger.error("Sync parameters are required for synchronization")
            return False
        if not isinstance(sync_params, dict):
            logger.error("Sync parameters must be provided as a dict")
            return False

        table_name = (
            sync_params.get('oracle_table')
            or sync_params.get('table_name')
            or self.config.sync_oracle_table
        )
        if not table_name or str(table_name).strip() == '':
            logger.error("Table name is required for synchronization")
            return False

        # Try to acquire lock
        sync_lock = SyncLock()

        if not sync_lock.acquire(timeout=1):
            lock_info = sync_lock.get_lock_info() or {}
            logger.warning(f"Another sync is running (PID: {lock_info.get('pid', 'unknown')})")
            return False

        try:
            # Create progress queue
            self._progress_queue = Queue()

            # Create and start worker
            params = dict(sync_params)
            params.setdefault('oracle_table', table_name)
            worker = SyncWorker(self.config, params, self._progress_queue)
            worker.start()

            # Store references
            self._current_worker = worker
            self._current_lock = sync_lock

            # Update status
            self._status = SyncStatus(
                state='running',
                progress={}
            )

            # Start progress monitoring if callback provided
            if progress_callback:
                self._start_progress_monitoring(progress_callback)

            logger.info(f"Sync started for table: {table_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to start sync: {e}")
            sync_lock.release()
            return False

    def _start_progress_monitoring(self, callback: Callable) -> None:
        """Start background thread to monitor progress."""
        def monitor():
            while self._status.state == 'running':
                try:
                    if self._progress_queue and not self._progress_queue.empty():
                        msg = self._progress_queue.get_nowait()

                        if msg['type'] == 'progress':
                            self._status.progress = msg['data']
                        elif msg['type'] == 'complete':
                            self._status = SyncStatus(
                                state='completed',
                                result=msg['data']
                            )
                            self._cleanup()
                            break
                        elif msg['type'] == 'error':
                            self._status = SyncStatus(
                                state='error',
                                error=msg['data']
                            )
                            self._cleanup()
                            break

                        callback(self._status)
                except Exception as e:
                    logger.error(f"Error in progress monitoring: {e}")

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    def check_and_update_progress(self) -> Optional[dict[str, Any]]:
        """
        Check for progress updates without blocking.

        Returns:
            Progress data if available, None otherwise
        """
        if not self._progress_queue or self._progress_queue.empty():
            return None

        try:
            msg = self._progress_queue.get_nowait()

            if msg['type'] == 'progress':
                self._status.progress = msg['data']
                return msg['data']
            elif msg['type'] == 'complete':
                self._status = SyncStatus(
                    state='completed',
                    result=msg['data']
                )
                self._cleanup()
                return msg['data']
            elif msg['type'] == 'error':
                self._status = SyncStatus(
                    state='error',
                    error=msg['data']
                )
                self._cleanup()
                return msg['data']
        except Exception as e:
            logger.error(f"Error checking progress: {e}")

        return None

    def reset(self) -> None:
        """Reset sync state to idle."""
        self._cleanup()
        self._status = SyncStatus(state='idle')

    def _cleanup(self) -> None:
        """Clean up resources after sync completion."""
        if self._current_lock:
            self._current_lock.release()
            self._current_lock = None

        self._current_worker = None
        self._progress_queue = None
