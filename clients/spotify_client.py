# clients/spotify_client.py

from spotdl import Spotdl
from spotdl.types.playlist import Playlist as SpotdlPlaylist
from spotdl.types.album import Album as SpotdlAlbum
from spotdl.types.song import Song as SpotdlSong
from models.playlist import Playlist

class SpotifyClient:
    def __init__(self, spotdl: Spotdl):
        self._spotdl = spotdl

    def fetch_playlist(self, url: str) -> Playlist:
        if "playlist" in url:
            metadata, songs = SpotdlPlaylist.get_metadata(url)
            name = metadata["name"]
            description = metadata.get("description", "")
            cover_url = metadata["images"][0]["url"] if metadata.get("images") else ""
        elif "album" in url:
            metadata, songs = SpotdlAlbum.get_metadata(url)
            name = metadata["name"]
            description = f"Album by {', '.join(a['name'] for a in metadata['artists'])}"
            cover_url = metadata["images"][0]["url"] if metadata.get("images") else ""
        elif "track" in url:
            song = SpotdlSong.get_metadata(url)
            metadata = {
                "name": song.name,
                "description": f"{', '.join(song.artists)} - {song.album_name}",
                "images": [{"url": song.cover_url}] if song.cover_url else []
            }
            songs = [song]
            name = metadata["name"]
            description = metadata["description"]
            cover_url = song.cover_url
        else:
            raise ValueError("Unsupported Spotify URL type.")

        return Playlist.from_spotdl(
            metadata={"name": name, "description": description, "images": [{"url": cover_url}]},
            songs=songs
        )
