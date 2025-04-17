from spotdl import Spotdl
from clients.spotify_client import SpotifyClient
from clients.youtube_downloader import YouTubeDownloader
from services.playlist_service import PlaylistService
from services.download_service import DownloadService
from services.metadata_service import MetadataService

class AppController:
    def __init__(self, config):
        self.spotdl = Spotdl(
            client_id=config.client_id,
            client_secret=config.client_secret,
        )

        # Pass shared Spotdl instance to clients
        spotify_client = SpotifyClient(self.spotdl)
        youtube_downloader = YouTubeDownloader(self.spotdl)

        # Use clients in services
        self.playlist_svc = PlaylistService(spotify_client)
        self.download_svc = DownloadService(youtube_downloader)
        self.metadata_svc = MetadataService()

    def run(self, url: str, out: str):
        playlist = self.playlist_svc.get_playlist(url)
        self.download_svc.download_all(playlist, out)
        self.metadata_svc.save_to_json(playlist, f"{out}/meta.json")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--out", default="downloads")
    args = parser.parse_args()

    # your config loader would go here
    class C: client_id="97fd44d331c548ebb642e71edcb2a1c0"; client_secret="05a129fae323410eb645feed31797132"
    AppController(C).run(args.url, args.out)
