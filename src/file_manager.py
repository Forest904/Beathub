import os
import re
import logging

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self, base_output_dir='downloads'):
        """
        Initializes the FileManager.
        :param base_output_dir: The base directory for all downloads.
        """
        self.base_output_dir = base_output_dir
        os.makedirs(self.base_output_dir, exist_ok=True)
        logger.info(f"FileManager initialized with base output directory: {self.base_output_dir}")

    def sanitize_filename(self, name):
        """
        Sanitizes a string to be used as a filename or directory name.
        Removes invalid characters and replaces multiple underscores with a single one.
        """
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        name = name.strip()
        name = re.sub(r'_{2,}', '_', name)
        return name

    def create_item_output_directory(self, artist_name, item_title):
        """
        Creates a dedicated output directory for a specific Spotify item (album, track, playlist).
        :param artist_name: The artist's name or playlist owner.
        :param item_title: The title of the album, track, or playlist.
        :return: The path to the created directory, or None if creation fails.
        """
        sanitized_artist = self.sanitize_filename(artist_name)
        sanitized_title = self.sanitize_filename(item_title)
        
        item_specific_output_dir = os.path.join(
            self.base_output_dir,
            f"{sanitized_artist} - {sanitized_title}"
        )

        try:
            os.makedirs(item_specific_output_dir, exist_ok=True)
            logger.info(f"Ensured output directory exists: {item_specific_output_dir}")
            return item_specific_output_dir
        except OSError as e:
            logger.error(f"Could not create directory {item_specific_output_dir}: {e}")
            return None

    def save_metadata_json(self, output_dir, metadata):
        """
        Saves metadata as a JSON file in the specified directory.
        :param output_dir: The directory to save the JSON file.
        :param metadata: The dictionary of metadata to save.
        :return: The path to the saved JSON file, or None on failure.
        """
        metadata_json_path = os.path.join(output_dir, "spotify_metadata.json")
        try:
            with open(metadata_json_path, 'w', encoding='utf-8') as f:
                import json # Import json locally to keep FileManager light
                json.dump(metadata, f, ensure_ascii=False, indent=4)
            logger.info(f"Spotify metadata saved to {metadata_json_path}")
            return metadata_json_path
        except IOError as e:
            logger.error(f"Failed to save Spotify metadata to JSON at {metadata_json_path}: {e}")
            return None