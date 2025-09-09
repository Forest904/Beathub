import threading
from typing import Dict, Any

class DownloadStatusManager:
    """Manage progress information for multiple download jobs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, job_id: str) -> None:
        """Create a new job entry with default values."""
        with self._lock:
            self._jobs[job_id] = {
                "status": "pending",
                "progress": 0,
                "message": "",
                "finished": False,
            }

    def update_job(self, job_id: str, *, status: str | None = None, progress: float | None = None,
                   message: str | None = None, finished: bool | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if status is not None:
                job["status"] = status
            if progress is not None:
                job["progress"] = progress
            if message is not None:
                job["message"] = message
            if finished is not None:
                job["finished"] = finished

    def get_job(self, job_id: str) -> Dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.copy() if job else None

    def reset_job(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

DOWNLOAD_STATUS_MANAGER = DownloadStatusManager()
