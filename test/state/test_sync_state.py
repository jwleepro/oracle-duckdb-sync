"""Tests for sync_state module"""
import pytest
import os
import time
from oracle_duckdb_sync.state.sync_state import SyncLock


def test_sync_lock_acquire_release():
    """Test lock acquisition and release"""
    lock_file = './data/test_sync.lock'
    
    # Clean up any existing lock
    if os.path.exists(lock_file):
        os.remove(lock_file)
    
    lock = SyncLock(lock_file)
    
    try:
        # Acquire lock
        assert lock.acquire(timeout=1), "Should acquire lock successfully"
        assert lock.is_locked(), "Lock should be held"
        
        # Release lock
        lock.release()
        assert not lock.is_locked(), "Lock should be released"
    finally:
        # Cleanup
        if os.path.exists(lock_file):
            os.remove(lock_file)


def test_sync_lock_concurrent():
    """Test that concurrent locks are prevented"""
    lock_file = './data/test_sync_concurrent.lock'
    
    # Clean up any existing lock
    if os.path.exists(lock_file):
        os.remove(lock_file)
    
    lock1 = SyncLock(lock_file)
    lock2 = SyncLock(lock_file)
    
    try:
        # First lock succeeds
        assert lock1.acquire(timeout=1), "First lock should succeed"
        
        # Second lock fails
        assert not lock2.acquire(timeout=1), "Second lock should fail while first is held"
        
        # Release first lock
        lock1.release()
        
        # Now second lock succeeds
        assert lock2.acquire(timeout=1), "Second lock should succeed after first is released"
        lock2.release()
    finally:
        # Cleanup
        if os.path.exists(lock_file):
            os.remove(lock_file)


def test_sync_lock_context_manager():
    """Test lock as context manager"""
    lock_file = './data/test_sync_context.lock'
    
    # Clean up any existing lock
    if os.path.exists(lock_file):
        os.remove(lock_file)
    
    lock = SyncLock(lock_file)
    
    try:
        with lock:
            assert lock.is_locked(), "Lock should be held inside context"
        
        assert not lock.is_locked(), "Lock should be released after context"
    finally:
        # Cleanup
        if os.path.exists(lock_file):
            os.remove(lock_file)


def test_sync_lock_stale_detection():
    """Test that stale locks are detected and removed"""
    lock_file = './data/test_sync_stale.lock'
    
    # Clean up any existing lock
    if os.path.exists(lock_file):
        os.remove(lock_file)
    
    lock1 = SyncLock(lock_file)
    
    try:
        # Acquire lock
        assert lock1.acquire(timeout=1)
        
        # Manually modify lock file to make it stale (older than 1 hour)
        import json
        with open(lock_file, 'r') as f:
            lock_info = json.load(f)
        
        lock_info['timestamp'] = time.time() - 3700  # 1 hour and 100 seconds ago
        
        with open(lock_file, 'w') as f:
            json.dump(lock_info, f)
        
        # New lock should detect stale lock and acquire successfully
        lock2 = SyncLock(lock_file)
        assert lock2.acquire(timeout=1), "Should acquire lock after detecting stale lock"
        
        lock2.release()
    finally:
        # Cleanup
        if os.path.exists(lock_file):
            os.remove(lock_file)


def test_sync_lock_get_info():
    """Test getting lock information"""
    lock_file = './data/test_sync_info.lock'
    
    # Clean up any existing lock
    if os.path.exists(lock_file):
        os.remove(lock_file)
    
    lock = SyncLock(lock_file)
    
    try:
        # No lock initially
        assert lock.get_lock_info() is None, "Should return None when not locked"
        
        # Acquire lock
        assert lock.acquire(timeout=1)
        
        # Get lock info
        info = lock.get_lock_info()
        assert info is not None, "Should return lock info"
        assert 'pid' in info, "Lock info should contain PID"
        assert 'timestamp' in info, "Lock info should contain timestamp"
        assert info['pid'] == os.getpid(), "PID should match current process"
        
        lock.release()
    finally:
        # Cleanup
        if os.path.exists(lock_file):
            os.remove(lock_file)
