# models/track.py

import dataclasses
from typing import List

@dataclasses.dataclass
class Track:
    """
    Data class representing a music track.
    """
    id: str
    title: str
    artists: List[str]
    album: str | None = None
    duration_ms: int | None = None # Duration in milliseconds
    download_url: str | None = None # URL for downloading (e.g., YouTube URL found by spotdl)
    isrc: str | None = None # International Standard Recording Code, often useful for matching

    def __repr__(self):
        return f"Track(id='{self.id}', title='{self.title}', artists={', '.join(self.artists)})"

