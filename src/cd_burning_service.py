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
from .lyrics_service import LyricsService

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
        # Utilities
        self._lyrics_svc = LyricsService()

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
                    self._imapi = IMAPI2AudioBurner(logger=self.logger, client_name="BeatHub")
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
                self._imapi = IMAPI2AudioBurner(logger=self.logger, client_name="BeatHub")
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

    # --- Filename matching helpers ---
    def _sanitize_title_for_filename(self, title: str) -> str:
        """Mimic spotDL's basic sanitization we expect in filenames."""
        sanitized = re.sub(r'[\\/:*?\"<>|]', '_', title or '')
        sanitized = sanitized.strip()
        sanitized = re.sub(r'_{2,}', '_', sanitized)
        return sanitized

    def _norm_for_match(self, s: str) -> str:
        """Normalization used for fuzzy comparisons (case/space/punct insensitive)."""
        s = (s or '').lower()
        s = s.replace('�?T', "'")
        s = re.sub(r"[\\/:*?\"<>|.,!()\[\]{}]", "", s)
        s = s.replace('_', '')
        s = re.sub(r"\s+", "", s)
        return s

    def _find_mp3_for_track(self, all_files: List[str], *, artist: str, title: str) -> Optional[str]:
        """
        Find the matching MP3 path for a given artist/title, tolerating filenames that include
        optional "(feat …)" suffixes and the common "Artist - Title" prefix form.

        Checks exact patterns first, then applies a constrained fuzzy match that only accepts
        surplus segments starting with feat/featuring/ft/with after the expected prefix.
        """
        sanitized_title = self._sanitize_title_for_filename(title)
        title_re = re.escape(sanitized_title)
        artist_re = re.escape(artist or '')

        # Common explicit patterns
        patterns = [
            rf"^{title_re}\.mp3$",
            rf"^{title_re}\s*\((?:feat\.?|featuring|ft\.?|with)\s+[^)]*\)\.mp3$",
            rf"^{artist_re}\s*-\s*{title_re}\.mp3$",
            rf"^{artist_re}\s*-\s*{title_re}\s*\((?:feat\.?|featuring|ft\.?|with)\s+[^)]*\)\.mp3$",
        ]

        # Fast pass on explicit regexes
        for path in all_files:
            base = os.path.basename(path)
            for pat in patterns:
                if re.fullmatch(pat, base, flags=re.IGNORECASE):
                    return path

        # Constrained fuzzy match: allow only extra 'feat*' tail after expected normalized base
        exp1 = self._norm_for_match(sanitized_title)
        exp2 = self._norm_for_match(f"{artist} - {sanitized_title}")
        exp_title = self._norm_for_match(title)
        artist_norm = self._norm_for_match(artist or '')
        for path in all_files:
            base_no_ext = os.path.splitext(os.path.basename(path))[0]
            nb = self._norm_for_match(base_no_ext)
            if nb == exp1 or nb == exp2:
                return path
            if nb.startswith(exp1):
                rest = nb[len(exp1):]
                if rest and re.match(r"^(feat|featuring|ft|with)[a-z0-9].*", rest):
                    return path
            if nb.startswith(exp2):
                rest = nb[len(exp2):]
                if rest and re.match(r"^(feat|featuring|ft|with)[a-z0-9].*", rest):
                    return path
            # Accept additional artists before the hyphen, e.g., "Artist, Other - Title"
            tail1 = '-' + exp1
            tail2 = '-' + exp_title
            if nb.endswith(tail1):
                left = nb[: -len(tail1)]
                if not artist_norm or left.startswith(artist_norm):
                    return path
            if nb.endswith(tail2):
                left = nb[: -len(tail2)]
                if not artist_norm or left.startswith(artist_norm):
                    return path
        return None

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
                self._imapi = IMAPI2AudioBurner(logger=self.logger, client_name="BeatHub")
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
        Parses spotify_metadata.json and returns a list for CD-Text ordering:
        [{ 'title': str, 'artist': str } ...]

        Supports multiple formats:
        - Saved app format: top-level 'tracks' is a list of track dicts with 'title' and 'artists' (array)
        - Raw Spotify album/playlist: 'tracks': {'items': [ {track or item} ]}
        - Single track: top-level 'type' or 'item_type' == 'track'
        """
        metadata_path = os.path.join(content_dir, "spotify_metadata.json")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"spotify_metadata.json not found in {content_dir}")

        self.logger.info(f"Parsing spotify_metadata.json from {metadata_path}")
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        tracks_data: List[dict] = []

        # 1) Saved app format: 'tracks' is a list with our normalized fields
        if isinstance(metadata.get('tracks'), list):
            for t in metadata['tracks']:
                title = t.get('title') or t.get('name')
                artists = t.get('artists') or []
                artist = None
                if isinstance(artists, list) and artists:
                    artist = artists[0]
                elif isinstance(artists, str):
                    artist = artists
                else:
                    artist = t.get('album_artist') or 'Unknown Artist'
                if title:
                    tracks_data.append({
                        'title': title,
                        'artist': artist,
                        'track_number': t.get('track_number'),
                        'disc_number': t.get('disc_number'),
                    })

        # 2) Raw Spotify format: album/playlist with tracks.items
        elif 'tracks' in metadata and isinstance(metadata['tracks'], dict) and 'items' in metadata['tracks']:
            for item in metadata['tracks']['items']:
                track_info = item.get('track') if isinstance(item, dict) and item.get('track') else item
                if track_info:
                    title = track_info.get('name') or track_info.get('title')
                    arts = track_info.get('artists') or []
                    artist = None
                    if isinstance(arts, list) and arts:
                        first = arts[0]
                        artist = first.get('name') if isinstance(first, dict) else str(first)
                    if title:
                        tracks_data.append({
                            'title': title,
                            'artist': artist or 'Unknown Artist',
                            'track_number': track_info.get('track_number'),
                            'disc_number': track_info.get('disc_number'),
                        })

        # 3) Single track objects (raw or saved)
        elif (metadata.get('type') == 'track') or (metadata.get('item_type') == 'track'):
            title = metadata.get('name') or metadata.get('title')
            arts = metadata.get('artists') or []
            artist = None
            if isinstance(arts, list) and arts:
                first = arts[0]
                artist = first.get('name') if isinstance(first, dict) else str(first)
            tracks_data.append({
                'title': title or 'Unknown Title',
                'artist': artist or 'Unknown Artist',
                'track_number': metadata.get('track_number'),
                'disc_number': metadata.get('disc_number'),
            })
        else:
            raise ValueError("Unsupported spotify_metadata.json format. Expected list 'tracks', album/playlist or track.")

        if not tracks_data:
            raise ValueError("No tracks found in spotify_metadata.json to burn.")

        # Sort by disc_number then track_number when available to enforce expected order
        def _key(t: dict):
            try:
                d = int(t.get('disc_number') or 1)
            except Exception:
                d = 1
            try:
                n = int(t.get('track_number') or 0)
            except Exception:
                n = 0
            return (d, n)

        # Only sort if at least one entry has a track_number/disc_number
        if any(t.get('track_number') is not None or t.get('disc_number') is not None for t in tracks_data):
            tracks_data.sort(key=_key)

        self.logger.info(f"Found {len(tracks_data)} tracks in metadata.")
        return tracks_data

    def generate_burn_plan(self, content_dir: str, disc_title: Optional[str] = None) -> dict:
        """
        Build a dry-run burn plan without converting/burning.

        - Parses spotify_metadata.json for track order
        - Resolves expected MP3 paths in order using same matching rules as conversion
        - Summarizes per-track info (title, artist, file, duration, lyrics)
        - Computes total duration and capacity fit for 74/80 minute CDs
        - Returns CD-Text fields that would be used
        """
        if not content_dir or not os.path.isdir(content_dir):
            raise FileNotFoundError(f"Content directory not found: {content_dir}")
        # Ensure metadata exists and parse
        tracks_data = self._parse_spotify_metadata(content_dir)

        # Try to infer album/playlist name for disc title if not provided
        album_title = None
        album_artist = None
        meta_path = os.path.join(content_dir, "spotify_metadata.json")
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            album_title = meta.get('title') or meta.get('name') or None
            # album/playlist artist best-effort
            try:
                if meta.get('artist'):
                    album_artist = meta.get('artist')
                elif meta.get('type') == 'album' and meta.get('artists'):
                    album_artist = meta['artists'][0].get('name')
            except Exception:
                pass
        except Exception:
            pass

        disc_title = disc_title or album_title or "Audio CD"

        # Resolve MP3 files in the same way as in conversion
        track_plans: List[dict] = []
        missing: List[dict] = []
        total_seconds: float = 0.0

        # Pre-list files recursively once for performance
        try:
            all_files: List[str] = []
            for root, _, files in os.walk(content_dir):
                for n in files:
                    all_files.append(os.path.join(root, n))
        except Exception as e:
            raise RuntimeError(f"Failed to list content directory: {e}")

        # Prepare saved metadata tracks list if present for duration fallback
        saved_meta_tracks = None
        duration_by_num: Dict[tuple, float] = {}
        try:
            if isinstance(meta.get('tracks'), list):
                saved_meta_tracks = meta['tracks']
                for rt in saved_meta_tracks:
                    try:
                        dn = int(rt.get('disc_number') or 1)
                    except Exception:
                        dn = 1
                    try:
                        tn = int(rt.get('track_number') or 0)
                    except Exception:
                        tn = 0
                    ms = rt.get('duration_ms')
                    if isinstance(ms, (int, float)) and ms > 0:
                        duration_by_num[(dn, tn)] = float(ms) / 1000.0
        except Exception:
            saved_meta_tracks = None

        # Normalization helper for robust filename matching
        def _norm(s: str) -> str:
            s = (s or "").lower()
            s = s.replace('’', "'")
            s = re.sub(r"[\\/:*?\"<>|.,!()\[\]{}]", "", s)
            s = s.replace('_', '')
            s = re.sub(r"\s+", "", s)
            return s

        for idx, track in enumerate(tracks_data, start=1):
            title = track.get('title') or 'Unknown Title'
            artist = track.get('artist') or 'Unknown Artist'
            sanitized_title = re.sub(r'[\\/:*?"<>|]', '_', title).strip()
            sanitized_title = re.sub(r'_{2,}', '_', sanitized_title)
            mp3_file_name_pattern = f"{re.escape(sanitized_title)}\.mp3"
            fallback_name_pattern = f"{re.escape(artist)} - {re.escape(sanitized_title)}\.mp3"

            found_mp3 = None
            for path in all_files:
                base = os.path.basename(path)
                if re.fullmatch(mp3_file_name_pattern, base, re.IGNORECASE):
                    found_mp3 = path
                    break
            if not found_mp3:
                for path in all_files:
                    base = os.path.basename(path)
                    if re.fullmatch(fallback_name_pattern, base, re.IGNORECASE):
                        found_mp3 = path
                        break
            # Fuzzy-normalized match (handles trailing underscores/punctuation)
            if not found_mp3:
                exp1 = _norm(sanitized_title)
                exp2 = _norm(f"{artist} - {sanitized_title}")
                exp3 = _norm(title)
                exp4 = _norm(f"{artist} - {title}")
                artist_norm = _norm(artist)
                for path in all_files:
                    base_no_ext = os.path.splitext(os.path.basename(path))[0]
                    nb = _norm(base_no_ext)
                    # Accept exact normalized matches, or normalized names that start with the expected
                    # title/artist-title followed by a 'feat*' suffix (to handle e.g. "(feat. X)").
                    if (
                        nb in (exp1, exp2, exp3, exp4)
                        or (nb.startswith(exp1) and nb[len(exp1):].startswith(('feat', 'featuring', 'ft', 'with')))
                        or (nb.startswith(exp2) and nb[len(exp2):].startswith(('feat', 'featuring', 'ft', 'with')))
                    ):
                        found_mp3 = path
                        break
                    # Also accept extra artists before the hyphen, e.g., "Artist, Other - Title"
                    tail1 = '-' + exp1
                    tail3 = '-' + exp3
                    if nb.endswith(tail1):
                        left = nb[: -len(tail1)]
                        if not artist_norm or left.startswith(artist_norm):
                            found_mp3 = path
                            break
                    if nb.endswith(tail3):
                        left = nb[: -len(tail3)]
                        if not artist_norm or left.startswith(artist_norm):
                            found_mp3 = path
                            break

            duration_sec = None
            has_lyrics = None
            if found_mp3 and os.path.exists(found_mp3):
                # Duration via mutagen (fast)
                try:
                    from mutagen import File as MutagenFile  # type: ignore
                    mf = MutagenFile(found_mp3)
                    info = getattr(mf, 'info', None)
                    length = getattr(info, 'length', None)
                    if length:
                        duration_sec = float(length)
                except Exception:
                    # If mutagen fails, leave duration None
                    pass
                try:
                    lyr = self._lyrics_svc.extract_lyrics_from_audio(found_mp3)
                    has_lyrics = bool(lyr and lyr.strip())
                except Exception:
                    has_lyrics = None
            else:
                missing.append({
                    'index': idx,
                    'title': title,
                    'artist': artist,
                    'expected': [
                        f"{sanitized_title}.mp3",
                        f"{sanitized_title} (feat. ...).mp3",
                        f"{artist} - {sanitized_title}.mp3",
                        f"{artist} - {sanitized_title} (feat. ...).mp3",
                        f"{artist}, ... - {sanitized_title}.mp3",
                    ],
                })

            # Duration fallback from saved metadata if not determined from file
            if duration_sec is None and saved_meta_tracks:
                try:
                    dn = int(track.get('disc_number') or 1)
                except Exception:
                    dn = 1
                try:
                    tn = int(track.get('track_number') or 0)
                except Exception:
                    tn = 0
                if (dn, tn) in duration_by_num:
                    duration_sec = duration_by_num[(dn, tn)]
                elif len(saved_meta_tracks) >= idx:
                    try:
                        raw = saved_meta_tracks[idx - 1]
                        ms = raw.get('duration_ms')
                        if isinstance(ms, (int, float)) and ms > 0:
                            duration_sec = float(ms) / 1000.0
                    except Exception:
                        pass

            track_plans.append({
                'index': idx,
                'title': title,
                'artist': artist,
                'file': found_mp3,
                'duration_sec': None if duration_sec is None else round(duration_sec, 2),
                'has_embedded_lyrics': has_lyrics,
            })

            if duration_sec:
                total_seconds += float(duration_sec)

        # Find stray audio files not referenced by metadata
        referenced = {os.path.basename(t['file']) for t in track_plans if t.get('file')}
        stray_audio: List[str] = []
        for path in all_files:
            base = os.path.basename(path)
            low = base.lower()
            if low.endswith(('.mp3', '.flac', '.wav', '.ogg', '.m4a')):
                if base not in referenced:
                    stray_audio.append(path)

        # Capacity checks using configured capacities
        try:
            primary_min = int(getattr(Config, 'CD_CAPACITY_MINUTES', 80) or 80)
        except Exception:
            primary_min = 80
        try:
            secondary_min = int(getattr(Config, 'CD_ALT_CAPACITY_MINUTES', 74) or 0)
        except Exception:
            secondary_min = 0

        cap_primary_sec = max(1, primary_min) * 60
        cap_secondary_sec = max(0, secondary_min) * 60 if secondary_min else 0

        fits_primary = total_seconds <= cap_primary_sec
        fits_secondary = (total_seconds <= cap_secondary_sec) if cap_secondary_sec else None

        # Legacy flags maintained for compatibility (based on 74/80 mins)
        fits_74 = total_seconds <= 74 * 60
        fits_80 = total_seconds <= 80 * 60

        # CD-Text composition
        album_cdtext = {'title': disc_title}
        if album_artist:
            album_cdtext['artist'] = album_artist
        elif tracks_data:
            album_cdtext['artist'] = tracks_data[0].get('artist')

        per_track_cdtext = [
            {'title': t.get('title'), 'artist': t.get('artist')}
            for t in tracks_data
        ]

        status = 'ok' if not missing else 'incomplete'
        warnings = []
        if not fits_primary:
            warnings.append(f'Total duration exceeds {primary_min}-minute CD capacity')
        elif cap_secondary_sec and not fits_secondary:
            warnings.append(f'Total duration exceeds {secondary_min}-minute CD, but fits {primary_min}-minute CD')

        # Try to include raw tracks from saved metadata for UI richness
        raw_tracks = None
        try:
            if isinstance(meta.get('tracks'), list):
                raw_tracks = meta['tracks']
        except Exception:
            pass

        plan = {
            'status': status,
            'disc_title': disc_title,
            'album_title': album_title or disc_title,
            'album_artist': album_cdtext.get('artist'),
            'content_dir': content_dir,
            'track_count': len(track_plans),
            'tracks': track_plans,
            'raw_tracks': raw_tracks,
            'missing_tracks': missing,
            'stray_audio_files': stray_audio,
            'total_duration_sec': round(total_seconds, 2),
            # Legacy
            'fits_74_min_cd': fits_74,
            'fits_80_min_cd': fits_80,
            # Dynamic capacities
            'capacity_primary_min': primary_min,
            'capacity_secondary_min': secondary_min if cap_secondary_sec else None,
            'fits_primary': fits_primary,
            'fits_secondary': fits_secondary,
            'time_left_primary_sec': round(cap_primary_sec - total_seconds, 2),
            'time_left_secondary_sec': round(cap_secondary_sec - total_seconds, 2) if cap_secondary_sec else None,
            'cd_text': {
                'album': album_cdtext,
                'per_track': per_track_cdtext,
            },
            'warnings': warnings,
        }
        return plan

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
        # Normalization helper shared with preview
        def _norm_conv(s: str) -> str:
            s = (s or "").lower()
            s = s.replace('’', "'")
            s = re.sub(r"[\\/:*?\"<>|.,!()\[\]{}]", "", s)
            s = s.replace('_', '')
            s = re.sub(r"\s+", "", s)
            return s

        # Build recursive file list to handle nested directories
        all_files = []
        for root, _, files in os.walk(content_dir):
            for n in files:
                if n.lower().endswith('.mp3'):
                    all_files.append(os.path.join(root, n))

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

            # Search exact sanitized in recursive list
            for f_path in all_files:
                base = os.path.basename(f_path)
                if re.fullmatch(mp3_file_name_pattern, base, re.IGNORECASE):
                    found_mp3_path = f_path
                    break

            # Fallback for "Artist - Title.mp3" format if initial match fails
            if not found_mp3_path:
                fallback_name_pattern = f"{re.escape(track['artist'])} - {re.escape(sanitized_title)}\.mp3"
                for f_path in all_files:
                    base = os.path.basename(f_path)
                    if re.fullmatch(fallback_name_pattern, base, re.IGNORECASE):
                        found_mp3_path = f_path
                        break

            # Fuzzy-normalized match (handles trailing underscores/punctuation)
            if not found_mp3_path:
                exp1 = _norm_conv(sanitized_title)
                exp2 = _norm_conv(f"{track['artist']} - {sanitized_title}")
                exp3 = _norm_conv(track['title'])
                exp4 = _norm_conv(f"{track['artist']} - {track['title']}")
                for f_path in all_files:
                    base_no_ext = os.path.splitext(os.path.basename(f_path))[0]
                    nb = _norm_conv(base_no_ext)
                    # Accept exact normalized matches, or normalized names that start with the expected
                    # title/artist-title followed by a 'feat*' suffix (to handle e.g. "(feat. X)").
                    if (
                        nb in (exp1, exp2, exp3, exp4)
                        or (nb.startswith(exp1) and nb[len(exp1):].startswith(('feat', 'featuring', 'ft', 'with')))
                        or (nb.startswith(exp2) and nb[len(exp2):].startswith(('feat', 'featuring', 'ft', 'with')))
                    ):
                        found_mp3_path = f_path
                        break

            # Final fallback: use robust fuzzy matching that tolerates multi-artist prefixes
            if not found_mp3_path:
                found_mp3_path = self._find_mp3_for_track(
                    all_files,
                    artist=track.get('artist') or '',
                    title=track.get('title') or '',
                )

            if not found_mp3_path:
                error_msg = (
                    f"MP3 file not found for track: '{track['title']}' (expected one of: "
                    f"{sanitized_title}.mp3, {sanitized_title} (feat. ...).mp3, "
                    f"{track['artist']} - {sanitized_title}.mp3, {track['artist']} - {sanitized_title} (feat. ...).mp3, "
                    f"{track['artist']}, ... - {sanitized_title}.mp3). "
                    "Aborting conversion."
                )
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
