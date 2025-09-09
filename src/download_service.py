import logging
import os
import re
import requests
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class AudioCoverDownloadService:
    def __init__(self, base_output_dir=None, spotdl_audio_source="youtube-music", spotdl_format="mp3"):
        """
        Service responsible for downloading audio via SpotDL and fetching cover images.
        """
        self.base_output_dir = base_output_dir if base_output_dir is not None else 'downloads'
        self.spotdl_audio_source = spotdl_audio_source
        self.spotdl_format = spotdl_format
        os.makedirs(self.base_output_dir, exist_ok=True)
        logger.info("DownloadService initialized with base output directory: %s", self.base_output_dir)

    def _sanitize_filename(self, name: str) -> str:
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        name = name.strip()
        name = re.sub(r'_{2,}', '_', name)
        return name

    def _detect_item_type(self, spotify_link: str) -> str:
        match = re.search(r"open\.spotify\.com/(track|album|playlist)", spotify_link)
        return match.group(1) if match else "track"

    def download_audio(
        self,
        spotify_link: str,
        output_directory: str,
        item_title: str,
        item_type: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> bool:
        """Download audio using the SpotDL Python API."""
        if item_type is None:
            item_type = self._detect_item_type(spotify_link)

        sanitized_item_title = self._sanitize_filename(item_title)
        if item_type == "track":
            output_template = os.path.join(output_directory, f"{sanitized_item_title}.{{ext}}")
        else:
            output_template = os.path.join(output_directory, "{artists} - {title}.{ext}")

        try:
            from spotdl.download.downloader import Downloader, DownloaderOptions
            from spotdl.types.song import Song
            from spotdl.types.playlist import Playlist
            from spotdl.types.album import Album
        except Exception as exc:
            logger.error("Failed to import SpotDL API: %s", exc)
            return False

        def _update(tracker):
            try:
                overall_total = getattr(tracker, 'overall_total', 100)
                overall_progress = getattr(tracker, 'overall_progress', 0)
                percent = (overall_progress / overall_total) * 100 if overall_total else getattr(tracker, 'progress', 0)
                status_text = getattr(tracker, 'status', '')
                if progress_callback:
                    progress_callback(status_text, percent)
            except Exception:
                pass

        options = DownloaderOptions(
            audio_providers=[self.spotdl_audio_source],
            output=output_template,
            format=self.spotdl_format,
            overwrite="skip",
        )
        downloader = Downloader(options)
        if downloader.progress_handler:
            downloader.progress_handler.update_callback = _update

        try:
            if item_type == "track":
                song = Song.from_url(spotify_link)
                result = downloader.download_song(song)
                success = result[1] is not None
            elif item_type == "playlist":
                playlist = Playlist.from_url(spotify_link)
                results = downloader.download_multiple_songs(playlist.songs)
                success = all(path for _, path in results)
            elif item_type == "album":
                album = Album.from_url(spotify_link)
                results = downloader.download_multiple_songs(album.songs)
                success = all(path for _, path in results)
            else:
                logger.error("Unsupported item type: %s", item_type)
                if progress_callback:
                    progress_callback("error", 0)
                return False

            if success:
                if progress_callback:
                    progress_callback("finished", 100)
                return True
            else:
                if progress_callback:
                    progress_callback("error", 0)
                return False
        except Exception as e:
            logger.error("SpotDL download failed: %s", e, exc_info=True)
            if progress_callback:
                progress_callback("error", 0)
            return False

    def download_cover_image(self, image_url: str, output_dir: str, filename: str = "cover.jpg") -> Optional[str]:
        if not image_url:
            logger.info("No image URL provided, skipping cover art download.")
            return None

        local_image_path = os.path.join(output_dir, filename)
        try:
            logger.info("Attempting to download cover art from %s to %s", image_url, local_image_path)
            response = requests.get(image_url, stream=True, timeout=15)
            response.raise_for_status()

            with open(local_image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info("Successfully downloaded cover art to %s", local_image_path)
            return local_image_path
        except requests.exceptions.Timeout:
            logger.error("Timeout while trying to download cover art from %s", image_url)
            return None
        except requests.exceptions.RequestException as e:
            logger.error("Failed to download cover art from %s: %s", image_url, e)
            return None
        except IOError as e:
            logger.error("Failed to save cover art to %s: %s", local_image_path, e)
            return None
