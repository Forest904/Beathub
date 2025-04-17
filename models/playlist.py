from dataclasses import dataclass
from typing import List

from models.track import Track

@dataclass
class Playlist:
    id: str
    name: str
    description: str
    cover_url: str
    tracks: List[Track]

    @classmethod
    def from_spotdl_metadata(cls, meta: dict, tracks: List[Track]) -> "Playlist":
        return cls(
            id=meta["url"].split("/")[-1],
            name=meta["name"],
            description=meta.get("description", ""),
            cover_url=meta.get("cover_url", ""),
            tracks=tracks
        )
