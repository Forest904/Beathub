# file_manager.py
import os
import re
import requests
import logging

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self):
        logger.info("FileManager initialized.")

    def sanitize_filename(self, name: str) -> str:
        """Sanitizes a string to be safe for use as a filename or directory name."""
        safe_name = re.sub(r'[^\w\s-]', '', name)
        safe_name = safe_name.strip()
        safe_name = safe_name[:100] # Limit length
        logger.debug(f"FileManager: Sanitized '{name}' to '{safe_name}'")
        return safe_name

    def get_output_directory(self, base_dir: str, item_name: str | None = None) -> str:
        """Determines the specific output directory and creates it."""
        output_dir = base_dir
        if item_name:
            safe_item_name = self.sanitize_filename(item_name)
            output_dir = os.path.join(base_dir, safe_item_name)

        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"FileManager: Using output directory: {output_dir}")
        return output_dir

    def save_cover_art(self, cover_url: str, output_dir: str, filename: str = "cover.jpg") -> str | None:
        """Downloads and saves cover art from a URL."""
        if not cover_url:
            logger.warning("FileManager: No cover art URL provided.")
            return None

        file_path = os.path.join(output_dir, filename)
        logger.info(f"FileManager: Attempting to save cover art from {cover_url} to {file_path}")

        try:
            response = requests.get(cover_url, stream=True)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"FileManager: Successfully saved cover art to {file_path}")
            return file_path
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading cover art from {cover_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while saving cover art: {e}")
            return None

