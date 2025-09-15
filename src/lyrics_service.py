import logging
import re
import os
from typing import Optional

from config import Config

logger = logging.getLogger(__name__)

try:
    # Prefer importing mutagen lazily in call sites, but keep top-level available if installed
    from mutagen import File as MutagenFile  # type: ignore
    from mutagen.id3 import ID3, USLT  # type: ignore
    from mutagen.mp3 import MP3  # type: ignore
    from mutagen.mp4 import MP4  # type: ignore
    from mutagen.flac import FLAC  # type: ignore
    from mutagen.oggvorbis import OggVorbis  # type: ignore
except Exception:  # pragma: no cover - mutagen is in requirements; defensive import only
    MutagenFile = None  # type: ignore
    ID3 = USLT = MP3 = MP4 = FLAC = OggVorbis = None  # type: ignore


class LyricsService:
    def __init__(self, genius_access_token=None):
        """Lyrics utilities for the SpotDL pipeline.

        Note: External lyrics fetching via Genius API is removed. SpotDL can
        embed lyrics using its own providers (optionally using a Genius token)
        during download; this service focuses on extracting and exporting
        embedded lyrics from audio files.
        """
        # Keep compatibility for callers that passed a token; handled by SpotDL
        # at download time via settings. This class does not use the token.
        _ = genius_access_token or Config.GENIUS_ACCESS_TOKEN

    def _sanitize_filename(self, name):
        """Sanitizes a string to be used as a filename."""
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        name = name.strip()
        name = re.sub(r'_{2,}', '_', name)
        return name

    # --- SpotDL pipeline path: extract embedded lyrics from audio files ---
    def extract_lyrics_from_audio(self, audio_path: str) -> Optional[str]:
        """Extract unsynced lyrics embedded in an audio file's tags.

        Supports common containers:
        - MP3 (ID3 USLT frames)
        - MP4/M4A (©lyr atom)
        - FLAC/OGG (Vorbis comments: lyrics/LYRICS/unsyncedlyrics)

        Returns the lyrics text if found; otherwise None.
        """
        if not audio_path or not os.path.exists(audio_path):
            return None
        if MutagenFile is None:  # pragma: no cover
            logger.debug("mutagen not available; cannot read embedded lyrics")
            return None

        try:
            mf = MutagenFile(audio_path, easy=False)
        except Exception as e:
            logger.debug("Failed to read audio tags for %s: %s", audio_path, e)
            return None

        if mf is None:
            return None

        # MP3 (ID3)
        try:
            if MP3 is not None and isinstance(mf, MP3):
                try:
                    id3 = ID3(audio_path)
                except Exception:
                    id3 = getattr(mf, 'tags', None)
                if id3 is not None:
                    try:
                        frames = id3.getall('USLT')  # type: ignore[attr-defined]
                    except Exception:
                        frames = []
                    texts = []
                    for fr in frames or []:
                        txt = getattr(fr, 'text', None)
                        if isinstance(txt, list):
                            texts.extend([t for t in txt if t])
                        elif isinstance(txt, str):
                            texts.append(txt)
                    joined = "\n".join([t for t in texts if t]).strip()
                    if joined:
                        return joined
        except Exception:
            pass

        # MP4/M4A
        try:
            if MP4 is not None and isinstance(mf, MP4):
                tags = mf.tags or {}
                vals = tags.get('©lyr') or tags.get('lyr')
                if vals:
                    if isinstance(vals, list):
                        text = "\n".join([v for v in vals if isinstance(v, str)])
                    else:
                        text = str(vals)
                    text = (text or "").strip()
                    if text:
                        return text
        except Exception:
            pass

        # FLAC / OGG (Vorbis comments)
        try:
            tags = getattr(mf, 'tags', None)
            if tags:
                for key in ('lyrics', 'LYRICS', 'unsyncedlyrics', 'UNSYNCEDLYRICS'):
                    vals = tags.get(key)
                    if vals:
                        if isinstance(vals, (list, tuple)):
                            text = "\n".join([str(v) for v in vals if v])
                        else:
                            text = str(vals)
                        text = (text or "").strip()
                        if text:
                            return text
        except Exception:
            pass

        return None

    def export_embedded_lyrics(self, audio_path: str, txt_path: Optional[str] = None) -> Optional[str]:
        """Export embedded lyrics to a .txt file alongside the audio.

        - If lyrics are present, writes a UTF-8 .txt and returns its path.
        - If no lyrics or any error occurs, returns None gracefully.
        """
        lyrics = self.extract_lyrics_from_audio(audio_path)
        if not lyrics:
            return None
        try:
            base_dir = os.path.dirname(audio_path)
            if not txt_path:
                base = os.path.splitext(os.path.basename(audio_path))[0]
                txt_path = os.path.join(base_dir, f"{base}.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(lyrics)
            logger.info("Exported embedded lyrics to %s", txt_path)
            return txt_path
        except Exception as e:
            logger.debug("Failed to export embedded lyrics for %s: %s", audio_path, e)
            return None
