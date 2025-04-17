from spotdl import Spotdl
from models.track import Track
from pathlib import Path
from typing import Optional

class YouTubeDownloader:
    def __init__(self, spotdl: Spotdl):
        self._spotdl = spotdl

    def download(self, url: str, output_dir: str) -> Optional[Path]:
        results = self._spotdl.download_song(url, output=output_dir)
        if not results:
            print(f"[WARN] Failed to download: {url}")
            return None
        _, path = results[0]
        return path

