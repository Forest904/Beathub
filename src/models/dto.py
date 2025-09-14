#!/usr/bin/env python
"""
Pydantic DTOs representing canonical API models derived from SpotDL Song.

Phase 3: Use SpotDL Song metadata as the canonical source and provide
typed, structured representations for API responses and persistence mapping.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class TrackDTO(BaseModel):
    """Normalized track-level metadata suitable for API and DB mapping."""

    spotify_id: str
    title: str
    artists: List[str]
    album_name: str
    album_id: Optional[str] = None
    album_artist: Optional[str] = None

    duration_ms: int = Field(ge=0)
    track_number: int = Field(ge=0)
    disc_number: int = Field(ge=0)
    disc_count: Optional[int] = None
    tracks_count: Optional[int] = None

    explicit: bool = False
    popularity: Optional[int] = None
    isrc: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[int] = None
    date: Optional[str] = None
    genres: Optional[List[str]] = None

    spotify_url: str
    cover_url: Optional[str] = None

    local_path: Optional[str] = None
    local_lyrics_path: Optional[str] = None


class ItemDTO(BaseModel):
    """Container for a downloaded item (track/album/playlist) and its tracks."""

    item_type: str  # 'track' | 'album' | 'playlist'
    artist: str
    title: str
    cover_url: Optional[str] = None
    spotify_link: Optional[str] = None
    local_cover_image_path: Optional[str] = None
    output_directory: Optional[str] = None
    tracks: List[TrackDTO]


__all__ = ["TrackDTO", "ItemDTO"]

