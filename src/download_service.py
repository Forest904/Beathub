import logging
import os
import re
import requests
import time
from typing import Callable, Optional
from config import Config

try:
    from spotdl.utils.spotify import SpotifyClient, SpotifyError  # type: ignore
except Exception:  # SpotDL may not be installed at import time; handled later in function
    SpotifyClient = None  # type: ignore
    SpotifyError = Exception  # type: ignore

logger = logging.getLogger(__name__)

class AudioCoverDownloadService:
    def __init__(self, base_output_dir=None, spotdl_audio_source=None, spotdl_format="mp3"):
        """
        Service responsible for downloading audio via SpotDL and fetching cover images.
        """
        self.base_output_dir = base_output_dir if base_output_dir is not None else 'downloads'
        # Allow single string or list, default to provider fallback
        if spotdl_audio_source is None:
            self.spotdl_audio_source = ["youtube-music", "youtube"]
        elif isinstance(spotdl_audio_source, (list, tuple)):
            self.spotdl_audio_source = list(spotdl_audio_source)
        else:
            self.spotdl_audio_source = [str(spotdl_audio_source)]
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

        # Ensure SpotDL Spotify client is initialized (singleton)
        if SpotifyClient is not None:
            try:
                # This will raise if not initialized in this process
                SpotifyClient()
            except Exception:
                # Attempt to initialize using Config defaults
                client_id = Config.SPOTIPY_CLIENT_ID
                client_secret = Config.SPOTIPY_CLIENT_SECRET
                if not client_id or not client_secret:
                    logger.error("Spotify credentials missing; cannot initialize SpotDL SpotifyClient.")
                    if progress_callback:
                        progress_callback("error", 0)
                    return False
                try:
                    SpotifyClient.init(
                        client_id=client_id,
                        client_secret=client_secret,
                        user_auth=False,
                        headless=True,
                    )
                    logger.info("Initialized SpotDL SpotifyClient in download service.")
                except Exception as exc:
                    logger.error("Failed to initialize SpotDL SpotifyClient: %s", exc, exc_info=True)
                    if progress_callback:
                        progress_callback("error", 0)
                    return False

        # Track elapsed time per song and detect SpotDL errors to shorten timeouts
        song_start_times = {}
        from threading import Event
        error_event = Event()

        def _update(tracker, message: str = ""):
            try:
                parent = getattr(tracker, 'parent', None)
                overall_total = getattr(parent, 'overall_total', None)
                overall_progress = getattr(parent, 'overall_progress', None)
                if overall_total and overall_total > 0 and overall_progress is not None:
                    percent = (overall_progress / overall_total) * 100
                else:
                    percent = float(getattr(tracker, 'progress', 0))

                song_name = getattr(tracker, 'song_name', '')
                # Initialize start time for this song when we first see it
                if song_name and song_name not in song_start_times:
                    song_start_times[song_name] = time.monotonic()
                elapsed = 0
                if song_name in song_start_times:
                    elapsed = int(time.monotonic() - song_start_times[song_name])

                nice_phase = message or getattr(tracker, 'status', '')
                # If SpotDL signals an error for a song, trigger error event to shorten timeout
                try:
                    if isinstance(message, str) and message.lower().startswith("error"):
                        error_event.set()
                except Exception:
                    pass
                if song_name:
                    status_text = f"{nice_phase}: {song_name} ({elapsed}s)"
                else:
                    status_text = nice_phase
                if progress_callback:
                    progress_callback(status_text, percent)
            except Exception:
                # Swallow any progress callback errors to not break downloads
                pass

        options = DownloaderOptions(
            audio_providers=self.spotdl_audio_source,
            output=output_template,
            format=self.spotdl_format,
            overwrite="skip",
            # Keep concurrency low to reduce hangs
            threads=2,
            # Help yt-dlp avoid indefinite stalls
            yt_dlp_args="--socket-timeout 15 --retries 3 --fragment-retries 3 --concurrent-fragments 1",
            # Avoid preloading extra data
            preload=False,
            # Print errors to our logs via SpotDL
            print_errors=True,
            save_errors=os.path.join(self.base_output_dir, "spotdl_errors.log"),
        )
        # Prepare objects and count tracks for timeout budgeting
        to_download = {"kind": None, "obj": None}
        track_count = 1

        try:
            if item_type == "track":
                song = Song.from_url(spotify_link)
                to_download = {"kind": "track", "obj": song}
                track_count = 1
            elif item_type == "playlist":
                playlist = Playlist.from_url(spotify_link)
                to_download = {"kind": "playlist", "obj": playlist}
                track_count = len(getattr(playlist, 'songs', []) or []) or 1
            elif item_type == "album":
                album = Album.from_url(spotify_link)
                to_download = {"kind": "album", "obj": album}
                track_count = len(getattr(album, 'songs', []) or []) or 1
            else:
                logger.error("Unsupported item type: %s", item_type)
                if progress_callback:
                    progress_callback("error", 0)
                return False
        except Exception as e:
            logger.error("Failed to prepare download objects: %s", e, exc_info=True)
            if progress_callback:
                progress_callback("error", 0)
            return False

        result_holder = {"success": False, "finished": False}

        def _run_download():
            try:
                # Create the downloader in this thread so its asyncio loop is bound here
                downloader = Downloader(options)
                if downloader.progress_handler:
                    downloader.progress_handler.update_callback = _update
                if to_download["kind"] == "track":
                    res = downloader.download_song(to_download["obj"])  # type: ignore[index]
                    result_holder["success"] = res[1] is not None
                elif to_download["kind"] == "playlist":
                    results = downloader.download_multiple_songs(to_download["obj"].songs)  # type: ignore[index]
                    success_count = sum(1 for _, path in results if path)
                    total_count = len(results)
                    result_holder["success"] = success_count > 0
                    if progress_callback:
                        progress_callback(f"Finished playlist: {success_count}/{total_count} tracks downloaded", 100)
                elif to_download["kind"] == "album":
                    results = downloader.download_multiple_songs(to_download["obj"].songs)  # type: ignore[index]
                    success_count = sum(1 for _, path in results if path)
                    total_count = len(results)
                    result_holder["success"] = success_count > 0
                    if progress_callback:
                        progress_callback(f"Finished album: {success_count}/{total_count} tracks downloaded", 100)
            except Exception as e:
                logger.error("SpotDL download failed: %s", e, exc_info=True)
                result_holder["success"] = False
            finally:
                result_holder["finished"] = True

        # Run download with a timeout watchdog
        import threading as _threading
        worker = _threading.Thread(target=_run_download, daemon=True)
        worker.start()
        timeout_seconds = int(min(max(180, 90 * track_count), 1800))

        # Wait with dynamic deadline that can be shortened on SpotDL errors
        start_time = time.monotonic()
        original_deadline = start_time + timeout_seconds
        current_deadline = original_deadline
        shortened_applied = False

        while not result_holder["finished"] and time.monotonic() < current_deadline:
            remaining = current_deadline - time.monotonic()
            worker.join(timeout= min(1.0, max(0.0, remaining)))
            if result_holder["finished"]:
                break
            # If an error has been seen, shorten remaining window once
            if (not shortened_applied) and error_event.is_set():
                # Short window: 15s per track, clamped to [30s, 60s]
                short_window = max(30, min(60, 15 * track_count))
                new_deadline = time.monotonic() + short_window
                if new_deadline < current_deadline:
                    current_deadline = new_deadline
                shortened_applied = True

        if not result_holder["finished"]:
            logger.warning(
                "Download timed out after %ss (tracks=%s); returning success to continue pipeline.",
                int(current_deadline - start_time),
                track_count,
            )
            if progress_callback:
                progress_callback("timeout", 100)
            # Return True to allow pipeline to continue; background thread will be daemon
            return True

        if result_holder["success"]:
            if progress_callback:
                progress_callback("finished", 100)
            return True
        else:
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
