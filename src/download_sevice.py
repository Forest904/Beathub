# download_service.py
import os
import json
import logging
from typing import List, Dict, Any

from .models import Track, Playlist # Relative import
from .file_manager import FileManager # Relative import
from .spotdl_client import SpotDLClient # Relative import

logger = logging.getLogger(__name__)

class DownloadService:
    def __init__(self, base_output_dir: str = "./downloads"):
        self.file_manager = FileManager()
        self.spotdl_client = SpotDLClient()
        self.base_output_dir = base_output_dir
        os.makedirs(self.base_output_dir, exist_ok=True)
        logger.info(f"DownloadService initialized with base output directory: {self.base_output_dir}")

    def download_spotify_content(self, spotify_link: str) -> Dict[str, Any]:
        """
        Main method to handle the entire download process for a Spotify link.
        Returns a dictionary with status and details.
        """
        logger.info(f"Processing Spotify link: {spotify_link}")

        try:
            # Step 1: Fetch metadata using spotdl save
            raw_tracks_data = self.spotdl_client.save_metadata(spotify_link)

            if not raw_tracks_data:
                return {"status": "error", "message": f"Could not fetch metadata for Spotify link: {spotify_link}"}

            if not isinstance(raw_tracks_data, list) or not raw_tracks_data:
                return {"status": "error", "message": "Fetched metadata is empty or in an unexpected format."}

            # Convert raw data to Track objects and determine item details
            fetched_tracks: List[Track] = []
            item_name = "Unknown Item"
            item_cover_url = None
            item_type = "unknown"

            # Determine item type and a good folder name/cover URL from the first track's metadata
            first_track_data = raw_tracks_data[0]
            if "/playlist/" in spotify_link:
                item_type = "playlist"
                item_name = first_track_data.get('list_name', 'Downloaded Playlist')
                item_cover_url = first_track_data.get('list_cover_url')
                if not item_cover_url:
                    item_cover_url = first_track_data.get('cover_url')
            elif "/album/" in spotify_link:
                item_type = "album"
                item_name = first_track_data.get('album_name', 'Downloaded Album')
                item_cover_url = first_track_data.get('album_cover_url')
                if not item_cover_url:
                    item_cover_url = first_track_data.get('cover_url')
            elif "/track/" in spotify_link:
                item_type = "track"
                item_name = first_track_data.get('name', 'Downloaded Track')
                item_cover_url = first_track_data.get('cover_url')

            if not item_name or item_name == "Unknown Item":
                item_name = first_track_data.get('album_name') or first_track_data.get('name') or "Spotify_Download"

            logger.info(f"Detected item type: {item_type}, Name: '{item_name}'")

            # Populate Track objects for response
            for t_data in raw_tracks_data:
                track = Track(
                    id=t_data.get('song_id', t_data.get('id','')),
                    title=t_data.get('name', 'Unknown Title'),
                    artists=t_data.get('artists', ['Unknown Artist']),
                    album=t_data.get('album_name', t_data.get('album', 'Unknown Album')),
                    duration_ms=t_data.get('duration') * 1000 if t_data.get('duration') is not None else None,
                    isrc=t_data.get('isrc'),
                    spotify_url=t_data.get('url'),
                    cover_url=t_data.get('cover_url')
                )
                fetched_tracks.append(track)
            logger.info(f"Successfully processed metadata for {len(fetched_tracks)} tracks.")

            # Step 2: Determine output directory for this item
            item_output_dir = self.file_manager.get_output_directory(self.base_output_dir, item_name)
            logger.info(f"Content will be saved to: {item_output_dir}")

            # Step 3: Save cover art
            saved_cover_path = None
            if item_cover_url:
                saved_cover_path = self.file_manager.save_cover_art(item_cover_url, item_output_dir, "cover.jpg")
            else:
                logger.warning("No primary cover art URL found in metadata. Skipping cover art download.")
                if fetched_tracks and fetched_tracks[0].cover_url:
                    logger.info("Attempting to use first track's cover art as a fallback.")
                    saved_cover_path = self.file_manager.save_cover_art(fetched_tracks[0].cover_url, item_output_dir, "cover.jpg")

            # Step 4: Save the raw .spotdl (JSON) metadata file
            metadata_filename = self.file_manager.sanitize_filename(item_name) + "_metadata.json"
            metadata_file_path = os.path.join(item_output_dir, metadata_filename)
            try:
                with open(metadata_file_path, 'w', encoding='utf-8') as f:
                    json.dump(raw_tracks_data, f, indent=4, ensure_ascii=False)
                logger.info(f"Metadata saved to {metadata_file_path}")
            except Exception as e:
                logger.error(f"Error saving metadata JSON: {e}", exc_info=True)

            # Step 5: Download songs
            logger.info("Initiating song download...")
            download_success = self.spotdl_client.download_item(spotify_link, item_output_dir)

            if download_success:
                logger.info("All requested songs have been processed by spotdl download.")
                return {
                    "status": "success",
                    "message": "Download completed successfully.",
                    "item_name": item_name,
                    "item_type": item_type,
                    "output_directory": item_output_dir,
                    "cover_art_saved": saved_cover_path is not None,
                    "tracks": [t.__dict__ for t in fetched_tracks] # Return track data for frontend
                }
            else:
                logger.error("Song download process failed or encountered errors.")
                return {"status": "error", "message": "Song download process failed or encountered errors."}

        except RuntimeError as e:
            logger.error(f"Application error: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            return {"status": "error", "message": "An unexpected server error occurred."}

