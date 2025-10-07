#!/usr/bin/env python
"""
SpotDL Song -> DTO/DB conversion utilities.

Phase 3 focuses on making SpotDL's Song the canonical metadata source.
These helpers convert Song objects to structured DTOs and SQLAlchemy rows.
"""

from __future__ import annotations

from typing import Iterable, List, Optional
from pathlib import Path

from pydantic import BaseModel

from spotdl.types.song import Song  # type: ignore

from .dto import TrackDTO, ItemDTO


def song_to_track_dto(song: Song, local_path: Optional[Path] = None, local_lyrics_path: Optional[Path] = None) -> TrackDTO:
    info = song.json  # spotdl provides a dict view

    return TrackDTO(
        spotify_id=info["song_id"],
        title=info["name"],
        artists=info["artists"],
        album_name=info["album_name"],
        album_id=info.get("album_id"),
        album_artist=info.get("album_artist"),
        duration_ms=int(info["duration"]) * 1000,
        track_number=int(info["track_number"]),
        disc_number=int(info["disc_number"]),
        disc_count=int(info.get("disc_count")) if info.get("disc_count") is not None else None,
        tracks_count=int(info.get("tracks_count")) if info.get("tracks_count") is not None else None,
        explicit=bool(info.get("explicit", False)),
        popularity=info.get("popularity"),
        isrc=info.get("isrc"),
        publisher=info.get("publisher"),
        year=info.get("year"),
        date=info.get("date"),
        genres=info.get("genres"),
        spotify_url=info["url"],
        cover_url=info.get("cover_url"),
        local_path=str(local_path) if local_path else None,
        local_lyrics_path=str(local_lyrics_path) if local_lyrics_path else None,
    )


def songs_to_item_dto(
    songs: List[Song],
    spotify_link: Optional[str] = None,
    cover_url_override: Optional[str] = None,
) -> ItemDTO:
    if not songs:
        raise ValueError("songs must be a non-empty list")

    first = songs[0]
    # Derive item characteristics
    item_type = "album" if len(songs) > 1 else "track"
    if item_type == "album":
        artist_name = first.album_artist or first.artist
    else:
        artist_name = first.artist
    title_name = first.album_name if first.album_name else first.name
    cover_url = cover_url_override if cover_url_override is not None else first.cover_url

    # Map tracks without local paths (these are added later by the downloader)
    tracks = [song_to_track_dto(s) for s in songs]

    return ItemDTO(
        item_type=item_type,
        artist=artist_name,
        title=title_name,
        cover_url=cover_url,
        spotify_link=spotify_link,
        tracks=tracks,
    )


def trackdto_to_db_kwargs(track: TrackDTO) -> dict:
    """Return field mapping suitable for creating a DownloadedTrack row.

    Keeps DB mapping decoupled from SQLAlchemy import to avoid cycles.
    """
    return {
        "spotify_id": track.spotify_id,
        "title": track.title,
        "artists": track.artists,
        "album_name": track.album_name,
        "album_id": track.album_id,
        "album_artist": track.album_artist,
        "duration_ms": track.duration_ms,
        "track_number": track.track_number,
        "disc_number": track.disc_number,
        "disc_count": track.disc_count,
        "tracks_count": track.tracks_count,
        "explicit": track.explicit,
        "popularity": track.popularity,
        "isrc": track.isrc,
        "publisher": track.publisher,
        "year": track.year,
        "date": track.date,
        "genres": track.genres,
        "spotify_url": track.spotify_url,
        "cover_url": track.cover_url,
        "local_path": track.local_path,
        "local_lyrics_path": track.local_lyrics_path,
    }


__all__ = [
    "song_to_track_dto",
    "songs_to_item_dto",
    "trackdto_to_db_kwargs",
]

