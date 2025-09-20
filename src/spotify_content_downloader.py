import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import spotipy  # Spotipy remains for browse/metadata endpoints
from spotipy.oauth2 import SpotifyClientCredentials
from config import Config
from .utils.cache import TTLCache, MISSING

# Services
from .metadata_service import MetadataService
from .download_service import AudioCoverDownloadService
from .lyrics_service import LyricsService
from .file_manager import FileManager
from .repository import DownloadRepository, DefaultDownloadRepository

# SpotDL client wrapper and DTO mapping (Phase 2/3)
from .spotdl_client import build_default_client, SpotdlClient
from .models.dto import TrackDTO, ItemDTO
from .models.spotdl_mapping import song_to_track_dto, songs_to_item_dto

# DB
from .database.db_manager import db, DownloadedTrack

from .progress import ProgressPublisher

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
        progress_publisher: Optional[ProgressPublisher] = None,
        spotdl_client: Optional[SpotdlClient] = None,
        download_repository: Optional[DownloadRepository] = None,
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

        # Initialize Spotipy for browse endpoints regardless of download pipeline
        self.sp = None  # Initialize to None
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
        self._popular_artists_cache = TTLCache(maxsize=4, ttl=Config.POPULAR_ARTIST_CACHE_TTL_SECONDS)
        self._popular_artist_playlist_ids = Config.POPULAR_ARTIST_PLAYLIST_IDS
        self._popular_artist_limit = Config.POPULAR_ARTIST_LIMIT

        logger.info("SpotifyContentDownloader initialized with decoupled services and configuration passed.")

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
        return {
            'id': artist_id,
            'name': artist.get('name'),
            'genres': artist.get('genres', []),
            'followers': followers.get('total'),
            'popularity': artist.get('popularity'),
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
        try:
            albums_results = self.sp.artist_albums(artist_id, album_type='album,single', country=market, limit=50)
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

            _ingest(albums_results.get('items', []))
            while albums_results.get('next'):
                albums_results = self.sp.next(albums_results)
                _ingest(albums_results.get('items', []))
        except Exception as exc:
            logger.error('Error fetching artist discography for %s: %s', artist_id, exc, exc_info=True)
            return []
        self._artist_discography_cache.set(cache_key, discography)
        return discography



    def fetch_popular_artists(self, limit: Optional[int] = None, market: str = 'US') -> List[Dict[str, Any]]:
        if not self.sp:
            logger.error('Spotipy client not initialized. Cannot fetch popular artists.')
            return []
        resolved_limit = limit or self._popular_artist_limit
        cache_key = (resolved_limit, market)
        cached = self._popular_artists_cache.get(cache_key, MISSING)
        if cached is not MISSING:
            return cached

        playlist_ids = [pid for pid in self._popular_artist_playlist_ids if pid]
        artist_payloads: List[Dict[str, Any]] = []

        if playlist_ids:
            target_unique = max(resolved_limit * 2, resolved_limit)
            collected: List[str] = []
            seen_ids: Set[str] = set()

            for playlist_id in playlist_ids:
                if len(collected) >= target_unique:
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
                            collected.append(artist_id)
                            if len(collected) >= target_unique:
                                break
                        if len(collected) >= target_unique:
                            break
                    if len(collected) >= target_unique or not playlist_items.get('next'):
                        break
                    try:
                        playlist_items = self.sp.next(playlist_items)
                    except Exception as exc:
                        logger.warning('Pagination failed for playlist %s: %s', playlist_id, exc)
                        break

            ids_to_fetch: List[str] = []
            for artist_id in collected:
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
        else:
            logger.warning('No playlist sources configured for popular artists.')

        if not artist_payloads:
            fallback_artists: List[Dict[str, Any]] = []
            seen_fallback: Set[str] = set()
            fallback_genres = ['pop', 'rock', 'hip-hop', 'latin', 'r&b']
            for genre in fallback_genres:
                try:
                    search = self.sp.search(q=f'genre:"{genre}"', type='artist', market=market, limit=resolved_limit)
                except Exception as exc:
                    logger.warning('Fallback genre search failed for %s: %s', genre, exc)
                    continue
                for artist in search.get('artists', {}).get('items', []):
                    normalized = self._normalize_artist_payload(artist)
                    if not normalized:
                        continue
                    identifier = normalized['id']
                    if identifier in seen_fallback:
                        continue
                    seen_fallback.add(identifier)
                    fallback_artists.append(normalized)
                    if len(fallback_artists) >= resolved_limit:
                        break
                if len(fallback_artists) >= resolved_limit:
                    break
            artist_payloads = fallback_artists

        unique_by_id: Dict[str, Dict[str, Any]] = {}
        for artist in artist_payloads:
            if not artist:
                continue
            unique_by_id[artist['id']] = artist

        final_list = list(unique_by_id.values())
        final_list.sort(key=lambda data: ((data.get('popularity') or 0), (data.get('followers') or 0)), reverse=True)
        result = final_list[:resolved_limit]
        self._popular_artists_cache.set(cache_key, result)
        return result

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

    def _download_best_of_album(self, artist_id: str) -> Dict[str, Any]:
        """Download pipeline for synthetic Best-Of albums using SpotDL on per-track URLs."""
        # Resolve progress publisher (same behavior as main pipeline)
        publisher = self.progress_publisher
        if publisher is None:
            try:
                from flask import current_app  # type: ignore
                broker = current_app.extensions.get('progress_broker')
                if broker is not None:
                    from .progress import BrokerPublisher
                    publisher = BrokerPublisher(broker)
            except Exception:
                publisher = None

        # Build details and track list
        details = self.build_best_of_album_details(artist_id)
        if not details:
            return {"status": "error", "error_code": "metadata_unavailable", "message": "Could not build Best-Of album for this artist."}

        artist_name = details.get('artist') or 'Unknown Artist'
        title_name = details.get('title') or f'Best Of {artist_name}'
        image_url_from_metadata = details.get('image_url')
        spotify_url = None
        item_type = 'album'
        spotify_id = details.get('spotify_id') or f'bestof:{artist_id}'

        # Prepare output directory and cover art
        item_specific_output_dir = self.file_manager.create_item_output_directory(artist_name, title_name)
        if not item_specific_output_dir:
            return {"status": "error", "message": f"Could not create output directory for {title_name}."}

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
        if publisher is not None:
            try:
                publisher.publish({
                    'song_display_name': title_name,
                    'status': 'Starting download',
                    'progress': 0,
                    'overall_completed': 0,
                    'overall_total': len(songs),
                    'overall_progress': 0,
                })
            except Exception:
                pass

        # Configure output template and download
        results_map: Dict[str, Optional[str]] = {}
        try:
            sanitized_title = self.file_manager.sanitize_filename(title_name)
            output_template = os.path.join(item_specific_output_dir, f"{sanitized_title}")
            spotdl_client.set_output_template(output_template)
            results = spotdl_client.download_songs(songs)
            audio_failed = False
            error_result = None
            for song, p in results:
                results_map[getattr(song, 'url', None)] = str(p) if p else None
                if p is None:
                    audio_failed = True
            if audio_failed:
                error_result = {"status": "error", "error_code": "download_failed", "message": f"Audio download failed for {title_name}."}
                return error_result
        except Exception as e:
            try:
                from spotdl.download.downloader import DownloaderError  # type: ignore
                from spotdl.providers.audio.base import AudioProviderError  # type: ignore
            except Exception:
                DownloaderError = Exception  # type: ignore
                AudioProviderError = Exception  # type: ignore
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
                    try:
                        exported = self.lyrics_service.export_embedded_lyrics(t.local_path)
                    except Exception:
                        exported = None
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
            self.repo.save_tracks(track_dtos)
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


    def download_spotify_content(self, spotify_link):
        """Orchestrates the download using SpotDL Song as canonical metadata source."""
        # Synthetic Best-Of album support: treat 'bestof:<artist_id>' like a container
        if isinstance(spotify_link, str) and spotify_link.startswith('bestof:'):
            artist_id = spotify_link.split(':', 1)[1]
            return self._download_best_of_album(artist_id)
        # Progress publisher for SSE/clients (compat: fall back to broker in app context)
        publisher = self.progress_publisher
        if publisher is None:
            try:
                from flask import current_app  # type: ignore
                broker = current_app.extensions.get('progress_broker')
                if broker is not None:
                    from .progress import BrokerPublisher
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
        error_result = None
        if spotdl_client and songs:
            # Drive downloads via SpotDL API (progress published via broker)
            try:
                # Inform UI that we are starting a multi-track job
                if publisher is not None:
                    try:
                        publisher.publish({
                            'song_display_name': title_name,
                            'status': 'Starting download',
                            'progress': 0,
                            'overall_completed': 0,
                            'overall_total': len(songs),
                            'overall_progress': 0,
                        })
                    except Exception:
                        pass
                sanitized_title = self.file_manager.sanitize_filename(title_name)
                output_template = os.path.join(item_specific_output_dir, f"{sanitized_title}")
                spotdl_client.set_output_template(output_template)
                results = spotdl_client.download_songs(songs)
                for song, p in results:
                    results_map[song.url] = str(p) if p else None
                    if p is None:
                        audio_failed = True
            except Exception as e:
                # Map specific SpotDL errors when possible
                try:
                    from spotdl.download.downloader import DownloaderError  # type: ignore
                    from spotdl.providers.audio.base import AudioProviderError  # type: ignore
                except Exception:
                    DownloaderError = Exception  # type: ignore
                    AudioProviderError = Exception  # type: ignore

                logger.exception("SpotDL API download failed: %s", e)
                if isinstance(e, AudioProviderError):
                    error_result = {"status": "error", "error_code": "provider_error", "message": str(e)}
                elif isinstance(e, DownloaderError):
                    error_result = {"status": "error", "error_code": "downloader_error", "message": str(e)}
                else:
                    error_result = {"status": "error", "error_code": "internal_error", "message": f"SpotDL API download failed: {e}"}
                audio_failed = True
        else:
            # Without SpotDL search results we cannot download audio
            return {"status": "error", "error_code": "search_unavailable", "message": "SpotDL search did not return results or client unavailable."}

        # --- Build track DTOs from SpotDL songs (canonical) ---
        track_dtos: List[TrackDTO] = []
        if songs:
            for s in songs:
                dto = song_to_track_dto(s)
                track_dtos.append(dto)
        else:
            # Keep compatibility: if we don't have songs (legacy metadata path), no tracks
            track_dtos = []

        # --- Lyrics handling ---
        # SpotDL pipeline: we will export embedded lyrics after audio paths are known.

        # --- Wait/check audio completion ---
        if audio_failed:
            return error_result or {"status": "error", "error_code": "download_failed", "message": f"Audio download failed for {title_name}."}
        # Fill local_path from results_map
        for t in track_dtos:
            t.local_path = results_map.get(t.spotify_url)

        # For SpotDL pipeline: export embedded lyrics alongside audio files (graceful if missing)
        if True:
            total_tracks = len(track_dtos)
            exported_count = 0
            for t in track_dtos:
                if t.local_path and not t.local_lyrics_path:
                    try:
                        exported = self.lyrics_service.export_embedded_lyrics(t.local_path)
                    except Exception:
                        exported = None
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
                        })
                    except Exception:
                        pass
            # Final completion event after lyrics export and persistence
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

        # Persist track rows (now including local audio path and lyrics path)
        try:
            self.repo.save_tracks(track_dtos)
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


