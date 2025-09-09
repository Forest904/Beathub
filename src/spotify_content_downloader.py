import logging

import spotipy  # Import spotipy here
from spotipy.oauth2 import SpotifyClientCredentials  # Import SpotifyClientCredentials here
from spotdl.utils.spotify import SpotifyClient
from config import Config

# Import the decoupled services using relative imports
from .metadata_service import MetadataService
from .download_service import AudioCoverDownloadService
from .download_status_manager import DOWNLOAD_STATUS_MANAGER
from .lyrics_service import LyricsService
from .file_manager import FileManager

logger = logging.getLogger(__name__)

class SpotifyContentDownloader:
    def __init__(self, base_output_dir=None, spotify_client_id=None, spotify_client_secret=None, genius_access_token=None):
        """
        Initializes the SpotifyContentDownloader with all necessary services.

        Configuration values can be supplied directly or will default to values
        defined in :class:`config.Config`.
        """
        # Resolve configuration using provided arguments or fall back to Config defaults
        self.base_output_dir = base_output_dir or Config.BASE_OUTPUT_DIR
        self._spotify_client_id = spotify_client_id or Config.SPOTIPY_CLIENT_ID
        self._spotify_client_secret = spotify_client_secret or Config.SPOTIPY_CLIENT_SECRET
        self._genius_access_token = genius_access_token or Config.GENIUS_ACCESS_TOKEN

        if self._spotify_client_id and self._spotify_client_secret:
            try:
                # Initialize SpotDL's SpotifyClient singleton with the installed API signature
                SpotifyClient.init(
                    client_id=self._spotify_client_id,
                    client_secret=self._spotify_client_secret,
                    user_auth=False,
                    headless=True,
                )
            except Exception as e:
                logger.error(
                    "Failed to initialize SpotifyClient: %s", e, exc_info=True
                )
        else:
            logger.error(
                "Spotify client ID or secret missing. SpotifyClient not initialized; downloads will be skipped."
            )

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

    def download_spotify_content(self, spotify_link: str, job_id: str | None = None):
        """Orchestrates the download of Spotify content (audio, cover, lyrics, metadata).

        If ``job_id`` is provided the function will update :class:`DownloadStatusManager`
        with progress information that can be consumed by Server Sent Events.
        """

        if not self._spotify_client_id or not self._spotify_client_secret:
            error_msg = "Spotify client ID or secret missing. Cannot download content."
            logger.error(error_msg)
            if job_id:
                DOWNLOAD_STATUS_MANAGER.update_job(
                    job_id, status="error", message=error_msg, finished=True
                )
            return {"status": "error", "message": error_msg}

        # Progress weights per phase (sum to 100)
        WEIGHTS = {
            "metadata": 10.0,
            "cover": 5.0,
            "audio": 70.0,
            "lyrics": 12.0,
            "save": 3.0,
        }
        progress_so_far = 0.0

        if job_id:
            DOWNLOAD_STATUS_MANAGER.update_job(job_id, status="Loading item metadata...", progress=0)

        initial_metadata = self.metadata_service.get_metadata_from_link(spotify_link)

        if not initial_metadata:
            if job_id:
                DOWNLOAD_STATUS_MANAGER.update_job(
                    job_id,
                    status="error",
                    message="Could not retrieve initial metadata for the given Spotify link.",
                    finished=True,
                )
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
        if job_id:
            progress_so_far += WEIGHTS["metadata"]
            pretty_item = f"{item_type}: {title_name} - {artist_name}"
            DOWNLOAD_STATUS_MANAGER.update_job(job_id, status=f"Loaded metadata - {pretty_item}", progress=progress_so_far)

        # --- Download and save album cover ---
        if job_id:
            DOWNLOAD_STATUS_MANAGER.update_job(job_id, status="Downloading cover...", progress=progress_so_far)
        local_cover_image_path = self.audio_cover_download_service.download_cover_image(
            image_url_from_metadata,
            item_specific_output_dir
        )
        if job_id:
            progress_so_far += WEIGHTS["cover"]
            DOWNLOAD_STATUS_MANAGER.update_job(job_id, status="Cover downloaded", progress=progress_so_far)
        # --- End download and save album cover ---

        # --- Download audio ---
        if job_id:
            DOWNLOAD_STATUS_MANAGER.update_job(job_id, status="Preparing audio download...", progress=progress_so_far)

        def progress_cb(status_text: str, percent: float) -> None:
            if job_id:
                overall = progress_so_far + WEIGHTS["audio"] * (percent / 100.0)
                # Clamp
                overall = max(0.0, min(99.0, overall))
                DOWNLOAD_STATUS_MANAGER.update_job(job_id, status=f"Downloading music - {status_text}", progress=overall)

        audio_download_success = self.audio_cover_download_service.download_audio(
            spotify_link,
            item_specific_output_dir,
            title_name,  # Pass item_title for output formatting
            item_type=item_type,
            progress_callback=progress_cb,
        )
        if not audio_download_success:
            if job_id:
                DOWNLOAD_STATUS_MANAGER.update_job(
                    job_id,
                    status="error",
                    message=f"Audio download failed for {title_name}.",
                    finished=True,
                )
            return {"status": "error", "message": f"Audio download failed for {title_name}."}
        # --- End download audio ---

        # --- Get detailed track list and download lyrics ---
        if job_id:
            DOWNLOAD_STATUS_MANAGER.update_job(job_id, status="Fetching track list...", progress=progress_so_far + WEIGHTS["audio"])
        detailed_tracks_list = self.metadata_service.get_tracks_details(
            spotify_id, # Use spotify_id here
            item_type,
            image_url_from_metadata
        )
        track_count = len(detailed_tracks_list) if detailed_tracks_list else 1

        # Enrich tracks with lyrics paths
        completed_lyrics = 0
        for track_detail in detailed_tracks_list:
            track_title = track_detail.get('title', 'Unknown Title')
            track_artist = track_detail.get('artists', ['Unknown Artist'])[0] # Use first artist
            if job_id:
                base = progress_so_far + WEIGHTS["audio"]
                fraction = (completed_lyrics / track_count) if track_count else 0
                current_progress = base + WEIGHTS["lyrics"] * fraction
                DOWNLOAD_STATUS_MANAGER.update_job(job_id, status=f"Downloading lyrics - {track_title} - {track_artist}", progress=current_progress)
            lyrics_path = self.lyrics_service.download_lyrics(
                track_title,
                track_artist,
                item_specific_output_dir
            )
            track_detail['local_lyrics_path'] = lyrics_path
            completed_lyrics += 1
            if job_id:
                base = progress_so_far + WEIGHTS["audio"]
                fraction = (completed_lyrics / track_count) if track_count else 1
                current_progress = base + WEIGHTS["lyrics"] * fraction
                DOWNLOAD_STATUS_MANAGER.update_job(job_id, status=f"Downloaded lyrics - {track_title}", progress=current_progress)
        if job_id:
            progress_so_far += WEIGHTS["audio"] + WEIGHTS["lyrics"]
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

        if job_id:
            DOWNLOAD_STATUS_MANAGER.update_job(job_id, status="Saving metadata...", progress=progress_so_far)
        metadata_json_path = self.file_manager.save_metadata_json(
            item_specific_output_dir,
            comprehensive_metadata_to_save
        )
        if job_id:
            progress_so_far += WEIGHTS["save"]
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

        result = {
            "status": "success",
            "message": f"Successfully processed {item_type}: {title_name}",
            "item_name": title_name,
            "item_type": item_type,
            "spotify_id": spotify_id,  # Include spotify_id in return
            "artist": artist_name,  # Include artist in return
            "spotify_url": spotify_url,  # Include spotify_url in return
            "output_directory": item_specific_output_dir,
            "cover_art_url": image_url_from_metadata,
            "local_cover_image_path": local_cover_image_path,
            "tracks": simplified_tracks_info_for_return,
            "metadata_file_path": metadata_json_path,
        }

        if job_id:
            DOWNLOAD_STATUS_MANAGER.update_job(job_id, status="finished", progress=100, finished=True)

        return result
