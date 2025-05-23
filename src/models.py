# models.py
from dataclasses import dataclass, field
from typing import List

@dataclass
class Track:
    id: str
    title: str
    artists: List[str]
    album: str | None = None
    duration_ms: int | None = None
    download_url: str | None = None
    isrc: str | None = None
    spotify_url: str | None = None
    cover_url: str | None = None

@dataclass
class Playlist: # Used for both playlists and albums for simplicity
    id: str
    name: str
    description: str | None = None
    cover_url: str | None = None
    tracks: List[Track] = field(default_factory=list)

