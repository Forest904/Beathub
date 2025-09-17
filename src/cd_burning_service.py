import os
import json
import logging
import re
import tempfile
import shutil
import threading
import time
from typing import Optional, Dict, List, TYPE_CHECKING, Any

from config import Config
from .burn_sessions import BurnSession
from .progress import ProgressPublisher

# Ensure pydub and its dependencies (like ffmpeg) are installed
from pydub import AudioSegment
import sys

# Windows IMAPI v2 adapter
try:
    from .burners.imapi2_audio import IMAPI2AudioBurner, IMAPIUnavailableError
except Exception:  # pragma: no cover - adapter optional at import time
    IMAPI2AudioBurner = None  # type: ignore[assignment]
    IMAPIUnavailableError = RuntimeError  # type: ignore[assignment]

if TYPE_CHECKING:
    from .burners.imapi2_audio import IMAPI2AudioBurner as IMAPI2AudioBurnerType
else:
    IMAPI2AudioBurnerType = Any

# Instance-specific loggers will be used within CDBurningService.


class CDBurningService:
    def __init__(self, app_logger=None, base_output_dir=None):
        # Use the provided app_logger or create a new one for this instance
        self.logger = app_logger if app_logger else logging.getLogger(self.__class__.__name__)
        self.base_output_dir = base_output_dir or Config.BASE_OUTPUT_DIR
        # ffmpeg is used indirectly by pydub
        self.ffmpeg_path = "ffmpeg"
        # IMAPI2 burner (Windows only)
        self._imapi: Optional[IMAPI2AudioBurnerType] = None
        self._imapi_recorder = None
        self._imapi_recorder_id: Optional[str] = None
        self._active_session_id: Optional[str] = None
        self._cancel_flags: Dict[str, threading.Event] = {}
        self.logger.info("CDBurningService initialized (IMAPI2 backend on Windows)")

    # Note: external burner CLI not used on Windows/IMAPI path. If a cross-platform
    # backend is added in future, introduce a dedicated command runner.


    def scan_for_burner(self, session: BurnSession):
        """Enumerate burners via IMAPI2 and select the first available recorder on Windows."""
        self.logger.info("Scanning for CD/DVD burners (IMAPI2)...")
        session.update_status("Scanning Burner...")
        try:
            if sys.platform != 'win32' or IMAPI2AudioBurner is None:
                session.update_burner_state(detected=False, present=False, blank_or_erasable=False)
                self.logger.error("IMAPI2 is only supported on Windows. Platform: %s", sys.platform)
                return False

            if self._imapi is None:
                try:
                    self._imapi = IMAPI2AudioBurner(logger=self.logger, client_name="CD-Collector")
                except IMAPIUnavailableError as e:
                    session.update_burner_state(detected=False, present=False, blank_or_erasable=False)
                    session.set_error(str(e))
                    return False

            devices = self._imapi.list_recorders()
            if not devices:
                session.update_burner_state(detected=False, present=False, blank_or_erasable=False)
                self.logger.warning("No IMAPI2 recorders found.")
                return False

            # Use selected if set and still available; else first
            chosen_id = None
            ids = {d['unique_id'] for d in devices}
            if self._imapi_recorder_id in ids:
                chosen_id = self._imapi_recorder_id
            else:
                chosen_id = devices[0]['unique_id']

            # Open the recorder
            rec, rec_id = self._imapi.open_recorder(chosen_id)
            self._imapi_recorder = rec
            self._imapi_recorder_id = rec_id
            self.logger.info("Selected recorder: %s (%s %s)", rec_id, devices[0].get('vendor_id', ''), devices[0].get('product_id', ''))
            session.update_burner_state(detected=True, present=False, blank_or_erasable=False)
            return True
        except Exception as e:
            self.logger.exception("An unexpected error occurred during IMAPI2 burner scan.")
            session.update_burner_state(detected=False, present=False, blank_or_erasable=False)
            session.set_error(f"Burner scan failed unexpectedly: {e}")
            return False

    def select_device(self, unique_id: str) -> bool:
        """Select a specific recorder by unique ID (Windows/IMAPI2)."""
        if sys.platform != 'win32' or IMAPI2AudioBurner is None:
            return False
        if self._imapi is None:
            try:
                self._imapi = IMAPI2AudioBurner(logger=self.logger, client_name="CD-Collector")
            except Exception as e:
                self.logger.error("IMAPI2 init failed for device select: %s", e)
                return False
        try:
            rec, rec_id = self._imapi.open_recorder(unique_id)
            self._imapi_recorder = rec
            self._imapi_recorder_id = rec_id
            self.logger.info("Recorder selected: %s", rec_id)
            return True
        except Exception as e:
            self.logger.error("Failed to select recorder %s: %s", unique_id, e)
            return False

    def clear_selected_device(self) -> bool:
        """Clear cached recorder selection so no device is marked as active."""
        self._imapi_recorder = None
        self._imapi_recorder_id = None
        return True

    def check_disc_status(self, session: BurnSession):
        """Check disc presence/writability using IMAPI2 audio format."""
        if not self._imapi or not self._imapi_recorder:
            self.logger.warning("No recorder selected. Run scan_for_burner first.")
            session.update_burner_state(detected=False, present=False, blank_or_erasable=False)
            return False

        # Perform the actual disc status check via IMAPI2
        self.logger.info("Checking disc status (IMAPI2)...")
        session.update_status("Checking Disc...")
        try:
            present, writable = self._imapi.check_audio_disc_ready(self._imapi_recorder)
            session.update_burner_state(detected=True, present=present, blank_or_erasable=writable)
            return bool(present and writable)
        except Exception as e:
            self.logger.exception("IMAPI2 disc status check failed: %s", e)
            session.update_burner_state(detected=True, present=False, blank_or_erasable=False)
            session.set_error(f"Disc status check failed: {e}")
            return False

    # --- Device/status helpers for routes ---
    def list_devices_with_status(self) -> List[dict]:
        """Return devices and dynamic media status. Windows/IMAPI only."""

        if sys.platform != 'win32':
            msg = f"CD burning requires Windows IMAPI2 support (current platform: {sys.platform})."
            self.logger.error(msg)
            raise IMAPIUnavailableError(msg)

        if IMAPI2AudioBurner is None:
            msg = ("IMAPI2AudioBurner adapter is unavailable. Install 'comtypes' and ensure IMAPI2 is registered.")
            self.logger.error(msg)
            raise IMAPIUnavailableError(msg)

        assert IMAPI2AudioBurner is not None

        if self._imapi is None:
            try:
                self._imapi = IMAPI2AudioBurner(logger=self.logger, client_name="CD-Collector")
            except IMAPIUnavailableError as exc:
                msg = f"IMAPI2 initialization failed: {exc}"
                self.logger.error(msg)
                raise IMAPIUnavailableError(msg) from exc
            except Exception as exc:
                msg = f"Failed to initialize IMAPI2 burner: {exc}"
                self.logger.exception(msg)
                raise IMAPIUnavailableError(msg) from exc

        out: List[dict] = []

        devices = self._imapi.list_recorders()

        for dev in devices:
            present = False
            writable = False
            try:
                rec, _ = self._imapi.open_recorder(dev['unique_id'])
                present, writable = self._imapi.check_audio_disc_ready(rec)
            except Exception:
                pass

            display = f"{dev.get('vendor_id','').strip()} {dev.get('product_id','').strip()}".strip()

            out.append({
                'id': dev['unique_id'],
                'display_name': display or dev['unique_id'],
                'vendor_id': dev.get('vendor_id'),
                'product_id': dev.get('product_id'),
                'product_rev': dev.get('product_rev'),
                'volume_paths': list(dev.get('volume_paths') or []),
                'present': bool(present),
                'writable': bool(writable),
                'selected': dev['unique_id'] == self._imapi_recorder_id,
                'active': (self._active_session_id is not None) and (dev['unique_id'] == self._imapi_recorder_id),
            })

        return out

    def get_active_device_id(self) -> Optional[str]:
        return self._imapi_recorder_id

    def request_cancel(self, session_id: str) -> bool:
        ev = self._cancel_flags.get(session_id)
        if not ev:
            return False
        ev.set()
        return True

    def _parse_spotify_metadata(self, content_dir):
        """
        Parses the spotify_metadata.json file to get track order and titles.
        Returns a list of dictionaries, each containing 'title' and 'artist' for a track.
        """
        metadata_path = os.path.join(content_dir, "spotify_metadata.json")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"spotify_metadata.json not found in {content_dir}")

        self.logger.info(f"Parsing spotify_metadata.json from {metadata_path}")
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        tracks_data = []
        # Handle different Spotify item types (album, playlist, track)
        if 'tracks' in metadata and 'items' in metadata['tracks']: # Album or Playlist
            for item in metadata['tracks']['items']:
                track_info = item.get('track') if item.get('track') else item # Handle playlist vs album item structure
                if track_info:
                    tracks_data.append({
                        'title': track_info.get('name'),
                        'artist': track_info.get('artists')[0]['name'] if track_info.get('artists') else 'Unknown Artist'
                    })
        elif metadata.get('type') == 'track': # Single track
            tracks_data.append({
                'title': metadata.get('name'),
                'artist': metadata.get('artists')[0]['name'] if metadata.get('artists') else 'Unknown Artist'
            })
        else:
            raise ValueError("Unsupported spotify_metadata.json format. Expected album/playlist or single track.")

        if not tracks_data:
            raise ValueError("No tracks found in spotify_metadata.json to burn.")

        self.logger.info(f"Found {len(tracks_data)} tracks in metadata.")
        return tracks_data

    def _convert_mp3_to_wav(self, content_dir, tracks_data, temp_wav_dir, *, session: BurnSession, cancel_event: Optional[threading.Event] = None, publisher: Optional[ProgressPublisher] = None):
        """
        Converts MP3 files to WAV format in the specified temporary directory.
        Ensures 44.1 kHz, 16-bit, stereo for audio CD compatibility.
        Returns a list of paths to the converted WAV files, in the correct order.
        """
        self.logger.info(f"Starting MP3 to WAV conversion for {len(tracks_data)} tracks in {content_dir}...")
        wav_file_paths = []
        total_tracks = len(tracks_data)

        # Ensure ffmpeg/libav is accessible by pydub.
        # pydub.AudioSegment.ffmpeg = self.ffmpeg_path # Can explicitly set if needed

        conv_start = time.perf_counter()
        for i, track in enumerate(tracks_data):
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError("Burn canceled during audio conversion")
            # Sanitize track title for filename matching. This should mirror the download logic.
            # Replace invalid filename characters
            sanitized_title = re.sub(r'[\\/:*?"<>|]', '_', track['title'])
            sanitized_title = sanitized_title.strip()
            # Replace multiple underscores with a single one
            sanitized_title = re.sub(r'_{2,}', '_', sanitized_title)
            # This pattern attempts to match files named after the sanitized title
            mp3_file_name_pattern = f"{re.escape(sanitized_title)}\.mp3"
            found_mp3_path = None

            # Search for the MP3 file in the content_dir
            for f_name in os.listdir(content_dir):
                if re.fullmatch(mp3_file_name_pattern, f_name, re.IGNORECASE):
                    found_mp3_path = os.path.join(content_dir, f_name)
                    break

            # Fallback for "Artist - Title.mp3" format if initial match fails
            if not found_mp3_path:
                fallback_name_pattern = f"{re.escape(track['artist'])} - {re.escape(sanitized_title)}\.mp3"
                for f_name in os.listdir(content_dir):
                    if re.fullmatch(fallback_name_pattern, f_name, re.IGNORECASE):
                        found_mp3_path = os.path.join(content_dir, f_name)
                        break

            if not found_mp3_path:
                error_msg = f"MP3 file not found for track: '{track['title']}' (expected: {sanitized_title}.mp3 or {track['artist']} - {sanitized_title}.mp3). Aborting conversion."
                self.logger.error(error_msg)
                session.set_error(error_msg)
                raise FileNotFoundError(error_msg)

            # Prefix with number for correct burning order
            wav_output_path = os.path.join(temp_wav_dir, f"{i+1:02d}_{sanitized_title}.wav")

            try:
                self.logger.info(f"Converting '{os.path.basename(found_mp3_path)}' to WAV...")
                t0 = time.perf_counter()
                audio = AudioSegment.from_mp3(found_mp3_path)
                # Ensure 44.1 kHz, 16-bit, stereo for audio CD compatibility
                audio = audio.set_frame_rate(44100).set_channels(2).set_sample_width(2)
                audio.export(wav_output_path, format="wav")
                elapsed = time.perf_counter() - t0
                self.logger.info(f"Converted track {i+1}/{total_tracks} in {elapsed:.2f}s: {os.path.basename(wav_output_path)}")
                wav_file_paths.append(wav_output_path)
                # Conversion takes 45% of overall progress (5-50%)
                progress = 5 + int(((i + 1) / total_tracks) * 45)
                session.update_status(f"Converting WAVs ({i+1}/{total_tracks})", progress)
                if publisher is not None:
                    try:
                        publisher.publish({
                            'event': 'cd_burn_progress',
                            'status': 'converting',
                            'phase': 'converting',
                            'progress': progress,
                            'message': f'Converting {i+1}/{total_tracks}',
                            'track_index': i + 1,
                            'track_total': total_tracks,
                            'elapsed_sec': round(elapsed, 2),
                            'session_id': session.id,
                        })
                    except Exception:
                        pass
            except Exception as e:
                self.logger.exception(f"Error converting MP3 '{found_mp3_path}' to WAV: {e}")
                raise RuntimeError(f"Failed to convert '{track['title']}' to WAV: {e}")

        total_elapsed = time.perf_counter() - conv_start
        self.logger.info(f"Finished converting {len(wav_file_paths)} tracks to WAV in {total_elapsed:.2f}s.")
        if publisher is not None:
            try:
                publisher.publish({
                    'event': 'cd_burn_progress',
                    'status': 'converting',
                    'phase': 'converting',
                    'progress': 50,
                    'message': 'Conversion complete',
                    'session_id': session.id,
                    'elapsed_sec': round(total_elapsed, 2),
                })
            except Exception:
                pass
        return wav_file_paths

    def _execute_burn(self, wav_file_paths, disc_title="Audio CD", *, session: BurnSession, publisher: Optional[ProgressPublisher] = None, album_artist: Optional[str] = None, per_track_cdtext: Optional[list] = None, cancel_event: Optional[threading.Event] = None):
        """Burn using IMAPI2 AudioCD format on Windows."""
        if not self._imapi or not self._imapi_recorder:
            raise RuntimeError("IMAPI2 recorder not selected. Cannot burn.")
        if not wav_file_paths:
            raise ValueError("No WAV files provided for burning. Burn cannot proceed.")

        self.logger.info("Starting IMAPI2 Audio CD burn with title '%s'...", disc_title)
        session.update_status("Burning Disc...", progress=60)
        if publisher is not None:
            try:
                publisher.publish({
                    'event': 'cd_burn_progress',
                    'status': 'burning',
                    'phase': 'burning',
                    'progress': 60,
                    'message': 'Starting burn... ',
                    'session_id': session.id,
                })
            except Exception:
                pass

        # Best-effort CD-TEXT (album + per-track)
        album_cdtext = {'title': disc_title}
        if album_artist:
            album_cdtext['artist'] = album_artist
        # Try deriving artist from first track's metadata during parsing stage later if available

        cancel_flag = cancel_event or threading.Event()
        try:
            self._imapi.burn_audio_cd(
                recorder=self._imapi_recorder,
                wav_paths=wav_file_paths,
                album_cdtext=album_cdtext,
                per_track_cdtext=per_track_cdtext,
                session=session,
                publisher=publisher,
                cancel_flag=cancel_flag,
            )
            if publisher is not None:
                try:
                    publisher.publish({'event': 'cd_burn_complete', 'status': 'completed', 'phase': 'completed', 'progress': 100, 'session_id': session.id})
                except Exception:
                    pass
        except Exception as e:
            self.logger.exception("IMAPI2 burn failed: %s", e)
            raise RuntimeError(f"CD burning failed: {e}")


    def _cleanup_temp_dir(self, temp_dir):
        """Removes the temporary directory and its contents, used for WAV files."""
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except OSError as e:
                self.logger.error(f"Error removing temporary directory {temp_dir}: {e}")

    def burn_cd(self, content_dir, item_title, *, session: BurnSession, publisher: Optional[ProgressPublisher] = None):
        """
        Orchestrates the entire CD burning process.
        This method is designed to be called in a separate thread.
        """
        temp_wav_dir = None
        # register cancel flag for this session
        cancel_event = threading.Event()
        self._cancel_flags[session.id] = cancel_event
        self._active_session_id = session.id
        try:
            self.logger.info(f"Starting CD burn process for content from: {content_dir}")
            session.start(status=f"Preparing to burn '{item_title}'...", progress=0)
            if publisher is not None:
                try:
                    publisher.publish({
                        'event': 'cd_burn_progress',
                        'status': 'preparing',
                        'phase': 'preparing',
                        'progress': 0,
                        'message': f"Preparing to burn '{item_title}'...",
                        'session_id': session.id,
                    })
                except Exception:
                    pass

            # 0. Validate inputs early and fail fast
            session.update_status("Validating content directory...", progress=0)
            if not isinstance(content_dir, str) or not content_dir:
                raise ValueError("Invalid content directory path provided.")
            if not os.path.isdir(content_dir):
                raise FileNotFoundError(f"Content directory not found: {content_dir}")
            try:
                # Basic readability check
                _ = os.listdir(content_dir)
            except PermissionError as e:
                raise PermissionError(f"Content directory not readable: {content_dir} ({e})")
            metadata_path = os.path.join(content_dir, "spotify_metadata.json")
            if not os.path.exists(metadata_path):
                raise FileNotFoundError(f"Missing spotify_metadata.json in content directory: {content_dir}")

            # 1. Scan for burner and check disc status
            if not self.scan_for_burner(session):
                raise RuntimeError("No compatible CD burner found. Please ensure a burner is connected.")
            if not self.check_disc_status(session):
                raise RuntimeError("No blank or erasable disc found in the burner. Please insert a disc.")

            # 2. Parse Spotify metadata to get track order and details
            tracks_data = self._parse_spotify_metadata(content_dir)
            self.logger.info(f"Successfully parsed {len(tracks_data)} tracks from metadata.")
            if publisher is not None:
                try:
                    publisher.publish({
                        'event': 'cd_burn_progress',
                        'status': 'preparing',
                        'phase': 'preparing',
                        'progress': 5,
                        'message': 'Validation complete; starting conversion',
                        'session_id': session.id,
                    })
                except Exception:
                    pass

            # 3. Create a temporary directory for converted WAV files
            temp_wav_dir = tempfile.mkdtemp(prefix='cd_burn_wavs_')
            self.logger.info(f"Created temporary WAV directory: {temp_wav_dir}")

            # 4. Convert MP3s to WAVs suitable for audio CD
            session.update_status("Converting MP3s to WAVs...", progress=5)
            wav_file_paths = self._convert_mp3_to_wav(content_dir, tracks_data, temp_wav_dir, session=session, cancel_event=cancel_event, publisher=publisher)
            if not wav_file_paths:
                raise RuntimeError("No WAV files were successfully converted. Aborting burn.")

            # 5. Execute the actual CD burning command
            session.update_status("Initiating CD burn...", progress=50)
            if publisher is not None:
                try:
                    publisher.publish({
                        'event': 'cd_burn_progress',
                        'status': 'staging',
                        'phase': 'staging',
                        'progress': 50,
                        'message': 'Staging tracks...',
                        'session_id': session.id,
                    })
                except Exception:
                    pass
            album_artist = tracks_data[0].get('artist') if tracks_data else None
            per_track_cdtext = tracks_data
            self._execute_burn(
                wav_file_paths,
                disc_title=item_title,
                session=session,
                publisher=publisher,
                album_artist=album_artist,
                per_track_cdtext=per_track_cdtext,
                cancel_event=cancel_event,
            )

            session.complete()
            self.logger.info(f"CD burn for '{item_title}' completed successfully.")

        except (FileNotFoundError, ValueError, RuntimeError) as e:
            # Catch specific errors from internal methods
            self.logger.error(f"CD burning process failed due to: {e}")
            session.set_error(f"Burning Failed: {e}")
        except Exception as e:
            # Catch any other unexpected errors
            self.logger.exception("An unhandled error occurred during CD burning process.")
            session.set_error(f"Unexpected Error during burn: {str(e)}")
        finally:
            # Always attempt to clean up temporary WAV directory
            if temp_wav_dir:
                self._cleanup_temp_dir(temp_wav_dir)
            # Ensure is_burning is reset even if an exception occurs mid-process
            # Only reset if it's still marked as burning and not already set to error/completed
            if getattr(session, 'is_burning', False) and getattr(session, 'current_status', '') not in ("Completed", "Error"):
                session.set_error("Burn process interrupted or failed unexpectedly.")
            # cleanup cancel flag and active device
            try:
                self._cancel_flags.pop(session.id, None)
            except Exception:
                pass
            self._active_session_id = None
