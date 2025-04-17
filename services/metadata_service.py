import json
from models.playlist import Playlist

class MetadataService:
    """Serializes Playlist & Track models to JSON, DB, etc."""

    def save_to_json(self, playlist: Playlist, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "id": playlist.id,
                "name": playlist.name,
                "description": playlist.description,
                "cover_url": playlist.cover_url,
                "tracks": [
                    {
                        "title": t.title,
                        "artists": t.artists,
                        "album": t.album,
                        "duration": t.duration,
                        "cover_url": t.cover_url,
                        "lyrics": t.lyrics,
                        "download_url": t.download_url,
                    }
                    for t in playlist.tracks
                ],
            }, f, ensure_ascii=False, indent=2)



