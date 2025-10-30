import logging
import time
from requests import exceptions as requests_exceptions
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set
import threading

import spotipy  # Spotipy remains for browse/metadata endpoints
from spotipy.oauth2 import SpotifyClientCredentials
from config import Config
from src.utils.cache import TTLCache, MISSING

# Services
from ..catalog.metadata_service import MetadataService
from .download_service import AudioCoverDownloadService
from ..catalog.lyrics_service import LyricsService
from .file_manager import FileManager
from .repository import DownloadRepository, DefaultDownloadRepository

# SpotDL client wrapper and DTO mapping (Phase 2/3)
from src.infrastructure.spotdl import build_default_client, SpotdlClient
from src.models.dto import TrackDTO, ItemDTO
from src.models.spotdl_mapping import song_to_track_dto, songs_to_item_dto

# DB
from src.database.db_manager import db, DownloadedTrack
from src.utils.cancellation import CancellationRequested

from src.support.user_settings import ensure_user_api_keys_applied_for_user_id, user_has_spotify_credentials
from src.core import ProgressPublisher

logger = logging.getLogger(__name__)

class DownloadOrchestrator:
    def __init__(
        self,
        base_output_dir=None,
        spotify_client_id=None,
        spotify_client_secret=None,
        genius_access_token=None,
        spotdl_audio_source=None,
        spotdl_format=None,
        progress_publisher: Optional[ProgressPublisher] = None,
        spotdl_client: Optional[SpotdlClient] = None,
        download_repository: Optional[DownloadRepository] = None,
        metadata_service: Optional[MetadataService] = None,
        audio_service: Optional[AudioCoverDownloadService] = None,
        lyrics_service: Optional[LyricsService] = None,
        file_manager: Optional[FileManager] = None,
    ):
        """Initializes the DownloadOrchestrator with all necessary services."""

        # Configuration values (fallback to Config if not provided)
        self.base_output_dir = base_output_dir if base_output_dir is not None else Config.BASE_OUTPUT_DIR
        self._spotify_client_id = spotify_client_id or Config.SPOTIPY_CLIENT_ID
        self._spotify_client_secret = spotify_client_secret or Config.SPOTIPY_CLIENT_SECRET
        self._genius_access_token = genius_access_token or Config.GENIUS_ACCESS_TOKEN
        self._spotdl_audio_source = spotdl_audio_source or Config.SPOTDL_AUDIO_SOURCE
        self._spotdl_format = spotdl_format or Config.SPOTDL_FORMAT

        # Initialize the sub-services, passing them their respective configuration
        self.metadata_service = metadata_service or MetadataService(
            spotify_client_id=self._spotify_client_id,
            spotify_client_secret=self._spotify_client_secret
        )
        self.audio_cover_download_service = audio_service or AudioCoverDownloadService(
            base_output_dir=self.base_output_dir,
            spotdl_audio_source=(self._spotdl_audio_source or "youtube-music"),
            spotdl_format=(self._spotdl_format or "mp3"),
        )
        self.lyrics_service = lyrics_service or LyricsService(genius_access_token=self._genius_access_token)
        self.file_manager = file_manager or FileManager(base_output_dir=self.base_output_dir)

        # Initialize Spotipy for browse endpoints regardless of download pipeline
        self.sp = None  # Initialize to None
        if self._spotify_client_id and self._spotify_client_secret:
            try:
                self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                    client_id=self._spotify_client_id,
                    client_secret=self._spotify_client_secret
                ))
                logger.info("Spotipy instance initialized within DownloadOrchestrator.")
            except Exception as e:
                logger.error(f"Failed to initialize Spotipy in DownloadOrchestrator: {e}", exc_info=True)
        else:
            logger.warning("Spotify client ID or secret missing. Spotipy instance for direct searches will not be available.")

        # Progress publisher (optional)
        self.progress_publisher: Optional[ProgressPublisher] = progress_publisher

        # SpotDL client can be injected; if None, we create on-demand
        self._spotdl_client: Optional[SpotdlClient] = spotdl_client

        # Repository for persistence (optional); default to SQLAlchemy-based
        self.repo: DownloadRepository = download_repository or DefaultDownloadRepository()

        cache_maxsize = Config.METADATA_CACHE_MAXSIZE
        cache_ttl = Config.METADATA_CACHE_TTL_SECONDS
        self._artist_cache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
        self._artist_discography_cache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
        # Caches popular-artist pool per market; result slicing happens per request
        self._popular_artists_cache = TTLCache(maxsize=4, ttl=Config.POPULAR_ARTIST_CACHE_TTL_SECONDS)
        self._popular_artist_playlist_ids = Config.POPULAR_ARTIST_PLAYLIST_IDS
        self._popular_artist_limit = Config.POPULAR_ARTIST_LIMIT
        self._popular_artist_pool_size = Config.POPULAR_ARTIST_POOL_SIZE

        logger.info("DownloadOrchestrator initialized with decoupled services and configuration passed.")

    def get_spotipy_instance(self):
        """ Provides access to the initialized Spotipy instance. """
        return self.sp

    def _resolve_spotdl_client(self) -> Optional[SpotdlClient]:
        """Return an injected SpotdlClient or build a default one."""
        if self._spotdl_client is not None:
            return self._spotdl_client
        try:
            self._spotdl_client = build_default_client(app_logger=logger)
            return self._spotdl_client
        except Exception as e:
            logger.warning("SpotDL client unavailable; metadata-only features may still work: %s", e)
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

    @staticmethod
    def _chunked_iterable(sequence: Sequence[str], size: int) -> Iterable[Sequence[str]]:
        if size <= 0:
            raise ValueError('size must be positive')
        for index in range(0, len(sequence), size):
            yield sequence[index:index + size]

    @staticmethod
    def _normalize_artist_payload(artist: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        artist_id = artist.get('id')
        if not artist_id:
            return None
        images = artist.get('images') or []
        image_url = None
        if images:
            first_image = images[0]
            image_url = first_image.get('url') if isinstance(first_image, dict) else None
        followers = artist.get('followers') or {}
        raw_followers = followers.get('total')
        raw_popularity = artist.get('popularity')
        followers_available = isinstance(raw_followers, int)
        popularity_available = isinstance(raw_popularity, int)
        norm_followers = int(raw_followers) if isinstance(raw_followers, int) else 0
        norm_popularity = int(raw_popularity) if isinstance(raw_popularity, int) else 0
        return {
            'id': artist_id,
            'name': artist.get('name'),
            'genres': artist.get('genres', []),
            'followers': norm_followers,
            'popularity': norm_popularity,
            'followers_available': followers_available,
            'popularity_available': popularity_available,
            'image': image_url,
            'external_urls': (artist.get('external_urls') or {}).get('spotify'),
        }

    def fetch_artist_details(self, artist_id: str) -> Optional[Dict[str, Any]]:
        cache_entry = self._artist_cache.get(artist_id, MISSING)
        if cache_entry is not MISSING:
            return cache_entry
        if not self.sp:
            logger.error('Spotipy client not initialized. Cannot fetch artist details.')
            return None
        try:
            artist_data = self.sp.artist(artist_id)
            if not artist_data:
                return None
            normalized = self._normalize_artist_payload(artist_data)
            if normalized:
                self._artist_cache.set(artist_id, normalized)
            return normalized
        except Exception as exc:
            logger.error('Error fetching artist details for %s: %s', artist_id, exc, exc_info=True)
            return None

    def fetch_artist_discography(self, artist_id: str, market: str = 'US') -> List[Dict[str, Any]]:
        cache_key = (artist_id, market)
        cached = self._artist_discography_cache.get(cache_key, MISSING)
        if cached is not MISSING:
            return cached
        if not self.sp:
            logger.error('Spotipy client not initialized. Cannot fetch artist discography.')
            return []
        discography: List[Dict[str, Any]] = []
        seen_titles: Set[str] = set()
        attempts = 3
        albums_results: Optional[Dict[str, Any]] = None
        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                albums_results = self.sp.artist_albums(artist_id, album_type='album,single', country=market, limit=50)
                break
            except requests_exceptions.ReadTimeout as exc:
                last_error = exc
                logger.warning('Timed out fetching discography for %s (attempt %s/%s); retrying...', artist_id, attempt, attempts)
                time.sleep(min(0.5 * attempt, 2.0))
            except Exception as exc:
                logger.error('Error fetching artist discography for %s: %s', artist_id, exc, exc_info=True)
                if cached is not MISSING:
                    return cached
                return []
        if albums_results is None:
            if last_error is not None:
                logger.error('Failed to fetch artist discography for %s after %s attempts: %s', artist_id, attempts, last_error)
            if cached is not MISSING:
                return cached
            return []
        if not albums_results:
            self._artist_discography_cache.set(cache_key, discography)
            return discography

        def _ingest(items: Sequence[Dict[str, Any]]) -> None:
            for album_data in items:
                name = album_data.get('name')
                if not name:
                    continue
                album_name_lower = name.lower()
                if album_name_lower in seen_titles:
                    continue
                artists = [a.get('name') for a in album_data.get('artists', []) if a.get('name')]
                images = album_data.get('images') or []
                image_url = images[0].get('url') if images else None
                discography.append({
                    'id': album_data.get('id'),
                    'name': name,
                    'album_type': album_data.get('album_type'),
                    'release_date': album_data.get('release_date'),
                    'total_tracks': album_data.get('total_tracks'),
                    'image_url': image_url,
                    'spotify_url': (album_data.get('external_urls') or {}).get('spotify'),
                    'artist': artists[0] if artists else 'Various Artists',
                    'artists': artists,
                })
                seen_titles.add(album_name_lower)

        try:
            _ingest(albums_results.get('items', []))
            while albums_results.get('next'):
                albums_results = self.sp.next(albums_results)
                _ingest(albums_results.get('items', []))
        except requests_exceptions.ReadTimeout as exc:
            logger.warning('Timed out paging discography for %s: %s', artist_id, exc)
        except Exception as exc:
            logger.error('Error paging artist discography for %s: %s', artist_id, exc, exc_info=True)

        self._artist_discography_cache.set(cache_key, discography)
        return discography



    def fetch_popular_artists(self, limit: Optional[int] = None, market: str = 'US') -> List[Dict[str, Any]]:
        """Return a slice of a large, cached popular-artist pool.

        Builds a diversified pool (~pool_size) from curated playlists and tops up
        with genre searches if needed, caches that pool per market, then slices
        it to the requested limit.
        """
        if not self.sp:
            logger.error('Spotipy client not initialized. Cannot fetch popular artists.')
            return []

        resolved_limit = max(1, int(limit or self._popular_artist_limit))
        pool_key = ('popular_pool', market)
        cached_pool = self._popular_artists_cache.get(pool_key, MISSING)
        if cached_pool is not MISSING:
            return list(cached_pool)[:resolved_limit]

        target_unique = max(1, int(self._popular_artist_pool_size))
        playlist_ids = [pid for pid in self._popular_artist_playlist_ids if pid]

        # 1) Collect unique artist IDs from curated playlists
        collected_ids: List[str] = []
        seen_ids: Set[str] = set()
        if playlist_ids:
            for playlist_id in playlist_ids:
                if len(collected_ids) >= target_unique:
                    break
                playlist_uri = playlist_id
                if not playlist_uri.startswith(('spotify:playlist:', 'https://', 'http://')):
                    playlist_uri = f'spotify:playlist:{playlist_id}'
                try:
                    playlist_items = self.sp.playlist_items(playlist_uri, limit=100, market=market)
                except Exception as exc:
                    logger.warning('Failed to load playlist %s for popular artist discovery: %s', playlist_id, exc)
                    continue
                while playlist_items:
                    items = playlist_items.get('items', [])
                    for entry in items:
                        track = entry.get('track')
                        if not track:
                            continue
                        for artist in track.get('artists', []):
                            artist_id = artist.get('id')
                            if not artist_id or artist_id in seen_ids:
                                continue
                            seen_ids.add(artist_id)
                            collected_ids.append(artist_id)
                            if len(collected_ids) >= target_unique:
                                break
                        if len(collected_ids) >= target_unique:
                            break
                    if len(collected_ids) >= target_unique or not playlist_items.get('next'):
                        break
                    try:
                        playlist_items = self.sp.next(playlist_items)
                    except Exception as exc:
                        logger.warning('Pagination failed for playlist %s: %s', playlist_id, exc)
                        break
        else:
            logger.warning('No playlist sources configured for popular artists.')

        # 2) Batch-fetch artist profiles for the collected IDs
        artist_payloads: List[Dict[str, Any]] = []
        ids_to_fetch: List[str] = []
        for artist_id in collected_ids:
            cached_artist = self._artist_cache.get(artist_id, MISSING)
            if cached_artist is not MISSING:
                if cached_artist:
                    artist_payloads.append(cached_artist)
            else:
                ids_to_fetch.append(artist_id)
        for chunk in self._chunked_iterable(ids_to_fetch, 50):
            try:
                resp = self.sp.artists(list(chunk))
            except Exception as exc:
                logger.warning('Batch artist lookup failed for %s: %s', chunk, exc)
                continue
            for artist in resp.get('artists', []):
                normalized = self._normalize_artist_payload(artist)
                if not normalized:
                    continue
                self._artist_cache.set(normalized['id'], normalized)
                artist_payloads.append(normalized)

        # 3) Top-up via diversified genre searches until pool is filled
        if len(artist_payloads) < target_unique:
            needed = target_unique - len(artist_payloads)
            seen_pool_ids: Set[str] = {a['id'] for a in artist_payloads if a and a.get('id')}
            fallback_genres = [
                'pop', 'rock', 'hip-hop', 'latin', 'r&b',
                'dance', 'electronic', 'indie', 'k-pop', 'metal',
                'country', 'reggaeton', 'soul', 'alternative', 'j-pop'
            ]
            try:
                per_page = 50
                for genre in fallback_genres:
                    if len(artist_payloads) >= target_unique:
                        break
                    # paginate offsets to widen unique pool
                    for offset in range(0, 500, per_page):
                        if len(artist_payloads) >= target_unique:
                            break
                        try:
                            search = self.sp.search(
                                q=f'genre:"{genre}"', type='artist', market=market, limit=per_page, offset=offset
                            )
                        except Exception as exc:
                            logger.warning('Fallback genre search failed for %s (offset %s): %s', genre, offset, exc)
                            break
                        for artist in (search.get('artists') or {}).get('items', []):
                            normalized = self._normalize_artist_payload(artist)
                            if not normalized:
                                continue
                            identifier = normalized.get('id')
                            if not identifier or identifier in seen_pool_ids:
                                continue
                            seen_pool_ids.add(identifier)
                            artist_payloads.append(normalized)
                            if len(artist_payloads) >= target_unique:
                                break
            except Exception as exc:
                logger.warning('Genre top-up failed: %s', exc)

        # 4) Deduplicate, sort, cache pool, slice
        unique_by_id: Dict[str, Dict[str, Any]] = {}
        for artist in artist_payloads:
            if not artist:
                continue
            unique_by_id[artist['id']] = artist

        full_pool = list(unique_by_id.values())
        full_pool.sort(key=lambda data: ((data.get('popularity') or 0), (data.get('followers') or 0)), reverse=True)
        # Trim to pool size for consistency
        full_pool = full_pool[:target_unique]
        self._popular_artists_cache.set(pool_key, full_pool)
        return list(full_pool)[:resolved_limit]

    def get_popular_artist_pool(self, market: str = 'US') -> List[Dict[str, Any]]:
        """Return the full cached popular-artist pool for a market, building it if needed."""
        pool_key = ('popular_pool', market)
        cached_pool = self._popular_artists_cache.get(pool_key, MISSING)
        if cached_pool is not MISSING:
            return list(cached_pool)
        # Build by invoking fetch (which constructs and stores the pool)
        _ = self.fetch_popular_artists(limit=self._popular_artist_pool_size, market=market)
        cached_pool = self._popular_artists_cache.get(pool_key, MISSING)
        if cached_pool is not MISSING:
            return list(cached_pool)
        return []

    def build_best_of_album_details(self, artist_id: str, market: str = 'US') -> Optional[Dict[str, Any]]:
        """
        Build a synthetic "Best Of" album for a given artist by selecting the most
        popular tracks that fit within the configured CD capacity.

        Returns a structure compatible with /api/album_details payloads.
        """
        if not self.sp:
            logger.error('Spotipy client not initialized. Cannot build Best Of album.')
            return None

        # Obtain artist profile for name and image
        artist = self.fetch_artist_details(artist_id)
        if not artist:
            logger.warning('Artist not found for Best Of build: %s', artist_id)
            return None

        try:
            primary_min = int(getattr(Config, 'CD_CAPACITY_MINUTES', 80) or 80)
        except Exception:
            primary_min = 80
        # Leave a safety buffer for Best-Of selection to avoid overfilling discs at burn time.
        # Use 2 minutes less than the configured capacity for selection purposes only.
        effective_min = max(1, primary_min - 2)
        capacity_ms = effective_min * 60 * 1000

        candidates_map: Dict[str, Any] = {}

        # 1) Start with Spotify's top tracks (up to 10)
        try:
            top_resp = self.sp.artist_top_tracks(artist_id, country=market) or {}
            for t in top_resp.get('tracks', []) or []:
                tid = t.get('id')
                if not tid or tid in candidates_map:
                    continue
                candidates_map[tid] = t
        except Exception as exc:
            logger.warning('Failed to fetch artist top tracks for %s: %s', artist_id, exc)

        # 2) Broaden with a search for the artist's tracks (to have popularity values)
        artist_name = artist.get('name') or ''
        if artist_name:
            query = f'artist:"{artist_name}"'
            try:
                search_resp = self.sp.search(q=query, type='track', market=market, limit=50)
                # Iterate through pages up to ~200 candidates
                while True:
                    tracks_page = (search_resp.get('tracks') or {})
                    for t in tracks_page.get('items', []) or []:
                        tid = t.get('id')
                        if tid and tid not in candidates_map:
                            candidates_map[tid] = t
                            if len(candidates_map) >= 200:
                                break
                    if len(candidates_map) >= 200:
                        break
                    next_url = tracks_page.get('next')
                    if not next_url:
                        break
                    try:
                        search_resp = self.sp.next(tracks_page)
                    except Exception as exc:
                        logger.warning('Pagination failed during track search for %s: %s', artist_name, exc)
                        break
            except Exception as exc:
                logger.warning('Search for artist tracks failed for %s: %s', artist_name, exc)

        candidates = list(candidates_map.values())
        if not candidates:
            logger.warning('No candidate tracks available for Best Of build for %s', artist_name or artist_id)
            return None

        # Sort by popularity (desc), then by duration to prefer longer tracks when ties
        candidates.sort(key=lambda t: ((t.get('popularity') or 0), (t.get('duration_ms') or 0)), reverse=True)

        # Accumulate tracks until capacity is reached
        selected: List[Dict[str, Any]] = []
        total_ms = 0
        for t in candidates:
            dur = t.get('duration_ms') or 0
            if dur <= 0:
                continue
            if total_ms + dur > capacity_ms:
                continue
            selected.append(t)
            total_ms += dur
            if total_ms >= capacity_ms * 0.98:
                break

        # Fallback: ensure we have at least some tracks even if capacity logic excludes all
        if not selected:
            selected = candidates[: min(len(candidates), 10)]
            total_ms = sum((t.get('duration_ms') or 0) for t in selected)

        # Normalize into album_details payload shape
        tracks_list: List[Dict[str, Any]] = []
        track_no = 1
        for t in selected:
            artists = [a.get('name') for a in (t.get('artists') or []) if a.get('name')]
            album_obj = t.get('album') or {}
            album_imgs = album_obj.get('images') or []
            album_img_url = album_imgs[0]['url'] if album_imgs else None
            tracks_list.append({
                'spotify_id': t.get('id'),
                'title': t.get('name'),
                'artists': artists,
                'duration_ms': t.get('duration_ms'),
                'track_number': track_no,
                'disc_number': 1,
                'explicit': t.get('explicit'),
                'spotify_url': (t.get('external_urls') or {}).get('spotify'),
                'album_name': album_obj.get('name'),
                'album_spotify_id': album_obj.get('id'),
                'album_image_url': album_img_url,
            })
            track_no += 1

        result = {
            'spotify_id': f'bestof:{artist_id}',
            'title': f'The Best Of {artist.get("name")}',
            'artist': artist.get('name'),
            'image_url': artist.get('image'),
            'spotify_url': None,
            # Report the configured capacity to the UI; selection used a reduced effective capacity.
            'capacity_minutes': primary_min,
            'release_date': None,
            'total_tracks': len(tracks_list),
            'tracks': tracks_list,
        }
        return result

    def _download_best_of_album(self, artist_id: str, *, cancel_event: Optional[threading.Event] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Download pipeline for synthetic Best-Of albums using SpotDL on per-track URLs."""
        # Resolve progress publisher (same behavior as main pipeline)
        publisher = self.progress_publisher
        if publisher is None:
            try:
                from flask import current_app  # type: ignore
                broker = current_app.extensions.get('progress_broker')
                if broker is not None:
                    from src.core import BrokerPublisher
                    publisher = BrokerPublisher(broker)
            except Exception:
                publisher = None

        # Build details and track list
        details = self.build_best_of_album_details(artist_id)
        if not details:
            return {"status": "error", "error_code": "metadata_unavailable", "message": "Could not build Best-Of album for this artist.", "user_id": user_id}

        artist_name = details.get('artist') or 'Unknown Artist'
        title_name = details.get('title') or f'Best Of {artist_name}'
        image_url_from_metadata = details.get('image_url')
        spotify_url = None
        item_type = 'album'
        spotify_id = details.get('spotify_id') or f'bestof:{artist_id}'

        # Prepare output directory and cover art
        item_specific_output_dir = self.file_manager.create_item_output_directory(artist_name, title_name)
        if not item_specific_output_dir:
            return {"status": "error", "message": f"Could not create output directory for {title_name}.", "user_id": user_id}

        local_cover_image_path = self.audio_cover_download_service.download_cover_image(
            image_url_from_metadata,
            item_specific_output_dir
        )

        # Resolve SpotDL client and search per-track Spotify URLs
        spotdl_client = self._resolve_spotdl_client()
        if not spotdl_client:
            return {"status": "error", "error_code": "search_unavailable", "message": "SpotDL client unavailable."}

        track_urls = [t.get('spotify_url') for t in (details.get('tracks') or []) if t.get('spotify_url')]
        if not track_urls:
            return {"status": "error", "error_code": "no_tracks", "message": "No tracks available for Best-Of album."}

        try:
            songs = spotdl_client.search(track_urls)
        except Exception as e:
            return {"status": "error", "error_code": "search_failed", "message": f"SpotDL search failed: {e}"}

        if not songs:
            return {"status": "error", "error_code": "no_results", "message": "SpotDL returned no songs for Best-Of selection."}

        # Inform UI that we are starting a multi-track job
        total_expected = len(songs)
        if publisher is not None:
            try:
                publisher.publish({
                    'song_display_name': title_name,
                    'status': 'Starting download',
                    'progress': 0,
                    'overall_completed': 0,
                    'overall_total': total_expected,
                    'overall_progress': 0,
                })
            except Exception:
                pass

        # Configure output template and download
        results_map: Dict[str, Optional[str]] = {}
        failed_tracks: List[dict] = []
        try:
            sanitized_title = self.file_manager.sanitize_filename(title_name)
            output_template = os.path.join(item_specific_output_dir, f"{sanitized_title}")
            # Per-job progress callback forwards to broker and checks cancellation
            # Adjust SpotDL per-batch counters into job-scope totals
            _acc = {"base": 0, "prev": 0}
            def _progress_cb(ev: dict) -> None:
                try:
                    cc = int(ev.get('overall_completed') or 0)
                except Exception:
                    cc = 0
                # Detect counter reset between chunks
                if cc < _acc["prev"]:
                    _acc["base"] += _acc["prev"]
                _acc["prev"] = cc
                global_completed = min(total_expected, _acc["base"] + cc)
                ev['overall_completed'] = global_completed
                ev['overall_total'] = total_expected
                try:
                    ev['overall_progress'] = int((global_completed / max(1, total_expected)) * 100)
                except Exception:
                    ev['overall_progress'] = 0
                if publisher is not None:
                    try:
                        publisher.publish(ev)
                    except Exception:
                        pass
            spotdl_client.set_output_template(output_template)
            spotdl_client.set_progress_callback(_progress_cb, web_ui=True, cancel_event=cancel_event)
            results = spotdl_client.download_songs(songs, cancel_event=cancel_event)
            audio_failed = False
            error_result = None
            for index, (song, p) in enumerate(results, start=1):
                song_url = getattr(song, 'url', None)
                display_name = getattr(song, 'display_name', None) or getattr(song, 'song_name', None)
                results_map[song_url] = str(p) if p else None
                if p is None:
                    audio_failed = True
                    provider = getattr(song, 'audio_provider', None)
                    if hasattr(provider, 'name'):
                        provider = provider.name
                    detail = getattr(song, 'error_message', None)
                    if isinstance(detail, Exception):
                        detail = str(detail)
                    if not detail:
                        detail = getattr(song, 'log', None)
                    if isinstance(detail, dict):
                        detail = detail.get('message') or detail.get('error')
                    if not detail:
                        detail = 'Audio provider did not return a media file.'
                    failed_entry = {
                        'index': index,
                        'title': display_name or song_url or f'Track {index}',
                        'spotify_url': song_url,
                        'audio_provider': provider,
                        'error_message': detail,
                    }
                    failed_tracks.append(failed_entry)
                    logger.error(
                        'Audio download failed for %s (provider=%s, url=%s): %s',
                        failed_entry['title'],
                        provider,
                        song_url,
                        detail,
                    )
            if audio_failed:
                error_result = {
                    'status': 'error',
                    'error_code': 'download_failed',
                    'message': f'Audio download failed for {title_name}.',
                }
                if failed_tracks:
                    error_result['failed_tracks'] = failed_tracks
                return error_result
        except Exception as e:
            try:
                from spotdl.download.downloader import DownloaderError  # type: ignore
                from spotdl.providers.audio.base import AudioProviderError  # type: ignore
            except Exception:
                DownloaderError = Exception  # type: ignore
                AudioProviderError = Exception  # type: ignore
            # Cooperative cancellation
            try:
                if isinstance(e, CancellationRequested):
                    # Cleanup partials and remove the album folder
                    try:
                        self.file_manager.cleanup_partial_output(item_specific_output_dir)
                    except Exception:
                        pass
                    try:
                        import shutil
                        shutil.rmtree(item_specific_output_dir, ignore_errors=True)
                    except Exception:
                        pass
                    return {"status": "error", "error_code": "cancelled", "message": "Download cancelled by user."}
            except Exception:
                pass
            if isinstance(e, AudioProviderError):
                return {"status": "error", "error_code": "provider_error", "message": str(e)}
            if isinstance(e, DownloaderError):
                return {"status": "error", "error_code": "downloader_error", "message": str(e)}
            return {"status": "error", "error_code": "internal_error", "message": f"SpotDL API download failed: {e}"}

        # Build TrackDTOs and override numbering to reflect Best-Of ordering
        track_dtos: List[TrackDTO] = []
        for index, s in enumerate(songs, start=1):
            dto = song_to_track_dto(s)
            dto.local_path = results_map.get(getattr(s, 'url', None))
            # Force disc/track numbers sequentially so the generated album looks like a real album
            dto.disc_number = 1
            dto.track_number = index
            track_dtos.append(dto)

        # Lyrics export phase
        if True:
            total_tracks = len(track_dtos)
            exported_count = 0
            for t in track_dtos:
                if t.local_path and not t.local_lyrics_path:
                    exported = self.lyrics_service.ensure_lyrics(
                        t.local_path,
                        title=t.title,
                        artists=t.artists,
                    )
                    t.local_lyrics_path = exported
                exported_count += 1
                if publisher is not None:
                    try:
                        publisher.publish({
                            'song_display_name': t.title,
                            'status': f'Exporting lyrics ({exported_count}/{total_tracks})',
                            'progress': 100 if t.local_lyrics_path else 0,
                            'overall_completed': exported_count,
                            'overall_total': total_tracks,
                            'overall_progress': int((exported_count / max(1, total_tracks)) * 100),
                        })
                    except Exception:
                        pass
            if publisher is not None:
                try:
                    publisher.publish({
                        'song_display_name': title_name,
                        'status': 'Complete',
                        'progress': 100,
                        'overall_completed': total_tracks,
                        'overall_total': total_tracks,
                        'overall_progress': 100,
                    })
                except Exception:
                    pass

        # Persist track rows
        try:
            self.repo.save_tracks(track_dtos, user_id=user_id)
        except Exception:
            pass

        # Save metadata JSON
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

        simplified_tracks_info_for_return = []
        for t in track_dtos:
            simplified_tracks_info_for_return.append({
                'title': t.title,
                'artists': t.artists,
                'cover_url': t.cover_url or image_url_from_metadata,
                'local_lyrics_path': t.local_lyrics_path,
            })

        completion_message = f"Successfully processed {item_type}: {title_name}"
        if failed_tracks:
            failure_suffix = f" (with {len(failed_tracks)} error{'s' if len(failed_tracks) != 1 else ''})"
            completion_message = completion_message + failure_suffix
            logger.warning(
                "Completed %s with %d failed tracks.",
                title_name,
                len(failed_tracks),
            )

        response_payload = {
            "status": "success",
            "message": completion_message,
            "item_name": title_name,
            "item_type": item_type,
            "spotify_id": spotify_id,
            "artist": artist_name,
            "spotify_url": spotify_url,
            "output_directory": item_specific_output_dir,
            "cover_art_url": image_url_from_metadata,
            "local_cover_image_path": local_cover_image_path,
            "tracks": simplified_tracks_info_for_return,
            "metadata_file_path": metadata_json_path,
            "user_id": user_id,
        }
        if failed_tracks:
            response_payload["failed_tracks"] = failed_tracks
            response_payload["partial_success"] = True

        return response_payload


    def download_compilation(self, tracks: List[Dict[str, Any]], name: str, cover_data_url: Optional[str] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Download an ad-hoc compilation of tracks into a dedicated folder.

        Args:
            tracks: list of dicts with keys like {spotify_id|id|url|uri,title,artists,duration_ms}
            name: compilation name provided by user

        Returns: orchestrator-style result dict with item_type='compilation'.
        """
        publisher = self.progress_publisher
        spotdl_client = self._resolve_spotdl_client()
        if not spotdl_client:
            return {"status": "error", "error_code": "spotdl_unavailable", "message": "SpotDL client unavailable."}

        # Resolve queries from provided tracks (prefer explicit links; else spotify:track:{id})
        queries: List[str] = []
        for t in tracks or []:
            url = t.get('url') or t.get('spotify_url') or t.get('uri')
            sid = t.get('spotify_id') or t.get('id')
            if url:
                queries.append(str(url))
            elif sid:
                queries.append(f"spotify:track:{sid}")
        if not queries:
            return {"status": "error", "message": "No valid tracks provided."}

        # Build output directory: BASE_OUTPUT_DIR/Compilations/<name-YYYYMMDD-HHMM>
        from datetime import datetime
        safe_name = self.file_manager.sanitize_filename(name or 'My Compilation')
        suffix = datetime.now().strftime('%Y%m%d-%H%M')
        comp_dir = os.path.join(self.base_output_dir, 'Compilations', f"{safe_name}-{suffix}")
        try:
            os.makedirs(comp_dir, exist_ok=True)
        except Exception as e:
            return {"status": "error", "message": f"Failed to create compilation directory: {e}"}

        
        # Determine existing or provided cover path (if any)
        local_cover_image_path = None
        try:
            jpg = os.path.join(comp_dir, 'cover.jpg')
            png = os.path.join(comp_dir, 'cover.png')
            svg = os.path.join(comp_dir, 'cover.svg')
            if os.path.exists(jpg):
                local_cover_image_path = jpg
            elif os.path.exists(png):
                local_cover_image_path = png
            elif os.path.exists(svg):
                local_cover_image_path = svg
            elif isinstance(cover_data_url, str) and cover_data_url and cover_data_url.startswith('data:image/') and ';base64,' in cover_data_url:
                # Save provided data URL (fallback path if route didn't pre-save)
                head, b64 = cover_data_url.split(',', 1)
                ext = 'jpg'
                if 'image/png' in head:
                    ext = 'png'
                elif 'image/jpeg' in head or 'image/jpg' in head:
                    ext = 'jpg'
                target = os.path.join(comp_dir, f'cover.{ext}')
                import base64 as _b64
                try:
                    raw = _b64.b64decode(b64)
                    with open(target, 'wb') as f:
                        f.write(raw)
                    local_cover_image_path = target
                except Exception:
                    local_cover_image_path = None
        except Exception:
            local_cover_image_path = None
        # Search and download songs
        try:
            songs = spotdl_client.search(queries)
        except Exception as e:
            logger.exception("SpotDL search failed for compilation: %s", e)
            return {"status": "error", "error_code": "search_failed", "message": str(e)}

        if not songs:
            return {"status": "error", "message": "No songs resolved for provided tracks."}

        if publisher is not None:
            try:
                publisher.publish({
                    'song_display_name': name,
                    'status': 'Starting compilation download',
                    'progress': 0,
                    'overall_completed': 0,
                    'overall_total': len(songs),
                    'overall_progress': 0,
                    'topic': f'compilation:{safe_name}',
                })
            except Exception:
                pass

        # Ensure files are saved under compilation directory; keep SpotDL default naming under that folder
        try:
            output_template = os.path.join(comp_dir, '{artist} - {title}')
            spotdl_client.set_output_template(output_template)
            results = spotdl_client.download_songs(songs)
        except Exception as e:
            logger.exception("SpotDL download failed for compilation: %s", e)
            return {"status": "error", "error_code": "download_failed", "message": str(e)}

        # Map results and export lyrics
        results_map: Dict[str, Optional[str]] = {}
        audio_failed = False
        for song, path in results:
            results_map[getattr(song, 'url', None)] = str(path) if path else None
            if path is None:
                audio_failed = True

        # Build DTOs to persist lyric paths (optional)
        track_dtos: List[TrackDTO] = []
        for s in songs:
            dto = song_to_track_dto(s)
            dto.local_path = results_map.get(dto.spotify_url)
            track_dtos.append(dto)

        # Export embedded lyrics where possible, publish light progress
        total_tracks = len(track_dtos)
        exported_count = 0
        for t in track_dtos:
            if t.local_path and not t.local_lyrics_path:
                exported = self.lyrics_service.ensure_lyrics(
                    t.local_path,
                    title=t.title,
                    artists=t.artists,
                )
                t.local_lyrics_path = exported
            exported_count += 1
            if publisher is not None:
                try:
                    publisher.publish({
                        'song_display_name': t.title,
                        'status': f'Exporting lyrics ({exported_count}/{total_tracks})',
                        'progress': 100 if t.local_lyrics_path else 0,
                        'overall_completed': exported_count,
                        'overall_total': total_tracks,
                        'overall_progress': int((exported_count / max(1, total_tracks)) * 100),
                        'topic': f'compilation:{safe_name}',
                    })
                except Exception:
                    pass

        try:
            self.repo.save_tracks(track_dtos, user_id=user_id)
        except Exception:
            pass

        # Write a simple manifest.json and a compatibility spotify_metadata.json
        try:
            import json as _json
            manifest = {
                'name': name,
                'created_at': suffix,
                'total_tracks': len(tracks or []),
                'tracks': [
                    {
                        'spotify_id': (t.get('spotify_id') or t.get('id')),
                        'title': t.get('title'),
                        'artists': t.get('artists'),
                        'duration_ms': t.get('duration_ms'),
                    } for t in (tracks or [])
                ],
            }
            with open(os.path.join(comp_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
                _json.dump(manifest, f, ensure_ascii=False, indent=2)
            # Compatibility file so UI can read metadata panel
            compat = {
                'spotify_id': f'comp-{suffix}-{safe_name}',
                'title': name,
                'artist': 'Various Artists',
                'image_url': None,
                'spotify_url': None,
                'item_type': 'compilation',
                'local_output_directory': comp_dir,
                'local_cover_image_path': local_cover_image_path,
                'tracks': [t.model_dump() for t in track_dtos],
            }
            with open(os.path.join(comp_dir, 'spotify_metadata.json'), 'w', encoding='utf-8') as f:
                _json.dump(compat, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # Final completion event
        if publisher is not None:
            try:
                publisher.publish({
                    'song_display_name': name,
                    'status': 'Complete',
                    'progress': 100,
                    'overall_completed': total_tracks,
                    'overall_total': total_tracks,
                    'overall_progress': 100,
                    'topic': f'compilation:{safe_name}',
                })
            except Exception:
                pass

        # Return synthetic item record
        return {
            'status': 'success',
            'message': f'Successfully downloaded compilation: {name}',
            'item_name': name,
            'item_type': 'compilation',
            'spotify_id': f'comp-{suffix}-{safe_name}',
            'artist': 'Various Artists',
            'spotify_url': None,
            'output_directory': comp_dir,
            'cover_art_url': None,
            'local_cover_image_path': local_cover_image_path,
            'tracks': [
                {
                    'title': t.title,
                    'artists': t.artists,
                    'cover_url': t.cover_url,
                    'local_lyrics_path': t.local_lyrics_path,
                } for t in track_dtos
            ],
            'metadata_file_path': os.path.join(comp_dir, 'spotify_metadata.json'),
            'user_id': user_id,
        }

    def download_spotify_content(self, spotify_link, *, cancel_event: Optional[threading.Event] = None, user_id: Optional[int] = None):
        """Orchestrates the download using SpotDL Song as canonical metadata source."""
        if user_id is not None:
            keys = ensure_user_api_keys_applied_for_user_id(user_id, refresh_client=False)
            if not user_has_spotify_credentials(keys):
                return {
                    "status": "error",
                    "error_code": "credentials_missing",
                    "message": "Spotify credentials are not configured. Please add them in Settings.",
                    "user_id": user_id,
                }
        # Synthetic Best-Of album support: treat 'bestof:<artist_id>' like a container
        if isinstance(spotify_link, str) and spotify_link.startswith('bestof:'):
            artist_id = spotify_link.split(':', 1)[1]
            return self._download_best_of_album(artist_id, cancel_event=cancel_event, user_id=user_id)
        # Progress publisher for SSE/clients (compat: fall back to broker in app context)
        publisher = self.progress_publisher
        if publisher is None:
            try:
                from flask import current_app  # type: ignore
                broker = current_app.extensions.get('progress_broker')
                if broker is not None:
                    from src.core import BrokerPublisher
                    publisher = BrokerPublisher(broker)
            except Exception:
                publisher = None
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

        # Fallback to metadata if SpotDL search unavailable
        if item_dto is None:
            initial_metadata = self.metadata_service.get_metadata_from_link(spotify_link)
            if not initial_metadata:
                return {"status": "error", "message": "Could not retrieve metadata for the given Spotify link.", "user_id": user_id}
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
        error_result = None
        failed_tracks: List[dict] = []
        failed_urls: Set[str] = set()
        if spotdl_client and songs:
            # Drive downloads via SpotDL API (progress published via broker)
            try:
                # Inform UI that we are starting a multi-track job
                total_expected = len(songs)
                if publisher is not None:
                    try:
                        publisher.publish({
                            'song_display_name': title_name,
                            'status': 'Starting download',
                            'progress': 0,
                            'overall_completed': 0,
                            'overall_total': total_expected,
                            'overall_progress': 0,
                        })
                    except Exception:
                        pass
                sanitized_title = self.file_manager.sanitize_filename(title_name)
                output_template = os.path.join(item_specific_output_dir, f"{sanitized_title}")
                # Install a per-job callback that republishes and normalizes totals
                _acc = {"base": 0, "prev": 0}
                def _progress_cb(ev: dict) -> None:
                    try:
                        cc = int(ev.get('overall_completed') or 0)
                    except Exception:
                        cc = 0
                    if cc < _acc["prev"]:
                        _acc["base"] += _acc["prev"]
                    _acc["prev"] = cc
                    global_completed = min(total_expected, _acc["base"] + cc)
                    ev['overall_completed'] = global_completed
                    ev['overall_total'] = total_expected
                    try:
                        ev['overall_progress'] = int((global_completed / max(1, total_expected)) * 100)
                    except Exception:
                        ev['overall_progress'] = 0
                    if publisher is not None:
                        try:
                            publisher.publish(ev)
                        except Exception:
                            pass
                spotdl_client.set_output_template(output_template)
                spotdl_client.set_progress_callback(_progress_cb, web_ui=True, cancel_event=cancel_event)
                results = spotdl_client.download_songs(songs, cancel_event=cancel_event)
                successful_downloads = 0
                partial_failures = False
                for index, (song, p) in enumerate(results, start=1):
                    song_url = getattr(song, "url", None)
                    display_name = getattr(song, "display_name", None) or getattr(song, "song_name", None)
                    results_map[song_url] = str(p) if p else None
                    if p:
                        successful_downloads += 1
                        continue

                    partial_failures = True
                    provider = getattr(song, "audio_provider", None)
                    detail = getattr(song, "download_error", None) or getattr(song, "error_message", None)
                    if isinstance(detail, Exception):
                        detail = str(detail)
                    if not detail:
                        detail = getattr(song, "log", None)
                    if isinstance(detail, dict):
                        detail = detail.get("message") or detail.get("error")
                    if not detail:
                        detail = "Audio provider did not return a media file."
                    failed_entry = {
                        "index": index,
                        "title": display_name or song_url or f"Track {index}",
                        "spotify_url": song_url,
                        "audio_provider": provider,
                        "error_message": detail,
                    }
                    failed_tracks.append(failed_entry)
                    if song_url:
                        failed_urls.add(song_url)
                    logger.error(
                        "Audio download failed for %s (provider=%s, url=%s): %s",
                        failed_entry["title"],
                        provider,
                        song_url,
                        detail,
                    )
                    if publisher is not None:
                        try:
                            publisher.publish({
                                'event': 'download_progress',
                                'song_display_name': failed_entry["title"],
                                'spotify_url': song_url,
                                'status': f"Error: {detail}",
                                'progress': 0,
                                'overall_completed': successful_downloads,
                                'overall_total': total_expected,
                                'overall_progress': int((successful_downloads / max(1, total_expected)) * 100),
                                'error_message': detail,
                                'audio_provider': provider,
                                'severity': 'error',
                            })
                        except Exception:
                            pass
                if successful_downloads == 0 and failed_tracks:
                    audio_failed = True
                    if error_result is None:
                        error_result = {"status": "error", "error_code": "download_failed", "message": f"Audio download failed for {title_name}."}
                elif partial_failures and publisher is not None:
                    try:
                        publisher.publish({
                            'event': 'download_error_summary',
                            'song_display_name': title_name,
                            'status': f'Completed with {len(failed_tracks)} failed track(s).',
                            'progress': 100 if successful_downloads else 0,
                            'overall_completed': successful_downloads,
                            'overall_total': total_expected,
                            'overall_progress': int((successful_downloads / max(1, total_expected)) * 100),
                            'error_message': 'Some tracks failed to download.',
                            'failed_tracks': failed_tracks,
                            'severity': 'warning',
                        })
                    except Exception:
                        pass
            except Exception as e:
                # Map specific SpotDL errors when possible
                try:
                    from spotdl.download.downloader import DownloaderError  # type: ignore
                    from spotdl.providers.audio.base import AudioProviderError  # type: ignore
                except Exception:
                    DownloaderError = Exception  # type: ignore
                    AudioProviderError = Exception  # type: ignore
                # Cooperative cancellation
                try:
                    if isinstance(e, CancellationRequested):
                        try:
                            self.file_manager.cleanup_partial_output(item_specific_output_dir)
                        except Exception:
                            pass
                        try:
                            import shutil
                            shutil.rmtree(item_specific_output_dir, ignore_errors=True)
                        except Exception:
                            pass
                        return {"status": "error", "error_code": "cancelled", "message": "Download cancelled by user."}
                except Exception:
                    pass
                detail = str(e).strip() or repr(e)
                provider_name = getattr(e, "provider", None) or e.__class__.__name__
                error_url = None
                try:
                    match = re.search(r"https?://\S+", detail or "")
                    if match:
                        error_url = match.group(0).rstrip(").,;")
                except Exception:
                    error_url = None

                matched_song = None
                if songs:
                    if error_url:
                        for idx, candidate in enumerate(songs, start=1):
                            if getattr(candidate, "url", None) == error_url:
                                matched_song = (idx, candidate)
                                break
                    if matched_song is None:
                        for idx, candidate in enumerate(songs, start=1):
                            cand_url = getattr(candidate, "url", None)
                            if cand_url not in failed_urls:
                                matched_song = (idx, candidate)
                                break

                failed_entry = None
                if matched_song is not None:
                    idx, candidate = matched_song
                    entry_title = (
                        getattr(candidate, "display_name", None)
                        or getattr(candidate, "song_name", None)
                        or getattr(candidate, "name", None)
                        or f"Track {idx}"
                    )
                    candidate_url = getattr(candidate, "url", None)
                    failed_entry = {
                        "index": idx,
                        "title": entry_title,
                        "spotify_url": error_url or candidate_url,
                        "audio_provider": provider_name,
                        "error_message": detail,
                    }
                elif songs:
                    entry_title = getattr(songs[0], "display_name", None) or getattr(songs[0], "song_name", None) or title_name
                    candidate_url = getattr(songs[0], "url", None)
                    failed_entry = {
                        "index": 1,
                        "title": entry_title,
                        "spotify_url": error_url or candidate_url,
                        "audio_provider": provider_name,
                        "error_message": detail,
                    }
                elif error_url:
                    failed_entry = {
                        "index": 1,
                        "title": title_name,
                        "spotify_url": error_url,
                        "audio_provider": provider_name,
                        "error_message": detail,
                    }

                if failed_entry:
                    failed_tracks.append(failed_entry)
                    url_value = failed_entry.get("spotify_url")
                    if url_value:
                        failed_urls.add(url_value)
                    logger.error(
                        "Audio provider error while downloading %s: %s (provider=%s, url=%s)",
                        failed_entry["title"],
                        detail,
                        provider_name,
                        failed_entry.get("spotify_url"),
                    )
                    if publisher is not None:
                        try:
                            publisher.publish({
                                "event": "download_progress",
                                "song_display_name": failed_entry["title"],
                                "spotify_url": failed_entry.get("spotify_url"),
                                "status": "Error: {}".format(detail),
                                "progress": 0,
                                "overall_completed": max(0, len(songs or []) - len(failed_tracks)),
                                "overall_total": total_expected if songs else 0,
                                "overall_progress": 0,
                                "error_message": detail,
                                "audio_provider": provider_name,
                                "severity": "error",
                            })
                        except Exception:
                            pass
                logger.exception("SpotDL API download failed: %s", e)
                if isinstance(e, AudioProviderError):
                    error_result = {"status": "error", "error_code": "provider_error", "message": detail}
                elif isinstance(e, DownloaderError):
                    error_result = {"status": "error", "error_code": "downloader_error", "message": detail}
                else:
                    error_result = {"status": "error", "error_code": "internal_error", "message": f"SpotDL API download failed: {detail}"}
                audio_failed = True
        if not songs:
            return {"status": "error", "error_code": "search_unavailable", "message": "SpotDL search did not return results or client unavailable."}
        if audio_failed and failed_tracks and error_result and "failed_tracks" not in error_result:
            error_result = {**error_result, "failed_tracks": failed_tracks}

        # --- Build track DTOs from SpotDL songs (canonical) ---
        track_dtos: List[TrackDTO] = []
        if songs:
            for s in songs:
                dto = song_to_track_dto(s)
                track_dtos.append(dto)
        else:
            # Keep compatibility: if we don't have songs (legacy metadata path), no tracks
            track_dtos = []

        # Always map known audio paths so downstream processing has access,
        # even if the download experienced partial failures.
        for t in track_dtos:
            t.local_path = results_map.get(t.spotify_url)

        # For SpotDL pipeline: export embedded lyrics alongside audio files (graceful if missing)
        total_tracks = len(track_dtos)
        if total_tracks:
            exported_count = 0
            for t in track_dtos:
                if t.local_path and not t.local_lyrics_path:
                    exported = self.lyrics_service.ensure_lyrics(
                        t.local_path,
                        title=t.title,
                        artists=t.artists,
                    )
                    t.local_lyrics_path = exported
                exported_count += 1
                # Progress update for lyrics export phase
                if publisher is not None:
                    try:
                        publisher.publish({
                            'song_display_name': t.title,
                            'status': f'Exporting lyrics ({exported_count}/{total_tracks})',
                            'progress': 100 if t.local_lyrics_path else 0,
                            'overall_completed': exported_count,
                            'overall_total': total_tracks,
                            'overall_progress': int((exported_count / max(1, total_tracks)) * 100),
                            'event': 'lyrics_export',
                            'lyrics_exported': bool(t.local_lyrics_path),
                            'lyrics_path': t.local_lyrics_path,
                        })
                    except Exception:
                        pass
            # Final completion event after lyrics export and persistence
            if publisher is not None and not audio_failed:
                try:
                    publisher.publish({
                        'song_display_name': title_name,
                        'status': 'Complete',
                        'progress': 100,
                        'overall_completed': total_tracks,
                        'overall_total': total_tracks,
                        'overall_progress': 100,
                    })
                except Exception:
                    pass

        # --- Wait/check audio completion ---
        if audio_failed:
            failure_payload = error_result or {
                "status": "error",
                "error_code": "download_failed",
                "message": f"Audio download failed for {title_name}.",
                "failed_tracks": failed_tracks,
            }
            if "failed_tracks" not in failure_payload:
                failure_payload = {**failure_payload, "failed_tracks": failed_tracks}
            if user_id is not None and "user_id" not in failure_payload:
                failure_payload = {**failure_payload, "user_id": user_id}
            if publisher is not None:
                try:
                    publisher.publish({
                        'event': 'download_error_summary',
                        'song_display_name': title_name,
                        'status': failure_payload.get("message"),
                        'progress': 0,
                        'overall_completed': max(0, len(songs or []) - len(failed_tracks)),
                        'overall_total': len(songs or []),
                        'overall_progress': 0,
                        'error_message': failure_payload.get("message"),
                        'failed_tracks': failure_payload.get("failed_tracks"),
                        'severity': 'error',
                    })
                except Exception:
                    pass
            return failure_payload

        # Persist track rows (now including local audio path and lyrics path)
        try:
            self.repo.save_tracks(track_dtos, user_id=user_id)
        except Exception:
            # Repository implementations log their own errors
            pass

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

        completion_message = f"Successfully processed {item_type}: {title_name}"
        if failed_tracks:
            failure_suffix = f" (with {len(failed_tracks)} error{'s' if len(failed_tracks) != 1 else ''})"
            completion_message = completion_message + failure_suffix
            logger.warning(
                "Completed %s with %d failed tracks.",
                title_name,
                len(failed_tracks),
            )

        response_payload = {
            "status": "success",
            "message": completion_message,
            "item_name": title_name,
            "item_type": item_type,
            "spotify_id": spotify_id,
            "artist": artist_name,
            "spotify_url": spotify_url,
            "output_directory": item_specific_output_dir,
            "cover_art_url": image_url_from_metadata,
            "local_cover_image_path": local_cover_image_path,
            "tracks": simplified_tracks_info_for_return,
            "metadata_file_path": metadata_json_path,
            "user_id": user_id,
        }
        if failed_tracks:
            response_payload["failed_tracks"] = failed_tracks
            response_payload["partial_success"] = True

        return response_payload


