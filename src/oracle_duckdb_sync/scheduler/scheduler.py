import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


class SyncScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._job_lock = threading.Lock()
        self._is_running = False

    def add_sync_job(self, func, hour=2, minute=0):
        trigger = CronTrigger(hour=hour, minute=minute)
        self.scheduler.add_job(func, trigger=trigger)

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()

    def stop(self):
        """Stop the scheduler gracefully"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)

    def is_running(self):
        """Check if scheduler is currently running"""
        return self.scheduler.running

    def create_protected_job(self, func):
        """Wrap a job function with lock protection to prevent concurrent execution"""
        def protected_wrapper(*args, **kwargs):
            # Try to acquire lock, skip if already running
            if not self._job_lock.acquire(blocking=False):
                # Job is already running, skip this execution
                return None

            try:
                self._is_running = True
                return func(*args, **kwargs)
            finally:
                self._is_running = False
                self._job_lock.release()

        return protected_wrapper


    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
