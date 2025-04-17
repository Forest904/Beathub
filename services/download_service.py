from models.track import Track
from clients.youtube_downloader import YouTubeDownloader

class DownloadService:
    """
    Takes Track models and downloads them to disk.
    """

    def __init__(self, yt_downloader: YouTubeDownloader):
        self._downloader = yt_downloader

    def download_tracks(self, tracks: list[Track], output_dir: str) -> None:
        for track in tracks:
            path = self._downloader.download(track.download_url, output_dir)
            # you could update track object with path if needed
