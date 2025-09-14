"""src/download_service.py

AudioCoverDownloadService now supports both legacy CLI and SpotDL API
paths. Under the feature flag USE_SPOTDL_PIPELINE, we use the SpotDL
Python API via the shared SpotdlClient; otherwise, we fall back to the
CLI subprocess for non-breaking behavior.
"""

import subprocess
import logging
import os
import re
import requests
import sys

from config import Config

logger = logging.getLogger(__name__)


class AudioCoverDownloadService:
    def __init__(self, base_output_dir=None,
                 spotdl_audio_source=None,
                 spotdl_format=None):
        """Initializes the DownloadService using Config defaults if not provided.

        :param base_output_dir: The base directory where downloaded content will be saved.
        :param spotdl_audio_source: The audio source to use for spotdl (e.g., "youtube-music", "youtube", "spotify").
        :param spotdl_format: The audio format to download (e.g., "opus", "mp3", "flac").
        """
        # Fallback to Config values when args are not provided
        self.base_output_dir = base_output_dir or Config.BASE_OUTPUT_DIR
        self.spotdl_audio_source = spotdl_audio_source or Config.SPOTDL_AUDIO_SOURCE
        self.spotdl_format = spotdl_format or Config.SPOTDL_FORMAT
        os.makedirs(self.base_output_dir, exist_ok=True)
        logger.info(f"DownloadService initialized with base output directory: {self.base_output_dir}")

    def _sanitize_filename(self, name):
        """Sanitizes a string to be used as a filename."""
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        name = name.strip()
        name = re.sub(r'_{2,}', '_', name)
        return name

    def _download_via_spotdl_api(self, spotify_link: str, output_directory: str, item_title: str) -> bool:
        """Download using the SpotDL Python API via SpotdlClient."""
        try:
            try:
                from flask import current_app
                spotdl_client = current_app.extensions.get('spotdl_client')
            except Exception:
                spotdl_client = None
            if spotdl_client is None:
                # Fallback: build a default client
                from .spotdl_client import build_default_client
                spotdl_client = build_default_client(app_logger=logger)

            sanitized_title = self._sanitize_filename(item_title)
            output_template = os.path.join(output_directory, f"{sanitized_title}")
            spotdl_client.set_output_template(output_template)

            songs = spotdl_client.search([spotify_link])
            results = spotdl_client.download_songs(songs)

            ok = True
            for song, path in results:
                if path is None:
                    logger.error("Failed to download %s", getattr(song, 'display_name', song))
                    ok = False
            return ok
        except Exception as e:
            logger.exception("SpotDL API download failed for %s: %s", spotify_link, e)
            return False

    def download_audio(self, spotify_link, output_directory, item_title):
        """
        Downloads audio content. Uses SpotDL API when feature flag is ON,
        otherwise falls back to the legacy subprocess CLI.
        :return: True on success, False on failure.
        """
        if Config.USE_SPOTDL_PIPELINE:
            return self._download_via_spotdl_api(spotify_link, output_directory, item_title)

        sanitized_item_title = self._sanitize_filename(item_title)
        # Build the output template using the sanitized title to avoid invalid
        # characters in the generated filename. spotDL CLI expects extension placeholder.
        output_template = os.path.join(
            output_directory,
            f"{sanitized_item_title}.{{ext}}",
        )

        command = [
            sys.executable, '-m', 'spotdl',
            spotify_link,
            '--output', output_template,
            '--overwrite', 'skip',
            '--format', self.spotdl_format,
            '--audio', self.spotdl_audio_source,
            '--threads', str(Config.SPOTDL_THREADS),
        ]

        if Config.SPOTIPY_CLIENT_ID and Config.SPOTIPY_CLIENT_SECRET:
            command.extend([
                '--client-id', Config.SPOTIPY_CLIENT_ID,
                '--client-secret', Config.SPOTIPY_CLIENT_SECRET,
            ])

        try:
            # Redact sensitive values in logs
            safe_command = list(command)
            try:
                if '--client-secret' in safe_command:
                    idx = safe_command.index('--client-secret')
                    if idx + 1 < len(safe_command):
                        safe_command[idx + 1] = '***REDACTED***'
            except Exception:
                pass

            logger.info(f"Executing spotdl command: {' '.join(safe_command)}")
            process = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
            logger.info(f"Spotdl stdout: {process.stdout}")
            if process.stderr:
                logger.warning(f"Spotdl stderr: {process.stderr.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Spotdl failed with exit code {e.returncode}. stdout: {e.stdout.strip() if e.stdout else ''}, stderr: {e.stderr.strip() if e.stderr else 'No stderr'}")
            if "rate/request limit" in (e.stderr or ""):
                logger.error("Spotdl hit a rate limit. Please wait and try again.")
            return False
        except FileNotFoundError:
            logger.error("Python executable or spotdl module not found for subprocess call. Check your environment.")
            return False
        except Exception as e:
            logger.exception(f"An unexpected error occurred during audio download for {spotify_link}: {e}")
            return False

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
