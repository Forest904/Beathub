# services/playlist_service.py

# Import client and model
from clients.spotify_client import SpotifyClient # Uncomment when client is ready
from models.playlist import Playlist # Uncomment when model is ready
from typing import List # Import List for type hinting

class PlaylistService:
    """
    Orchestrates fetching Playlist data via SpotifyClient.
    """
    def __init__(self):
        # Initialize the SpotifyClient
        self.spotify_client = SpotifyClient() # Uncomment when client is ready
        print("PlaylistService initialized.")

    def get_playlist_data(self, playlist_link: str) -> Playlist | None:
        """
        Fetches playlist data using the SpotifyClient.

        Args:
            playlist_link: The URL of the Spotify playlist.

        Returns:
            A Playlist object.
        """
        print(f"PlaylistService: Getting data for playlist link: {playlist_link}")
        # Call SpotifyClient to fetch data
        playlist = self.spotify_client.fetch_playlist(playlist_link)
        return playlist

