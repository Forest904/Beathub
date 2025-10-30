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
from queue import Empty, Queue
from typing import Any, Dict, Optional

from config import Config
from src.database.db_manager import db, DownloadJob
from src.support.identity import resolve_user_id
from src.support.user_settings import ensure_user_api_keys_applied_for_user_id, user_has_spotify_credentials
from .history_service import persist_download_item


JobResult = Dict[str, Any]


@dataclass
class Job:
    id: str
    link: str
    user_id: int
    attempts: int = 0
    status: str = "pending"  # pending | in_progress | completed | failed | cancelled
    result: Optional[JobResult] = None
    error: Optional[str] = None
    event: threading.Event = field(default_factory=threading.Event)
    cancel_event: threading.Event = field(default_factory=threading.Event)


class JobQueue:
    def __init__(self, downloader, logger, workers: int = Config.DOWNLOAD_QUEUE_WORKERS, flask_app=None):
        self.downloader = downloader
        self.logger = logger
        self.workers = workers
        self.flask_app = flask_app
        self._lock = threading.RLock()
        self._queue: Queue[Job] = Queue()
        self._jobs: Dict[str, Job] = {}
        self._by_link: Dict[tuple[int, str], str] = {}
        self._threads: list[threading.Thread] = []
        self._shutdown = False

        for i in range(self.workers):
            t = threading.Thread(target=self._worker, name=f"download-worker-{i+1}", daemon=True)
            t.start()
            self._threads.append(t)

    def _resolve_user_id(self, explicit_user_id: Optional[int]) -> int:
        return resolve_user_id(explicit_user_id)

    def submit(self, link: str, user_id: Optional[int] = None) -> Job:
        """Submit a job if not present; returns existing job for idempotency."""
        resolved_user_id = self._resolve_user_id(user_id)
        with self._lock:
            # Enforce single active download per user (pending or in_progress)
            # If an active job exists for this user, return it instead of enqueuing a new one.
            for j in self._jobs.values():
                if j.user_id == resolved_user_id and j.status in ("pending", "in_progress"):
                    return j
            key = (resolved_user_id, link)
            jid = self._by_link.get(key)
            if jid:
                existing = self._jobs.get(jid)
                if existing and existing.status in ("pending", "in_progress"):
                    return existing
                self._by_link.pop(key, None)
            job = Job(id=str(uuid.uuid4()), link=link, user_id=resolved_user_id)
            self._jobs[job.id] = job
            self._by_link[key] = job.id
            self._queue.put(job)
            self._persist_job(job)
            return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def get_by_link(self, link: str, user_id: Optional[int] = None) -> Optional[Job]:
        resolved_user_id = self._resolve_user_id(user_id)
        key = (resolved_user_id, link)
        jid = self._by_link.get(key)
        return self._jobs.get(jid) if jid else None

    def get_active_for_user(self, user_id: Optional[int] = None) -> Optional[Job]:
        """Return active (pending or in_progress) job for user if any."""
        resolved_user_id = self._resolve_user_id(user_id)
        with self._lock:
            for j in self._jobs.values():
                if j.user_id == resolved_user_id and j.status in ("pending", "in_progress"):
                    return j
        return None

    def cancel_active_for_user(self, user_id: Optional[int] = None, *, timeout: float = 8.0) -> Optional[str]:
        """Request cancellation of the active job for a user and wait briefly.

        Returns the cancelled job_id if a job was found, otherwise None.
        """
        resolved_user_id = self._resolve_user_id(user_id)
        job_id: Optional[str] = None
        with self._lock:
            for j in self._jobs.values():
                if j.user_id == resolved_user_id and j.status in ("pending", "in_progress"):
                    j.cancel_event.set()
                    j.status = "cancelled"
                    j.result = {"status": "error", "error_code": "cancelled", "message": "Job cancelled"}
                    self._update_job_status(j, status=j.status, result=j.result)
                    j.event.set()
                    job_id = j.id
                    break
        if job_id is not None and timeout > 0:
            try:
                import time
                time.sleep(min(timeout, 0.15))
            except Exception:
                pass
        return job_id

    def wait(self, job_id: str, timeout: Optional[float] = None) -> Optional[JobResult]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.event.wait(timeout=timeout)
        return job.result

    def request_cancel(self, job_id: str) -> bool:
        """Cooperatively request cancellation for a job in progress or pending.

        Returns True if the signal was set, False if job not found.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            job.cancel_event.set()
            self._update_job_status(job, status="cancelled", result={"status": "error", "error_code": "cancelled"})
            return True

    def _worker(self):
        while not self._shutdown:
            try:
                job = self._queue.get(timeout=0.5)
            except Empty:
                continue

            try:
                if self.flask_app is not None:
                    # Ensure Flask application context for DB/session and current_app
                    with self.flask_app.app_context():
                        self._run_job(job)
                else:
                    self._run_job(job)
            finally:
                self._queue.task_done()

    def _persist_job(self, job: Job) -> None:
        try:
            record = DownloadJob(id=job.id, link=job.link, user_id=job.user_id, status=job.status)
            db.session.merge(record)
            db.session.commit()
        except Exception:
            db.session.rollback()

    def _update_job_status(self, job: Job, *, status: Optional[str] = None, result: Optional[JobResult] = None, error: Optional[str] = None) -> None:
        try:
            record = db.session.get(DownloadJob, job.id)
            if record is None:
                record = DownloadJob(id=job.id, user_id=job.user_id, link=job.link)
                db.session.add(record)
            if status is not None:
                record.status = status
            if result is not None:
                record.result = result
            if error is not None:
                record.error = error
            db.session.commit()
        except Exception:
            db.session.rollback()

    def _run_job(self, job: Job):
        def _publish_cancelled(phase: str):
            try:
                if self.flask_app is None:
                    return
                from flask import current_app  # type: ignore
                broker = current_app.extensions.get('progress_broker')
                if broker is not None:
                    broker.publish({
                        'event': 'job_cancelled',
                        'job_id': job.id,
                        'link': job.link,
                        'status': 'cancelled',
                        'phase': phase,
                    })
            except Exception:
                pass
        with self._lock:
            # If another waiter already completed it, skip
            if job.status in ("completed", "failed"):
                return
            if job.cancel_event.is_set():
                job.status = "cancelled"
                job.result = {"status": "error", "error_code": "cancelled", "message": "Job cancelled"}
                self._update_job_status(job, status=job.status, result=job.result)
                job.event.set()
                _publish_cancelled('preflight')
                return
            job.status = "in_progress"
            self._update_job_status(job, status=job.status)

        keys = ensure_user_api_keys_applied_for_user_id(job.user_id, refresh_client=False)
        if not user_has_spotify_credentials(keys):
            message = "Spotify credentials are not configured."
            job.status = "failed"
            job.result = {
                "status": "error",
                "error_code": "credentials_missing",
                "message": message,
                "user_id": job.user_id,
            }
            self._update_job_status(job, status=job.status, result=job.result, error=message)
            job.event.set()
            self.logger.warning("Job %s aborted: %s", job.id, message)
            return

        max_attempts = max(1, Config.DOWNLOAD_MAX_RETRIES)
        last_error: Optional[str] = None
        for attempt in range(1, max_attempts + 1):
            job.attempts = attempt
            try:
                self.logger.info("Processing job %s (attempt %d): %s", job.id, attempt, job.link)
                # Respect cooperative cancellation prior to starting network work
                if job.cancel_event.is_set():
                    raise RuntimeError("cancelled")
                result = self.downloader.download_spotify_content(job.link, cancel_event=job.cancel_event, user_id=job.user_id)
                if isinstance(result, dict):
                    if result.get("status") == "success":
                        job.result = result
                        job.status = "completed"
                        self._update_job_status(job, status=job.status, result=job.result)
                        persist_download_item(result, explicit_user_id=job.user_id)
                        job.event.set()
                        self.logger.info("Job %s completed", job.id)
                        return
                    # Map error code and message for retry decision
                    err_code = result.get("error_code")
                    last_error = result.get("message", "Unknown error")
                    if err_code == "cancelled":
                        job.result = result
                        job.status = "cancelled"
                        self._update_job_status(job, status=job.status, result=job.result)
                        job.event.set()
                        self.logger.info("Job %s cancelled", job.id)
                        _publish_cancelled('downloader')
                        return
                    non_retriable = {
                        "credentials_missing",
                        "spotdl_unavailable",
                        "search_unavailable",
                        "no_results",
                        "metadata_unavailable",
                        "no_tracks",
                    }
                    if err_code in non_retriable:
                        self.logger.warning(
                            "Job %s non-retriable error (%s): %s", job.id, err_code, last_error
                        )
                        break
                else:
                    # Unexpected orchestrator response shape
                    last_error = "Unexpected orchestrator response"
            except Exception as e:  # pragma: no cover - defensive
                if str(e) == "cancelled" or job.cancel_event.is_set():
                    job.result = {"status": "error", "error_code": "cancelled", "message": "Job cancelled"}
                    job.status = "cancelled"
                    self._update_job_status(job, status=job.status, result=job.result)
                    job.event.set()
                    self.logger.info("Job %s cancelled before start", job.id)
                    _publish_cancelled('exception')
                    return
                last_error = str(e)

            # Decide retry; for now, retry on generic failures until attempts exhausted
            self.logger.warning("Job %s failed attempt %d/%d: %s", job.id, attempt, max_attempts, last_error)

        # Exhausted retries
        job.error = last_error
        job.status = "failed"
        job.result = {"status": "error", "message": last_error or "Job failed"}
        self._update_job_status(job, status=job.status, result=job.result, error=job.error)
        job.event.set()
        self.logger.error("Job %s failed: %s", job.id, job.error)


__all__ = ["Job", "JobQueue"]
