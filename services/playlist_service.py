from clients.spotify_client import SpotifyClient
from models.playlist import Playlist

class PlaylistService:
    """
    Orchestrates everything needed to get a Playlist.
    High cohesion: one task only.
    """

    def __init__(self, spotify_client: SpotifyClient):
        self._spotify = spotify_client

    def get_playlist(self, url: str) -> Playlist:
        return self._spotify.fetch_playlist(url)
