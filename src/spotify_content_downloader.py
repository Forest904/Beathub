import logging
import os
import threading
from typing import List, Optional

import spotipy  # Legacy spotipy kept for fallback
from spotipy.oauth2 import SpotifyClientCredentials
from config import Config

# Services
from .metadata_service import MetadataService
from .download_service import AudioCoverDownloadService
from .lyrics_service import LyricsService
from .file_manager import FileManager

# SpotDL client wrapper and DTO mapping (Phase 2/3)
from .spotdl_client import build_default_client, SpotdlClient
from .models.dto import TrackDTO, ItemDTO
from .models.spotdl_mapping import song_to_track_dto, songs_to_item_dto

# DB
from .database.db_manager import db, DownloadedTrack

logger = logging.getLogger(__name__)

class SpotifyContentDownloader:
    def __init__(
        self,
        base_output_dir=None,
        spotify_client_id=None,
        spotify_client_secret=None,
        genius_access_token=None,
        spotdl_audio_source=None,
        spotdl_format=None,
    ):
        """Initializes the SpotifyContentDownloader with all necessary services."""

        # Configuration values (fallback to Config if not provided)
        self.base_output_dir = base_output_dir if base_output_dir is not None else Config.BASE_OUTPUT_DIR
        self._spotify_client_id = spotify_client_id or Config.SPOTIPY_CLIENT_ID
        self._spotify_client_secret = spotify_client_secret or Config.SPOTIPY_CLIENT_SECRET
        self._genius_access_token = genius_access_token or Config.GENIUS_ACCESS_TOKEN
        self._spotdl_audio_source = spotdl_audio_source or Config.SPOTDL_AUDIO_SOURCE
        self._spotdl_format = spotdl_format or Config.SPOTDL_FORMAT

        # Initialize the sub-services, passing them their respective configuration
        self.metadata_service = MetadataService(
            spotify_client_id=self._spotify_client_id,
            spotify_client_secret=self._spotify_client_secret
        )
        self.audio_cover_download_service = AudioCoverDownloadService(
            base_output_dir=self.base_output_dir,
            spotdl_audio_source=(self._spotdl_audio_source or "youtube-music"),
            spotdl_format=(self._spotdl_format or "mp3"),
        )
        self.lyrics_service = LyricsService(genius_access_token=self._genius_access_token)
        self.file_manager = FileManager(base_output_dir=self.base_output_dir)

        # Initialize Spotipy directly within the downloader for artist search access (legacy)
        # This uses the same credentials passed to MetadataService
        self.sp = None # Initialize to None
        if self._spotify_client_id and self._spotify_client_secret:
            try:
                self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                    client_id=self._spotify_client_id,
                    client_secret=self._spotify_client_secret
                ))
                logger.info("Spotipy instance initialized within SpotifyContentDownloader.")
            except Exception as e:
                logger.error(f"Failed to initialize Spotipy in SpotifyContentDownloader: {e}", exc_info=True)
        else:
            logger.warning("Spotify client ID or secret missing. Spotipy instance for direct searches will not be available.")

        # SpotDL client is resolved lazily per call to avoid startup hard-failure
        self._spotdl_client: Optional[SpotdlClient] = None

        logger.info("SpotifyContentDownloader initialized with decoupled services and configuration passed.")

    def get_spotipy_instance(self):
        """ Provides access to the initialized Spotipy instance. """
        return self.sp

    def _resolve_spotdl_client(self) -> Optional[SpotdlClient]:
        """Return a SpotdlClient from Flask app context or build a default one."""
        if self._spotdl_client is not None:
            return self._spotdl_client
        try:
            from flask import current_app
            cli = current_app.extensions.get('spotdl_client')  # type: ignore[attr-defined]
            if isinstance(cli, SpotdlClient):
                self._spotdl_client = cli
                return self._spotdl_client
        except Exception:
            pass
        try:
            self._spotdl_client = build_default_client(app_logger=logger)
            return self._spotdl_client
        except Exception as e:
            logger.warning("SpotDL client unavailable, falling back to legacy metadata: %s", e)
            return None

    def _parse_item_type(self, link: str) -> str:
        lower = link.lower()
        if "playlist" in lower:
            return "playlist"
        if "album" in lower:
            return "album"
        if "track" in lower:
            return "track"
        return "unknown"

    def _extract_spotify_id(self, link: str) -> str:
        try:
            from urllib.parse import urlparse
            path = urlparse(link).path
            segs = [s for s in path.split('/') if s]
            return segs[-1] if segs else ""
        except Exception:
            return ""

    def download_spotify_content(self, spotify_link):
        """Orchestrates the download using SpotDL Song as canonical metadata source."""
        # Prefer SpotDL for metadata
        spotdl_client = self._resolve_spotdl_client()
        songs = []
        item_dto: Optional[ItemDTO] = None
        if spotdl_client:
            try:
                songs = spotdl_client.search([spotify_link])
                if songs:
                    item_dto = songs_to_item_dto(songs, spotify_link=spotify_link)
            except Exception as e:
                logger.exception("SpotDL search failed: %s", e)

        # Fallback to legacy metadata if SpotDL unavailable
        if item_dto is None:
            initial_metadata = self.metadata_service.get_metadata_from_link(spotify_link)
            if not initial_metadata:
                return {"status": "error", "message": "Could not retrieve metadata for the given Spotify link."}
            artist_name = initial_metadata.get('artist', 'Unknown Artist')
            title_name = initial_metadata.get('title', 'Unknown Title')
            cover_url = initial_metadata.get('image_url')
            item_type = initial_metadata.get('item_type', 'unknown')
            # Build minimal ItemDTO for downstream compatibility
            item_dto = ItemDTO(
                item_type=item_type,
                artist=artist_name,
                title=title_name,
                cover_url=cover_url,
                spotify_link=spotify_link,
                tracks=[],
            )

        # Derive resolved item type (playlist/album/track)
        resolved_item_type = self._parse_item_type(spotify_link)
        if resolved_item_type != "unknown":
            item_type = resolved_item_type
        else:
            item_type = item_dto.item_type

        # Determine spotify_id for the container
        spotify_id = ""
        if songs:
            first = songs[0]
            if item_type == "track":
                spotify_id = first.song_id
            elif item_type == "album":
                spotify_id = first.album_id or self._extract_spotify_id(spotify_link)
            elif item_type == "playlist":
                spotify_id = self._extract_spotify_id(spotify_link)
        else:
            spotify_id = self._extract_spotify_id(spotify_link)

        artist_name = item_dto.artist
        title_name = item_dto.title
        image_url_from_metadata = item_dto.cover_url
        spotify_url = spotify_link  # Use input link as canonical container URL

        # Create specific output directory
        item_specific_output_dir = self.file_manager.create_item_output_directory(artist_name, title_name)
        if not item_specific_output_dir:
            return {"status": "error", "message": f"Could not create output directory for {title_name}."}

        # --- Download and save album cover ---
        local_cover_image_path = self.audio_cover_download_service.download_cover_image(
            image_url_from_metadata,
            item_specific_output_dir
        )
        # --- End download and save album cover ---

        # --- Audio download ---
        results_map = {}
        audio_failed = False
        used_spotdl_download = False
        if Config.USE_SPOTDL_PIPELINE and spotdl_client and songs:
            # Drive downloads via SpotDL API (progress published via broker)
            try:
                sanitized_title = self.file_manager.sanitize_filename(title_name)
                output_template = os.path.join(item_specific_output_dir, f"{sanitized_title}")
                spotdl_client.set_output_template(output_template)
                results = spotdl_client.download_songs(songs)
                for song, p in results:
                    results_map[song.url] = str(p) if p else None
                    if p is None:
                        audio_failed = True
                used_spotdl_download = True
            except Exception as e:
                logger.exception("SpotDL API download failed: %s", e)
                audio_failed = True
        else:
            # Legacy CLI path in background thread
            audio_result = {'ok': None}

            def _audio_job():
                audio_result['ok'] = self.audio_cover_download_service.download_audio(
                    spotify_link,
                    item_specific_output_dir,
                    title_name
                )

            audio_thread = threading.Thread(target=_audio_job, name='audio-download', daemon=True)
            audio_thread.start()
            # We'll join later to preserve legacy concurrent lyrics fetching

        # --- Build track DTOs from SpotDL songs (canonical) ---
        track_dtos: List[TrackDTO] = []
        if songs:
            for s in songs:
                dto = song_to_track_dto(s)
                track_dtos.append(dto)
        else:
            # Keep compatibility: if we don't have songs (legacy metadata path), no tracks
            track_dtos = []

        # --- Sliding window lyrics fetching ---
        window = Config.LYRICS_WINDOW_SIZE
        total = len(track_dtos)
        if total:
            for i in range(0, total, window):
                batch = track_dtos[i:i + window]
                logger.info(f"Fetching lyrics for tracks {i + 1}-{i + len(batch)} of {total}")
                for track_dto in batch:
                    track_title = track_dto.title
                    track_artist = track_dto.artists[0] if track_dto.artists else "Unknown Artist"
                    lyrics_path = self.lyrics_service.download_lyrics(
                        track_title,
                        track_artist,
                        item_specific_output_dir
                    )
                    track_dto.local_lyrics_path = lyrics_path
        # --- End sliding window lyrics fetching ---

        # --- Wait/check audio completion ---
        if used_spotdl_download:
            if audio_failed:
                return {"status": "error", "message": f"Audio download failed for {title_name}."}
            # Fill local_path from results_map
            for t in track_dtos:
                t.local_path = results_map.get(t.spotify_url)
        else:
            audio_thread.join()
            if audio_result['ok'] is False:
                return {"status": "error", "message": f"Audio download failed for {title_name}."}

        # Persist track rows (without local audio path for now; phase 6 will fill paths)
        try:
            for t in track_dtos:
                existing = DownloadedTrack.query.filter_by(spotify_id=t.spotify_id).first()
                if existing:
                    # Update a subset likely to change (lyrics path)
                    existing.local_lyrics_path = t.local_lyrics_path
                else:
                    row = DownloadedTrack(
                        spotify_id=t.spotify_id,
                        spotify_url=t.spotify_url,
                        isrc=t.isrc,
                        title=t.title,
                        artists=t.artists,
                        album_name=t.album_name,
                        album_id=t.album_id,
                        album_artist=t.album_artist,
                        track_number=t.track_number,
                        disc_number=t.disc_number,
                        disc_count=t.disc_count,
                        tracks_count=t.tracks_count,
                        duration_ms=t.duration_ms,
                        explicit=t.explicit,
                        popularity=t.popularity,
                        publisher=t.publisher,
                        year=t.year,
                        date=t.date,
                        genres=t.genres,
                        cover_url=t.cover_url,
                        local_path=t.local_path,
                        local_lyrics_path=t.local_lyrics_path,
                    )
                    db.session.add(row)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to persist DownloadedTrack rows: %s", e, exc_info=True)

        # --- Save comprehensive metadata JSON ---
        meta_tracks = [t.model_dump() for t in track_dtos]
        comprehensive_metadata_to_save = {
            'spotify_id': spotify_id,
            'title': title_name,
            'artist': artist_name,
            'image_url': image_url_from_metadata,
            'spotify_url': spotify_url,
            'item_type': item_type,
            'local_output_directory': item_specific_output_dir,
            'local_cover_image_path': local_cover_image_path,
            'tracks': meta_tracks,
        }

        metadata_json_path = self.file_manager.save_metadata_json(
            item_specific_output_dir,
            comprehensive_metadata_to_save
        )
        # --- End save comprehensive metadata JSON ---

        simplified_tracks_info_for_return = []
        if track_dtos:
            for t in track_dtos:
                simplified_tracks_info_for_return.append({
                    'title': t.title,
                    'artists': t.artists,
                    'cover_url': t.cover_url or image_url_from_metadata,
                    'local_lyrics_path': t.local_lyrics_path,
                })

        return {
            "status": "success",
            "message": f"Successfully processed {item_type}: {title_name}",
            "item_name": title_name,
            "item_type": item_type,
            "spotify_id": spotify_id,
            "artist": artist_name,
            "spotify_url": spotify_url,
            "output_directory": item_specific_output_dir,
            "cover_art_url": image_url_from_metadata,
            "local_cover_image_path": local_cover_image_path,
            "tracks": simplified_tracks_info_for_return,
            "metadata_file_path": metadata_json_path
        }
