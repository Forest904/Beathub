"""src/download_service.py

AudioCoverDownloadService provides utilities needed alongside the SpotDL API
pipeline: cover image downloading and filename sanitization. All legacy CLI
subprocess paths have been removed.
"""

import logging
import os
import re
import requests

from config import Config

logger = logging.getLogger(__name__)


class AudioCoverDownloadService:
    def __init__(self, base_output_dir=None,
                 spotdl_audio_source=None,
                 spotdl_format=None):
        """Initializes the service using Config defaults if not provided.

        :param base_output_dir: The base directory where downloaded content will be saved.
        :param spotdl_audio_source: The audio source to use for spotdl (e.g., "youtube-music", "youtube", "spotify").
        :param spotdl_format: The audio format to download (e.g., "opus", "mp3", "flac").
        """
        # Fallback to Config values when args are not provided
        self.base_output_dir = base_output_dir or Config.BASE_OUTPUT_DIR
        # Kept for compatibility with callers; SpotDL API consumes these via
        # its own settings in the dedicated client.
        self.spotdl_audio_source = spotdl_audio_source or Config.SPOTDL_AUDIO_SOURCE
        self.spotdl_format = spotdl_format or Config.SPOTDL_FORMAT
        os.makedirs(self.base_output_dir, exist_ok=True)
        logger.info(f"Download helpers initialized with base output directory: {self.base_output_dir}")

    def _sanitize_filename(self, name):
        """Sanitizes a string to be used as a filename."""
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        name = name.strip()
        name = re.sub(r'_{2,}', '_', name)
        return name

    # All audio downloading is handled via SpotDL API in the orchestrator.
    # This service no longer downloads audio directly.

    def download_cover_image(self, image_url, output_dir, filename="cover.jpg"):
        """
        Downloads a cover image from a URL and saves it to a specified directory.
        :param image_url: The URL of the image to download.
        :param output_dir: The directory where the image will be saved.
        :param filename: The name of the file to save the image as.
        :return: The local path to the downloaded image file, or None if an error occurs.
        """
        if not image_url:
            logger.info("No image URL provided, skipping cover art download.")
            return None

        local_image_path = os.path.join(output_dir, filename)
        try:
            logger.info(f"Attempting to download cover art from {image_url} to {local_image_path}")
            response = requests.get(image_url, stream=True, timeout=15)
            response.raise_for_status()

            with open(local_image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Successfully downloaded cover art to {local_image_path}")
            return local_image_path
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while trying to download cover art from {image_url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download cover art from {image_url}: {e}")
            return None
        except IOError as e:
            logger.error(f"Failed to save cover art to {local_image_path}: {e}")
            return None
