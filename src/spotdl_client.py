#!/usr/bin/env python
"""
SpotDL client wrapper for reusable, programmatic downloads.

Phase 2 goal: instantiate a single Spotdl client, allow per-job
output template updates, enable lyrics providers (Genius) via
settings, and expose a progress callback hook.

This module does NOT change existing CLI-based download flow yet.
It prepares the new API path while remaining idle until used by
the orchestrator/routes in later phases.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, List, Optional, Tuple
from pathlib import Path
import asyncio
from queue import Queue
import contextlib
import io
import os

from .settings import load_app_settings, build_spotdl_downloader_options


logger = logging.getLogger(__name__)


class SpotdlClient:
    """Thin wrapper around spotdl.Spotdl with per-job helpers.

    - Reuses a single Spotdl instance across requests
    - Allows setting per-job output template safely
    - Exposes a progress callback interface via spotdl's ProgressHandler
    - Leaves concurrency to SpotDL's internal thread pool ("threads" option)
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        downloader_options: Optional[dict] = None,
        app_logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initialize Spotdl in a dedicated engine thread with its own loop.

        This avoids cross-thread asyncio loop/semaphore errors by ensuring that
        SpotDL's downloader and its event loop are created and used on the same
        thread for all operations.
        """
        self.logger = app_logger or logger
        self._client_id = client_id
        self._client_secret = client_secret
        self._downloader_options = downloader_options
        self._lock = threading.RLock()

        self._spotdl = None  # created in engine
        self._engine_queue: "Queue[tuple]" = Queue()
        self._engine_ready = threading.Event()

        def _engine():
            # Create and bind a dedicated asyncio loop for the engine thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from spotdl import Spotdl  # type: ignore
                self._spotdl = Spotdl(
                    client_id=self._client_id,
                    client_secret=self._client_secret,
                    downloader_settings=self._downloader_options,
                )
                try:
                    self._spotdl.downloader.settings["simple_tui"] = True
                except Exception:
                    pass
                self.logger.info(
                    "Spotdl client initialized on engine thread (providers: %s)",
                    self._spotdl.downloader.settings.get("lyrics_providers"),
                )
            finally:
                self._engine_ready.set()

            # Process callable tasks marshaled from other threads
            while True:
                item = self._engine_queue.get()
                if item is None:
                    break
                fn, args, kwargs, done = item
                try:
                    res = fn(*args, **kwargs)
                    done["result"] = res
                except Exception as e:  # pragma: no cover
                    done["error"] = e
                finally:
                    ev = done.get("event")
                    if ev:
                        ev.set()

        self._engine_thread = threading.Thread(target=_engine, name="spotdl-engine", daemon=True)
        self._engine_thread.start()
        self._engine_ready.wait(timeout=10)
        if self._spotdl is None:
            raise RuntimeError("Failed to initialize SpotDL engine thread")

    # --- Core accessors ---
    @property
    def spotdl(self):
        return self._spotdl

    # --- Configuration helpers (per job) ---
    def _call_engine(self, fn, *args, **kwargs):
        done = {"event": threading.Event(), "result": None, "error": None}
        self._engine_queue.put((fn, args, kwargs, done))
        done["event"].wait()
        if done["error"] is not None:
            raise done["error"]
        return done["result"]

    def set_output_template(self, output_template: str) -> str:
        """Set SpotDL output template for the next download job.

        Returns the effective template set on the SpotDL downloader settings.
        """
        def _fn():
            self._spotdl.downloader.settings["output"] = output_template
            return self._spotdl.downloader.settings["output"]
        with self._lock:
            return self._call_engine(_fn)

    # --- Progress callback ---
    def set_progress_callback(
        self,
        callback: Optional[Callable[[dict], None]],
        web_ui: bool = True,
    ) -> None:
        """Attach a progress callback that receives dict events per update.

        Event example:
        {
          'song_display_name': str,
          'status': str,               # e.g., 'Downloading', 'Converting', 'Done'
          'progress': int,             # 0-100
          'overall_completed': int,    # completed tracks count
          'overall_total': int,        # total tracks count
          'overall_progress': int      # aggregate progress (0..100*tracks)
        }
        """
        def _fn():
            ph = self._spotdl.downloader.progress_handler
            ph.update_callback = None if callback is None else self._wrap_progress_callback(callback)
            try:
                ph.web_ui = bool(web_ui)
            except Exception:
                pass
        with self._lock:
            self._call_engine(_fn)

    def clear_progress_callback(self) -> None:
        def _fn():
            self._spotdl.downloader.progress_handler.update_callback = None
        with self._lock:
            self._call_engine(_fn)

    def _wrap_progress_callback(self, cb: Callable[[dict], None]):
        def _inner(tracker: Any, message: str) -> None:
            try:
                ev = {
                    "song_display_name": getattr(tracker, "song_name", None)
                    or getattr(getattr(tracker, "song", None), "display_name", None),
                    "status": message,
                    "progress": int(getattr(tracker, "progress", 0) or 0),
                    "overall_completed": int(getattr(tracker.parent, "overall_completed_tasks", 0) or 0),
                    "overall_total": int(getattr(tracker.parent, "song_count", 0) or 0),
                    "overall_progress": int(getattr(tracker.parent, "overall_progress", 0) or 0),
                }
                cb(ev)
            except Exception as e:  # pragma: no cover - do not break downloads on UI errors
                self.logger.debug("Progress callback error: %s", e, exc_info=True)

        return _inner

    # --- Thin API pass-throughs ---
    def search(self, queries: List[str]):
        def _fn():
            return self._spotdl.search(queries)
        with self._lock:
            return self._call_engine(_fn)

    def download_songs(self, songs) -> List[Tuple[Any, Optional[Path]]]:
        """Download songs by executing inside the engine thread.

        Ensures SpotDL's event loop and semaphore remain on the same thread.
        """
        def _fn():
            # Silence console TUI/progress that SpotDL and its subprocesses print
            # Use both Python-level stdout/stderr redirection and OS-level fd redirection
            try:
                devnull_file = open(os.devnull, 'w')
                devnull_fd = devnull_file.fileno()
            except Exception:
                devnull_file = None
                devnull_fd = None

            # Python-level redirection (affects print/rich in-process)
            cm_out = contextlib.redirect_stdout(devnull_file) if devnull_file else contextlib.nullcontext()
            cm_err = contextlib.redirect_stderr(devnull_file) if devnull_file else contextlib.nullcontext()

            # OS-level fd redirection (affects child processes like ffmpeg/yt-dlp)
            class _FdSilence:
                def __enter__(self_inner):
                    if devnull_fd is None:
                        self_inner._active = False
                        return self_inner
                    self_inner._active = True
                    try:
                        import os as _os
                        self_inner._stdout_save = _os.dup(1)
                        self_inner._stderr_save = _os.dup(2)
                        _os.dup2(devnull_fd, 1)
                        _os.dup2(devnull_fd, 2)
                    except Exception:
                        self_inner._active = False
                    return self_inner

                def __exit__(self_inner, exc_type, exc, tb):
                    if not getattr(self_inner, '_active', False):
                        return False
                    try:
                        import os as _os
                        try:
                            _os.dup2(self_inner._stdout_save, 1)
                            _os.dup2(self_inner._stderr_save, 2)
                        finally:
                            try:
                                _os.close(self_inner._stdout_save)
                            except Exception:
                                pass
                            try:
                                _os.close(self_inner._stderr_save)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    return False

            with cm_out, cm_err, _FdSilence():
                try:
                    return self._spotdl.download_songs(songs)
                finally:
                    if devnull_file:
                        try:
                            devnull_file.close()
                        except Exception:
                            pass
        with self._lock:
            return self._call_engine(_fn)

    def download_link(
        self,
        spotify_link: str,
        output_template: str,
        progress_callback: Optional[Callable[[dict], None]] = None,
    ) -> List[Tuple[Any, Optional[Path]]]:
        """Convenience one-shot download for a link with per-job settings.

        Note: this method serializes jobs at the client level while allowing
        SpotDL to run per-song concurrency internally according to the
        configured thread count.
        """
        with self._lock:
            self.set_output_template(output_template)
            self.set_progress_callback(progress_callback)
        songs = self.search([spotify_link])
        return self.download_songs(songs)


def build_default_client(app_logger: Optional[logging.Logger] = None) -> SpotdlClient:
    """Build a SpotdlClient from environment/config defaults."""
    settings = load_app_settings()
    opts = build_spotdl_downloader_options(settings)

    if not settings.spotify_client_id or not settings.spotify_client_secret:
        raise RuntimeError(
            "Missing Spotify credentials. Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET."
        )

    return SpotdlClient(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
        downloader_options=opts,
        app_logger=app_logger,
    )


__all__ = [
    "SpotdlClient",
    "build_default_client",
]
