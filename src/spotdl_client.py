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
        # Import locally to avoid import side effects at module import time
        from spotdl import Spotdl  # type: ignore

        self.logger = app_logger or logger
        self._lock = threading.RLock()

        # Construct Spotdl instance
        self._spotdl = Spotdl(
            client_id=client_id,
            client_secret=client_secret,
            downloader_settings=downloader_options,
        )

        # Prefer quieter console progress output; we surface updates via callback
        try:
            self._spotdl.downloader.settings["simple_tui"] = True
        except Exception:  # pragma: no cover - defensive only
            pass

        self.logger.info("Spotdl client initialized (lyrics providers: %s)",
                         self._spotdl.downloader.settings.get("lyrics_providers"))

    # --- Core accessors ---
    @property
    def spotdl(self):
        return self._spotdl

    # --- Configuration helpers (per job) ---
    def set_output_template(self, output_template: str) -> str:
        """Set SpotDL output template for the next download job.

        Returns the effective template set on the SpotDL downloader settings.
        """
        with self._lock:
            self._spotdl.downloader.settings["output"] = output_template
            return self._spotdl.downloader.settings["output"]

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
        with self._lock:
            ph = self._spotdl.downloader.progress_handler
            # Wrap SpotDL's SongTracker callback signature (tracker, message) -> None
            ph.update_callback = None if callback is None else self._wrap_progress_callback(callback)
            try:
                ph.web_ui = bool(web_ui)
            except Exception:  # pragma: no cover
                pass

    def clear_progress_callback(self) -> None:
        with self._lock:
            self._spotdl.downloader.progress_handler.update_callback = None

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
        return self._spotdl.search(queries)

    def download_songs(self, songs) -> List[Tuple[Any, Optional[Path]]]:
        # Always use a fresh event loop in this worker thread
        with self._lock:
            created_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(created_loop)
            prev_loop = getattr(self._spotdl.downloader, "loop", None)
            self._spotdl.downloader.loop = created_loop
            try:
                return self._spotdl.download_songs(songs)
            finally:
                # Restore previous loop and close the worker loop
                if prev_loop is not None:
                    self._spotdl.downloader.loop = prev_loop
                try:
                    created_loop.close()
                except Exception:
                    pass

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

        # We still call search in current thread (no async needed)
        songs = self._spotdl.search([spotify_link])
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
