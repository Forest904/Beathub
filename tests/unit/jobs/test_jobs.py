import logging
import time

import pytest


@pytest.mark.unit
def test_idempotent_submission_and_wait_success():
    from src.jobs import JobQueue

    class SuccessDownloader:
        def download_spotify_content(self, link):
            return {"status": "success", "item_name": "OK", "item_type": "track", "spotify_id": "x"}

    q = JobQueue(downloader=SuccessDownloader(), logger=logging.getLogger("t"), workers=1)
    link = "https://open.spotify.com/track/1"
    j1 = q.submit(link)
    j2 = q.submit(link)
    assert j1.id == j2.id

    res = q.wait(j1.id, timeout=5)
    assert res and res.get("status") == "success"
    j = q.get(j1.id)
    assert j.status == "completed"
    assert q.get_by_link(link).id == j1.id


@pytest.mark.unit
def test_retries_then_success(monkeypatch):
    import src.jobs as jobs
    from src.jobs import JobQueue

    # Configure max retries to 3
    monkeypatch.setattr(jobs.Config, "DOWNLOAD_MAX_RETRIES", 3, raising=True)

    class Flaky:
        def __init__(self):
            self.calls = 0
        def download_spotify_content(self, link):
            self.calls += 1
            if self.calls < 3:
                return {"status": "error", "message": "temp"}
            return {"status": "success", "item_name": "OK", "item_type": "track", "spotify_id": "x"}

    d = Flaky()
    q = JobQueue(downloader=d, logger=logging.getLogger("t"), workers=1)
    j = q.submit("https://open.spotify.com/track/2")
    res = q.wait(j.id, timeout=5)
    assert res and res.get("status") == "success"
    j2 = q.get(j.id)
    assert j2.status == "completed"
    assert j2.attempts == 3


@pytest.mark.unit
def test_permanent_failure_sets_failed(monkeypatch):
    import src.jobs as jobs
    from src.jobs import JobQueue

    monkeypatch.setattr(jobs.Config, "DOWNLOAD_MAX_RETRIES", 2, raising=True)

    class AlwaysFail:
        def download_spotify_content(self, link):
            return {"status": "error", "message": "nope"}

    q = JobQueue(downloader=AlwaysFail(), logger=logging.getLogger("t"), workers=1)
    j = q.submit("https://open.spotify.com/track/3")
    res = q.wait(j.id, timeout=5)
    assert res and res.get("status") == "error"
    j2 = q.get(j.id)
    assert j2.status == "failed"
    assert "nope" in (j2.error or "")


@pytest.mark.unit
def test_worker_uses_flask_app_context(monkeypatch):
    from flask import Flask, current_app
    from src.jobs import JobQueue

    app = Flask("queued-app")

    class ContextAware:
        def __init__(self):
            self.seen = None
        def download_spotify_content(self, link):
            try:
                self.seen = current_app.name
            except Exception:
                self.seen = None
            return {"status": "success", "item_name": "X", "item_type": "track", "spotify_id": "y"}

    d = ContextAware()
    q = JobQueue(downloader=d, logger=logging.getLogger("t"), workers=1, flask_app=app)
    j = q.submit("https://open.spotify.com/track/4")
    _ = q.wait(j.id, timeout=5)
    assert d.seen == "queued-app"

