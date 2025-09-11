import logging
import spotipy # Import spotipy here
from spotipy.oauth2 import SpotifyClientCredentials # Import SpotifyClientCredentials here

# Import configuration and decoupled services using relative imports
from .config import (
    BASE_OUTPUT_DIR,
    SPOTIPY_CLIENT_ID,
    SPOTIPY_CLIENT_SECRET,
    GENIUS_ACCESS_TOKEN,
)
from .metadata_service import MetadataService
from .download_service import AudioCoverDownloadService
from .lyrics_service import LyricsService
from .file_manager import FileManager

logger = logging.getLogger(__name__)

class SpotifyContentDownloader:
    def __init__(
        self,
        base_output_dir=BASE_OUTPUT_DIR,
        spotify_client_id=SPOTIPY_CLIENT_ID,
        spotify_client_secret=SPOTIPY_CLIENT_SECRET,
        genius_access_token=GENIUS_ACCESS_TOKEN,
    ):
        """Initializes the SpotifyContentDownloader with all necessary services."""

        # Configuration values with centralized defaults
        self.base_output_dir = base_output_dir
        self._spotify_client_id = spotify_client_id
        self._spotify_client_secret = spotify_client_secret
        self._genius_access_token = genius_access_token

        # Initialize the sub-services, passing them their respective configuration
        self.metadata_service = MetadataService(
            spotify_client_id=self._spotify_client_id,
            spotify_client_secret=self._spotify_client_secret
        )
        self.audio_cover_download_service = AudioCoverDownloadService(base_output_dir=self.base_output_dir)
        self.lyrics_service = LyricsService(genius_access_token=self._genius_access_token)
        self.file_manager = FileManager(base_output_dir=self.base_output_dir)

        # Initialize Spotipy directly within the downloader for artist search access
        # This uses the same credentials passed to MetadataService
        self.sp = None # Initialize to None
        if self._spotify_client_id and self._spotify_client_secret:
            try:
                self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                    client_id=self._spotify_client_id,
                    client_secret=self._spotify_client_secret
                ))
                logger.info("Spotipy instance initialized within SpotifyContentDownloader.")
            except Exception as e:
                logger.error(f"Failed to initialize Spotipy in SpotifyContentDownloader: {e}", exc_info=True)
        else:
            logger.warning("Spotify client ID or secret missing. Spotipy instance for direct searches will not be available.")

        logger.info("SpotifyContentDownloader initialized with decoupled services and configuration passed.")

    def get_spotipy_instance(self):
        """ Provides access to the initialized Spotipy instance. """
        return self.sp

    def download_spotify_content(self, spotify_link):
        """ Orchestrates the download of Spotify content (audio, cover, lyrics, metadata). """
        initial_metadata = self.metadata_service.get_metadata_from_link(spotify_link)

        if not initial_metadata:
            return {"status": "error", "message": "Could not retrieve initial metadata for the given Spotify link."}

        # Extract relevant info from initial_metadata for clearer variable names
        artist_name = initial_metadata.get('artist', 'Unknown Artist')
        title_name = initial_metadata.get('title', 'Unknown Title')
        item_type = initial_metadata.get('item_type', 'unknown')
        spotify_id = initial_metadata.get('spotify_id')
        image_url_from_metadata = initial_metadata.get('image_url')
        spotify_url = initial_metadata.get('spotify_url')

        # Create specific output directory
        item_specific_output_dir = self.file_manager.create_item_output_directory(artist_name, title_name)
        if not item_specific_output_dir:
            return {"status": "error", "message": f"Could not create output directory for {title_name}."}

        # --- Download and save album cover ---
        local_cover_image_path = self.audio_cover_download_service.download_cover_image(
            image_url_from_metadata,
            item_specific_output_dir
        )
        # --- End download and save album cover ---

        # --- Download audio ---
        audio_download_success = self.audio_cover_download_service.download_audio(
            spotify_link,
            item_specific_output_dir,
            title_name # Pass item_title for output formatting
        )
        if not audio_download_success:
            return {"status": "error", "message": f"Audio download failed for {title_name}."}
        # --- End download audio ---

        # --- Get detailed track list and download lyrics ---
        detailed_tracks_list = self.metadata_service.get_tracks_details(
            spotify_id, # Use spotify_id here
            item_type,
            image_url_from_metadata
        )

        # Enrich tracks with lyrics paths
        for track_detail in detailed_tracks_list:
            track_title = track_detail.get('title', 'Unknown Title')
            track_artist = track_detail.get('artists', ['Unknown Artist'])[0] # Use first artist
            lyrics_path = self.lyrics_service.download_lyrics(
                track_title,
                track_artist,
                item_specific_output_dir
            )
            track_detail['local_lyrics_path'] = lyrics_path
        # --- End get detailed track list and download lyrics ---

        # --- Save comprehensive metadata JSON ---
        # The comprehensive metadata should now include all details
        comprehensive_metadata_to_save = {
            'spotify_id': spotify_id,
            'title': title_name,
            'artist': artist_name,
            'image_url': image_url_from_metadata,
            'spotify_url': spotify_url,
            'item_type': item_type,
            'local_output_directory': item_specific_output_dir, # Add the actual local path here
            'local_cover_image_path': local_cover_image_path,
            'tracks_details': detailed_tracks_list
        }

        metadata_json_path = self.file_manager.save_metadata_json(
            item_specific_output_dir,
            comprehensive_metadata_to_save
        )
        # --- End save comprehensive metadata JSON ---

        simplified_tracks_info_for_return = []
        if detailed_tracks_list:
            for t_detail in detailed_tracks_list:
                simplified_tracks_info_for_return.append({
                    'title': t_detail.get('title'),
                    'artists': t_detail.get('artists'),
                    'cover_url': t_detail.get('album_image_url', image_url_from_metadata),
                    'local_lyrics_path': t_detail.get('local_lyrics_path')
                })

        return {
            "status": "success",
            "message": f"Successfully processed {item_type}: {title_name}",
            "item_name": title_name,
            "item_type": item_type,
            "spotify_id": spotify_id, # Include spotify_id in return
            "artist": artist_name, # Include artist in return
            "spotify_url": spotify_url, # Include spotify_url in return
            "output_directory": item_specific_output_dir,
            "cover_art_url": image_url_from_metadata,
            "local_cover_image_path": local_cover_image_path,
            "tracks": simplified_tracks_info_for_return,
            "metadata_file_path": metadata_json_path
        }