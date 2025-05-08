# utils/file_manager.py

import os
import re # Import re for sanitization
import requests # Import requests for downloading cover art

# Import models
from models.playlist import Playlist # Uncomment when models are ready
from models.track import Track # Uncomment when models is ready

class FileManager:
    """
    Handles filesystem I/O, including determining paths, naming files,
    and managing cover art.
    """
    def __init__(self):
        print("FileManager initialized.")
        pass

    def sanitize_filename(self, name: str) -> str:
        """
        Sanitizes a string to be safe for use as a filename or directory name.
        Removes invalid characters and limits length.

        Args:
            name: The input string.

        Returns:
            A sanitized string.
        """
        # Replace characters that are not alphanumeric, spaces, hyphens, or underscores
        safe_name = re.sub(r'[^\w\s-]', '', name)
        # Replace spaces with underscores (optional, can keep spaces if preferred)
        # safe_name = safe_name.replace(' ', '_')
        # Remove leading/trailing spaces
        safe_name = safe_name.strip()
        # Limit length (optional, adjust as needed)
        safe_name = safe_name[:100]
        print(f"FileManager: Sanitized '{name}' to '{safe_name}'")
        return safe_name

    def get_output_directory(self, base_dir: str, item_name: str | None = None) -> str:
        """
        Determines the specific output directory based on the base directory and item name.
        Creates the directory if it doesn't exist.

        Args:
            base_dir: The base download directory.
            item_name: The name of the item (playlist or album) for creating a subdirectory (optional).

        Returns:
            The full path to the output directory.
        """
        output_dir = base_dir
        if item_name:
            # Sanitize item name for use as a directory name
            safe_item_name = self.sanitize_filename(item_name)
            output_dir = os.path.join(base_dir, safe_item_name)

        os.makedirs(output_dir, exist_ok=True)
        print(f"FileManager: Using output directory: {output_dir}")
        return output_dir

    def get_track_filename(self, track: Track, file_extension: str = ".mp3") -> str:
        """
        Generates a safe filename for a track using its artist(s) and title.

        Args:
            track: The Track object.
            file_extension: The desired file extension (e.g., ".mp3").

        Returns:
            A safe filename string.
        """
        # Use the primary artist and title for the filename
        artist_name = self.sanitize_filename(track.artists[0]) if track.artists else "UnknownArtist"
        track_title = self.sanitize_filename(track.title)

        # Generate filename format: "Artist - Track Title.ext"
        filename = f"{artist_name} - {track_title}{file_extension}"

        # Ensure filename is not empty after sanitization
        if not filename.strip(file_extension):
             filename = f"Track_{track.id}{file_extension}" # Fallback filename

        print(f"FileManager: Generated filename: {filename}")
        return filename

    def save_cover_art(self, cover_url: str, output_dir: str, filename: str = "cover.jpg") -> str | None:
        """
        Downloads and saves cover art from a URL.

        Args:
            cover_url: The URL of the cover art image.
            output_dir: The directory to save the image.
            filename: The desired filename for the cover art.

        Returns:
            The path to the saved cover art file, or None if download fails.
        """
        if not cover_url:
            print("FileManager: No cover art URL provided.")
            return None

        file_path = os.path.join(output_dir, filename)
        print(f"FileManager: Attempting to save cover art from {cover_url} to {file_path}")

        try:
            response = requests.get(cover_url, stream=True)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"FileManager: Successfully saved cover art to {file_path}")
            return file_path
        except requests.exceptions.RequestException as e:
            print(f"Error downloading cover art from {cover_url}: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while saving cover art: {e}")
            return None

