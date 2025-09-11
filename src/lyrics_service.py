import lyricsgenius
import logging
import re
import os

from config import Config

logger = logging.getLogger(__name__)

class LyricsService:
    def __init__(self, genius_access_token=None):
        """Initializes the LyricsService using token from Config by default."""
        # Fallback to Config if not explicitly provided
        genius_access_token = genius_access_token or Config.GENIUS_ACCESS_TOKEN
        self.genius_client = None
        if genius_access_token:
            try:
                self.genius_client = lyricsgenius.Genius(genius_access_token, verbose=False, retries=3)
                logger.info("LyricsGenius client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize LyricsGenius client: {e}")
        else:
            logger.warning("GENIUS_ACCESS_TOKEN not set. Lyrics will not be downloaded.")

    def _sanitize_filename(self, name):
        """Sanitizes a string to be used as a filename."""
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        name = name.strip()
        name = re.sub(r'_{2,}', '_', name)
        return name

    def download_lyrics(self, track_title, track_artist, output_dir):
        """ Downloads lyrics for a given track and saves them to a file. """
        if not self.genius_client:
            logger.warning("LyricsGenius client not initialized. Cannot download lyrics.")
            return None

        sanitized_track_title = self._sanitize_filename(track_title)
        sanitized_track_artist = self._sanitize_filename(track_artist)
        lyrics_filename = f"{sanitized_track_title} - {sanitized_track_artist}.txt"
        local_lyrics_path = os.path.join(output_dir, lyrics_filename)

        try:
            logger.info(f"Attempting to download lyrics for '{track_title}' by '{track_artist}'")
            song = self.genius_client.search_song(track_title, track_artist)
            if song and song.lyrics:
                with open(local_lyrics_path, 'w', encoding='utf-8') as f:
                    f.write(song.lyrics)
                logger.info(f"Successfully downloaded lyrics to {local_lyrics_path}")
                return local_lyrics_path
            else:
                logger.info(f"No lyrics found for '{track_title}' by '{track_artist}' on Genius.")
                return None
        except Exception as e:
            logger.error(f"Failed to download lyrics for '{track_title}' by '{track_artist}': {e}")
            return None
