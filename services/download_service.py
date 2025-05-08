# services/download_service.py

# Import clients, models, and utils
from clients.youtube_downloader import YouTubeDownloader # Uncomment when client is ready
from models.track import Track # Uncomment when model is ready
from utils.file_manager import FileManager # Uncomment when util is ready
from services.metadata_service import MetadataService # Uncomment when service is ready
from typing import List # Import List for type hinting
import os # Import os for path joining

class DownloadService:
    """
    Orchestrates the download process. Takes a list of Tracks and invokes the YouTubeDownloader.
    Also interacts with FileManager for output paths and MetadataService for metadata application.
    """
    def __init__(self):
        # Initialize the downloader, file manager, and metadata service
        self.downloader = YouTubeDownloader() # Uncomment when client is ready
        self.file_manager = FileManager() # Uncomment when util is ready
        self.metadata_service = MetadataService() # Uncomment when service is ready
        print("DownloadService initialized.")


    def download_tracks_from_list(self, tracks: List[Track], base_output_dir: str, item_name: str | None = None) -> List[str]:
        """
        Downloads a list of tracks to a specified base directory, optionally within a subdirectory
        named after the item (playlist/album).

        Args:
            tracks: A list of Track objects to download.
            base_output_dir: The base directory for downloads.
            item_name: The name of the item (playlist or album) for creating a subdirectory (optional).

        Returns:
            A list of paths to the successfully downloaded files.
        """
        print(f"DownloadService: Starting download for {len(tracks)} tracks.")

        # Determine the specific output directory using FileManager
        output_dir = self.file_manager.get_output_directory(base_output_dir, item_name)

        downloaded_files = []
        for i, track in enumerate(tracks):
            # Get the desired filename for the track
            filename = self.file_manager.get_track_filename(track)
            output_path = os.path.join(output_dir, filename)

            # Download the track
            if self.downloader.download_track(track, output_path):
                downloaded_files.append(output_path)
                # Apply metadata after successful download
                self.metadata_service.apply_metadata_to_file(output_path, track)
            else:
                 print(f"DownloadService: Skipping metadata application for failed download of '{track.title}'.")


        print(f"DownloadService: Finished download process. Successfully downloaded {len(downloaded_files)} files.")
        return downloaded_files

