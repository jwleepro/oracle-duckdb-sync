"""Sync state management for preventing duplicate sync operations"""
import os
import json
import time
import threading
from pathlib import Path


class SyncLock:
    """File-based lock to prevent concurrent sync operations
    
    This lock uses a simple file-based mechanism to ensure only one
    sync operation runs at a time, even across multiple Streamlit sessions.
    """
    
    def __init__(self, lock_file=os.getenv('DUCKDB_LOCK_FILE', './data/sync.lock')):
        """Initialize SyncLock
        
        Args:
            lock_file: Path to the lock file
        """
        self.lock_file = lock_file
        self.lock_fd = None
        self._lock = threading.Lock()
        
        # Ensure directory exists
        lock_dir = os.path.dirname(lock_file)
        if lock_dir and not os.path.exists(lock_dir):
            os.makedirs(lock_dir, exist_ok=True)
    
    def acquire(self, timeout=5):
        """Acquire lock with timeout
        
        Args:
            timeout: Maximum time to wait for lock (seconds)
            
        Returns:
            True if lock acquired, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if not os.path.exists(self.lock_file):
                    # Create lock file with metadata
                    lock_info = {
                        'pid': os.getpid(),
                        'timestamp': time.time(),
                        'hostname': os.environ.get('COMPUTERNAME', 'unknown')
                    }
                    
                    with open(self.lock_file, 'w') as f:
                        json.dump(lock_info, f, indent=2)
                    
                    return True
                else:
                    # Check if lock is stale (older than 1 hour)
                    try:
                        with open(self.lock_file, 'r') as f:
                            lock_info = json.load(f)
                        
                        lock_age = time.time() - lock_info.get('timestamp', 0)
                        
                        if lock_age > 3600:  # 1 hour
                            # Stale lock, remove it
                            os.remove(self.lock_file)
                            continue
                    except (json.JSONDecodeError, KeyError):
                        # Corrupted lock file, remove it
                        os.remove(self.lock_file)
                        continue
                
                # Lock exists and is valid, wait a bit
                time.sleep(0.1)
                
            except Exception as e:
                # On any error, wait and retry
                time.sleep(0.1)
        
        return False
    
    def release(self):
        """Release lock by removing lock file"""
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except Exception:
            # Ignore errors on release
            pass
    
    def is_locked(self):
        """Check if lock is currently held
        
        Returns:
            True if lock file exists and is not stale
        """
        if not os.path.exists(self.lock_file):
            return False
        
        try:
            with open(self.lock_file, 'r') as f:
                lock_info = json.load(f)
            
            lock_age = time.time() - lock_info.get('timestamp', 0)
            
            # Consider stale if older than 1 hour
            if lock_age > 3600:
                return False
            
            return True
        except Exception:
            return False
    
    def get_lock_info(self):
        """Get information about current lock holder
        
        Returns:
            Dict with lock info or None if not locked
        """
        if not self.is_locked():
            return None
        
        try:
            with open(self.lock_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def __enter__(self):
        """Context manager entry"""
        if not self.acquire():
            raise RuntimeError("Could not acquire sync lock")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
