from __future__ import annotations

import logging
from typing import List, Optional

from flask import has_app_context
from flask_login import current_user

from .database.db_manager import db, DownloadedTrack, get_system_user_id
from .models.dto import TrackDTO


logger = logging.getLogger(__name__)


class DownloadRepository:
    """Interface for persisting downloaded track metadata."""

    def save_tracks(self, tracks: List[TrackDTO]) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class DefaultDownloadRepository(DownloadRepository):
    def _resolve_user_id(self) -> int:
        if has_app_context():
            try:
                user = current_user
                if getattr(user, "is_authenticated", False):
                    return int(user.get_id())
            except Exception:
                pass
        return get_system_user_id()

    def save_tracks(self, tracks: List[TrackDTO]) -> None:
        try:
            user_id = self._resolve_user_id()
            for t in tracks:
                existing = DownloadedTrack.query.filter_by(spotify_id=t.spotify_id).first()
                if existing:
                    existing.local_lyrics_path = t.local_lyrics_path
                    if not existing.user_id:
                        existing.user_id = user_id
                else:
                    row = DownloadedTrack(
                        spotify_id=t.spotify_id,
                        spotify_url=t.spotify_url,
                        isrc=t.isrc,
                        title=t.title,
                        artists=t.artists,
                        album_name=t.album_name,
                        album_id=t.album_id,
                        album_artist=t.album_artist,
                        track_number=t.track_number,
                        disc_number=t.disc_number,
                        disc_count=t.disc_count,
                        tracks_count=t.tracks_count,
                        duration_ms=t.duration_ms,
                        explicit=t.explicit,
                        popularity=t.popularity,
                        publisher=t.publisher,
                        year=t.year,
                        date=t.date,
                        genres=t.genres,
                        cover_url=t.cover_url,
                        local_path=t.local_path,
                        local_lyrics_path=t.local_lyrics_path,
                        user_id=user_id,
                    )
                    db.session.add(row)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to persist DownloadedTrack rows: %s", e, exc_info=True)


__all__ = ["DownloadRepository", "DefaultDownloadRepository"]

