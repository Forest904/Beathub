# app.py

import argparse
import os
import re

# Import services and utils
from services.playlist_service import PlaylistService
from services.download_service import DownloadService
from services.metadata_service import MetadataService
from utils.file_manager import FileManager

# Import models to check returned types and create objects
from models.playlist import Playlist
from models.track import Track
from typing import List # Import List for type hinting

class AppController:
    """
    The main application controller. Wires services together and serves as the
    entrypoint for CLI or UI.
    """
    def __init__(self):
        # Initialize services and utils
        self.playlist_service = PlaylistService() # PlaylistService now contains SpotifyClient
        self.download_service = DownloadService()
        self.metadata_service = MetadataService()
        self.file_manager = FileManager()
        print("AppController initialized.")


    def download_spotify_item(self, spotify_link: str, base_output_dir: str):
        """
        Determines the type of Spotify link (track, album, playlist),
        fetches its data using SpotifyClient, and initiates the download process.

        Args:
            spotify_link: The URL of the Spotify item (track, album, or playlist).
            base_output_dir: The base directory for downloads.
        """
        print(f"AppController: Processing Spotify link: {spotify_link}")
        print(f"AppController: Base output directory: {base_output_dir}")

        # Use the SpotifyClient to fetch the item data (list of tracks with download URLs)
        # SpotifyClient.fetch_spotify_item now returns a List[Track] or None
        fetched_tracks = self.playlist_service.spotify_client.fetch_spotify_item(spotify_link)

        if not fetched_tracks:
            print(f"Error: Could not fetch data or tracks for Spotify link: {spotify_link}")
            return

        print(f"AppController: Successfully fetched {len(fetched_tracks)} tracks from SpotifyClient.")

        # Now, determine the item type based on the original link
        if "/playlist/" in spotify_link:
            item_type = "playlist"
            print(f"AppController: Detected item type: {item_type}")
            # Create a Playlist object from the fetched tracks
            # We might need to fetch playlist-specific info (name, cover) separately
            # if spotdl save doesn't provide it at the top level.
            # For now, let's create a basic Playlist object.
            # A more robust approach might involve a separate call to get playlist details
            # or ensuring spotdl save provides top-level info.
            playlist_name = "Downloaded Playlist" # Placeholder name
            playlist_cover_url = None # Placeholder cover URL

            # Attempt to get playlist name from the first track's list_name or a generic name
            if fetched_tracks and fetched_tracks[0].album: # Using album name as a fallback
                 playlist_name = f"Playlist - {fetched_tracks[0].album}"
            # Check if list_name is available in the first track's metadata
            if fetched_tracks and 'list_name' in fetched_tracks[0].__dict__: # Accessing __dict__ to check raw metadata key
                 playlist_name = fetched_tracks[0].__dict__.get('list_name', playlist_name)
            # TODO: Implement fetching actual playlist name and cover if spotdl save doesn't provide it reliably

            playlist = Playlist(
                 id="placeholder_id", # spotdl save might not provide playlist ID
                 name=playlist_name,
                 description=None,
                 cover_url=playlist_cover_url, # Cover URL might be in track metadata, need to extract one
                 tracks=fetched_tracks
            )
            self.download_playlist(playlist, base_output_dir)

        elif "/album/" in spotify_link:
            item_type = "album"
            print(f"AppController: Detected item type: {item_type}")
            # Create a Playlist-like object for the album
            album_name = "Downloaded Album" # Placeholder name
            album_cover_url = None # Placeholder cover URL

            # Attempt to get album name from the first track's album
            if fetched_tracks and fetched_tracks[0].album:
                 album_name = fetched_tracks[0].album
            # TODO: Implement fetching actual album name and cover if spotdl save doesn't provide it reliably

            album_as_playlist = Playlist( # Reusing Playlist model
                 id="placeholder_id", # spotdl save might not provide album ID
                 name=album_name,
                 description=None,
                 cover_url=album_cover_url, # Cover URL might be in track metadata, need to extract one
                 tracks=fetched_tracks
            )
            self.download_album(album_as_playlist, base_output_dir)

        elif "/track/" in spotify_link:
            item_type = "track"
            print(f"AppController: Detected item type: {item_type}")
            if len(fetched_tracks) == 1:
                single_track = fetched_tracks[0]
                self.download_track(single_track, base_output_dir)
            else:
                print(f"Error: Expected 1 track for single track link, but received {len(fetched_tracks)}")

        else:
            print(f"Error: Could not determine type of Spotify link: {spotify_link}")
            print("Please provide a valid Spotify playlist, album, or track URL.")


    def download_playlist(self, playlist: Playlist, base_output_dir: str):
        """
        Downloads tracks from a given Playlist object.

        Args:
            playlist: The Playlist object containing tracks to download.
            base_output_dir: The base directory for downloads.
        """
        print(f"AppController: Starting download for playlist '{playlist.name}' with {len(playlist.tracks)} tracks.")

        if not playlist.tracks:
            print(f"Playlist '{playlist.name}' has no tracks. Skipping download.")
            return

        # Download cover art for the playlist
        # We can try to get the cover art URL from the first track if the playlist object doesn't have it
        cover_art_url_to_save = playlist.cover_url
        if not cover_art_url_to_save and playlist.tracks and playlist.tracks[0].__dict__.get('cover_url'):
             cover_art_url_to_save = playlist.tracks[0].__dict__.get('cover_url')


        cover_art_path = None
        if cover_art_url_to_save:
             # Save cover art in the base output directory for the playlist
             playlist_output_dir = self.file_manager.get_output_directory(base_output_dir, playlist.name)
             cover_art_path = self.file_manager.save_cover_art(cover_art_url_to_save, playlist_output_dir, "cover.jpg")


        # Download tracks using DownloadService
        # Pass the playlist name so DownloadService can create a subdirectory
        downloaded_files = self.download_service.download_tracks_from_list(
            playlist.tracks,
            base_output_dir,
            item_name=playlist.name # Use playlist name for subdirectory
        )

        print(f"Download process finished. Successfully downloaded {len(downloaded_files)} files for playlist '{playlist.name}'.")

        # Optionally save playlist metadata (e.g., to a JSON file)
        try:
            json_data = self.metadata_service.serialize_playlist_to_json(playlist)
            playlist_output_dir = self.file_manager.get_output_directory(base_output_dir, playlist.name)
            metadata_file_path = os.path.join(playlist_output_dir, "playlist_metadata.json")
            with open(metadata_file_path, 'w', encoding='utf-8') as f:
                f.write(json_data)
            print(f"Playlist metadata saved to {metadata_file_path}")
        except Exception as e:
            print(f"Error saving playlist metadata: {e}")


    def download_album(self, album_as_playlist: Playlist, base_output_dir: str):
        """
        Downloads tracks from a given Album object (represented as Playlist).

        Args:
            album_as_playlist: The Playlist object representing the album.
            base_output_dir: The base directory for downloads.
        """
        print(f"AppController: Starting download for album '{album_as_playlist.name}' with {len(album_as_playlist.tracks)} tracks.")

        if not album_as_playlist.tracks:
            print(f"Album '{album_as_playlist.name}' has no tracks. Skipping download.")
            return

        # Download cover art for the album
        # We can try to get the cover art URL from the first track if the album object doesn't have it
        cover_art_url_to_save = album_as_playlist.cover_url
        if not cover_art_url_to_save and album_as_playlist.tracks and album_as_playlist.tracks[0].__dict__.get('cover_url'):
             cover_art_url_to_save = album_as_playlist.tracks[0].__dict__.get('cover_url')

        cover_art_path = None
        if cover_art_url_to_save:
             album_output_dir = self.file_manager.get_output_directory(base_output_dir, album_as_playlist.name)
             cover_art_path = self.file_manager.save_cover_art(cover_art_url_to_save, album_output_dir, "cover.jpg")


        # Download tracks using DownloadService (pass album name for subdirectory)
        downloaded_files = self.download_service.download_tracks_from_list(
            album_as_playlist.tracks,
            base_output_dir,
            item_name=album_as_playlist.name # Use album name for subdirectory
        )

        print(f"Download process finished. Successfully downloaded {len(downloaded_files)} files for album '{album_as_playlist.name}'.")

        # TODO: Optionally save album metadata (similar to playlist)


    def download_track(self, track: Track, base_output_dir: str):
        """
        Downloads a single given Track object.

        Args:
            track: The Track object to download.
            base_output_dir: The base directory for downloads.
        """
        print(f"AppController: Starting download for single track '{track.title}'.")

        # For a single track, we might want a subdirectory based on artist or album.
        # Let's use the album name for the subdirectory if available, otherwise the base directory.
        output_dir = self.file_manager.get_output_directory(base_output_dir, track.album if track.album else None)

        # Download cover art for the single track if available in its metadata
        cover_art_url_to_save = track.__dict__.get('cover_url') # Access raw metadata key
        cover_art_path = None
        if cover_art_url_to_save:
             cover_art_path = self.file_manager.save_cover_art(cover_art_url_to_save, output_dir, "cover.jpg")


        # Download the single track using DownloadService
        # download_tracks_from_list expects a list, so wrap the single track
        downloaded_files = self.download_service.download_tracks_from_list(
            [track], # Pass a list containing the single track
            base_output_dir, # Pass base_output_dir
            item_name=track.album if track.album else None # Use album name for subdirectory if available
        )

        print(f"Download process finished. Successfully downloaded {len(downloaded_files)} files for track '{track.title}'.")

        # TODO: Optionally save track metadata


    def run_cli(self):
        """
        Command-line interface entrypoint using argparse.
        """
        print("SpotDL Wrapper CLI")
        print("------------------")

        parser = argparse.ArgumentParser(
            description="Download Spotify content (playlists, albums, tracks) using spotdl."
        )
        parser.add_argument(
            "spotify_link",
            help="The Spotify URL of the playlist, album, or track to download."
        )
        parser.add_argument(
            "--output",
            "-o",
            default="./downloads",
            help="Output directory for downloads. Defaults to ./downloads."
        )

        args = parser.parse_args()

        # Ensure the base output directory exists
        try:
            os.makedirs(args.output, exist_ok=True)
            print(f"Ensured output directory exists: {args.output}")
        except OSError as e:
            print(f"Error creating output directory {args.output}: {e}")
            return # Exit if directory cannot be created


        # Call the method to handle the Spotify link
        self.download_spotify_item(args.spotify_link, args.output)

        print("CLI execution finished.")


if __name__ == "__main__":
    # Entry point for the command-line interface
    app = AppController()
    app.run_cli()
