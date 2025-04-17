from dataclasses import dataclass
from spotdl.types.song import Song as SpotdlSong

@dataclass
class Track:
    id: str
    title: str
    artists: list[str]
    album: str
    duration: int   # seconds
    download_url: str
    cover_url: str
    lyrics: str = ""

    @classmethod
    def from_spotdl(cls, song: SpotdlSong) -> "Track":
        data = song.json  # dict of all metadata
        return cls(
            id=data["external_ids"]["isrc"],
            title=song.name,
            artists=song.artists,
            album=song.album_name,
            duration=song.duration,
            download_url=song.source_url,
            cover_url=song.cover_url,
            lyrics=data.get("lyrics", "")
        )
