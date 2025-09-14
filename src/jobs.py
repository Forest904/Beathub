#!/usr/bin/env python
"""
In-process download job queue with deduplication and retries.

Phase 5: orchestrates parallel jobs and provides idempotent handling
of duplicate links.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from queue import Queue, Empty
from typing import Any, Dict, Optional

from config import Config


JobResult = Dict[str, Any]


@dataclass
class Job:
    id: str
    link: str
    attempts: int = 0
    status: str = "pending"  # pending | in_progress | completed | failed
    result: Optional[JobResult] = None
    error: Optional[str] = None
    event: threading.Event = field(default_factory=threading.Event)


class JobQueue:
    def __init__(self, downloader, logger, workers: int = Config.DOWNLOAD_QUEUE_WORKERS):
        self.downloader = downloader
        self.logger = logger
        self.workers = workers
        self._lock = threading.RLock()
        self._queue: Queue[Job] = Queue()
        self._jobs: Dict[str, Job] = {}
        self._by_link: Dict[str, str] = {}
        self._threads: list[threading.Thread] = []
        self._shutdown = False

        for i in range(self.workers):
            t = threading.Thread(target=self._worker, name=f"download-worker-{i+1}", daemon=True)
            t.start()
            self._threads.append(t)

    def submit(self, link: str) -> Job:
        """Submit a job if not present; returns existing job for idempotency."""
        with self._lock:
            jid = self._by_link.get(link)
            if jid:
                return self._jobs[jid]
            job = Job(id=str(uuid.uuid4()), link=link)
            self._jobs[job.id] = job
            self._by_link[link] = job.id
            self._queue.put(job)
            return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def get_by_link(self, link: str) -> Optional[Job]:
        jid = self._by_link.get(link)
        return self._jobs.get(jid) if jid else None

    def wait(self, job_id: str, timeout: Optional[float] = None) -> Optional[JobResult]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.event.wait(timeout=timeout)
        return job.result

    def _worker(self):
        while not self._shutdown:
            try:
                job = self._queue.get(timeout=0.5)
            except Empty:
                continue

            try:
                self._run_job(job)
            finally:
                self._queue.task_done()

    def _run_job(self, job: Job):
        with self._lock:
            # If another waiter already completed it, skip
            if job.status in ("completed", "failed"):
                return
            job.status = "in_progress"

        max_attempts = max(1, Config.DOWNLOAD_MAX_RETRIES)
        last_error: Optional[str] = None
        for attempt in range(1, max_attempts + 1):
            job.attempts = attempt
            try:
                self.logger.info("Processing job %s (attempt %d): %s", job.id, attempt, job.link)
                result = self.downloader.download_spotify_content(job.link)
                if isinstance(result, dict) and result.get("status") == "success":
                    job.result = result
                    job.status = "completed"
                    job.event.set()
                    self.logger.info("Job %s completed", job.id)
                    return
                # Map error message for retry decision
                last_error = (result or {}).get("message", "Unknown error")
                # On certain errors, retry may help; otherwise fail fast
            except Exception as e:  # pragma: no cover - defensive
                last_error = str(e)

            # Decide retry; for now, retry on generic failures until attempts exhausted
            self.logger.warning("Job %s failed attempt %d/%d: %s", job.id, attempt, max_attempts, last_error)

        # Exhausted retries
        job.error = last_error
        job.status = "failed"
        job.result = {"status": "error", "message": last_error or "Job failed"}
        job.event.set()
        self.logger.error("Job %s failed: %s", job.id, job.error)


__all__ = ["Job", "JobQueue"]

