import pytest
from unittest.mock import MagicMock, patch
from oracle_duckdb_sync.scheduler.scheduler import SyncScheduler
from apscheduler.triggers.cron import CronTrigger

def test_110_scheduler_setup():
    """TEST-110: 스케줄러 등록 확인"""
    with patch("apscheduler.schedulers.background.BackgroundScheduler.add_job") as mock_add_job:
        scheduler = SyncScheduler()
        scheduler.add_sync_job(lambda: print("sync"), hour=2, minute=30)

        mock_add_job.assert_called_once()
        args, kwargs = mock_add_job.call_args
        trigger = kwargs["trigger"]
        assert isinstance(trigger, CronTrigger)

        # 필드 값 확인 (속성 접근)
        fields = {f.name: str(f.expressions[0]) for f in trigger.fields}
        assert fields["hour"] == "2"
        assert fields["minute"] == "30"

def test_111_duplicate_execution_prevention():
    """TEST-111: 중복 실행 방지(락/플래그) 동작"""
    import threading
    import time

    execution_count = []
    lock_acquired = []

    def sync_job():
        """Simulated sync job that tracks execution"""
        execution_count.append(1)
        time.sleep(0.1)  # Simulate work

    scheduler = SyncScheduler()

    # Wrap the job with lock protection
    protected_job = scheduler.create_protected_job(sync_job)

    # Try to run the job twice simultaneously
    thread1 = threading.Thread(target=protected_job)
    thread2 = threading.Thread(target=protected_job)

    thread1.start()
    time.sleep(0.01)  # Small delay to ensure thread1 starts first
    thread2.start()

    thread1.join()
    thread2.join()

    # Verify only one execution happened (second was blocked)
    assert len(execution_count) == 1, f"Expected 1 execution, got {len(execution_count)}"

def test_112_safe_scheduler_restart():
    """TEST-112: 스케줄 재등록/중단 시 안전 처리"""
    import time

    scheduler = SyncScheduler()
    job_executed = []

    def test_job():
        job_executed.append(1)

    # Start scheduler
    scheduler.add_sync_job(test_job, hour=2, minute=0)
    scheduler.start()

    # Verify scheduler is running
    assert scheduler.is_running()

    # Stop scheduler
    scheduler.stop()

    # Verify scheduler stopped cleanly
    assert not scheduler.is_running()

    # Restart scheduler
    scheduler2 = SyncScheduler()
    scheduler2.add_sync_job(test_job, hour=2, minute=0)
    scheduler2.start()

    # Verify second scheduler started
    assert scheduler2.is_running()

    # Clean up
    scheduler2.stop()
    assert not scheduler2.is_running()