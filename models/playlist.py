# models/playlist.py

import dataclasses
from typing import List

# Import the Track data class
from .track import Track

@dataclasses.dataclass
class Playlist:
    """
    Data class representing a Spotify playlist.
    """
    id: str
    name: str
    description: str | None = None
    cover_url: str | None = None
    tracks: List[Track] = dataclasses.field(default_factory=list) # Added default_factory=list

    def __repr__(self):
        return f"Playlist(id='{self.id}', name='{self.name}', tracks={len(self.tracks)} tracks)"

