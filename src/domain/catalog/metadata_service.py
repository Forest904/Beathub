# src/metadata_service.py
import logging
import threading
from typing import Any, Callable, Optional

import spotipy
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials

from config import Config
from src.utils.cache import TTLCache, MISSING

logger = logging.getLogger(__name__)

class MetadataService:
    def __init__(self, spotify_client_id=None,
                 spotify_client_secret=None,
                 spotify_client=None):
        """Initializes the MetadataService using keys from Config by default."""
        # Fallback to values from Config if not explicitly provided
        self._spotify_client_id = spotify_client_id or Config.SPOTIPY_CLIENT_ID
        self._spotify_client_secret = spotify_client_secret or Config.SPOTIPY_CLIENT_SECRET

        self._spotify_client_lock = threading.RLock()
        self._spotify_client_warned = False

        self.sp = spotify_client
        if not self.sp:
            self._initialize_spotify_client()
        else:
            logger.info("Spotipy client injected into MetadataService.")

        self._cache = TTLCache(maxsize=Config.METADATA_CACHE_MAXSIZE, ttl=Config.METADATA_CACHE_TTL_SECONDS)

    def _initialize_spotify_client(self, *, log_success_as_debug: bool = False) -> bool:
        if not self._spotify_client_id or not self._spotify_client_secret:
            if not self._spotify_client_warned:
                logger.warning("Spotify client ID and secret not provided in Config or args. MetadataService will be limited.")
                self._spotify_client_warned = True
            self.sp = None
            return False
        with self._spotify_client_lock:
            try:
                client = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                    client_id=self._spotify_client_id,
                    client_secret=self._spotify_client_secret
                ))
            except Exception as exc:
                logger.error("Failed to initialize Spotipy client in MetadataService: %s", exc, exc_info=True)
                self.sp = None
                return False
            else:
                self.sp = client
                message = "Spotipy client initialized successfully in MetadataService."
                if log_success_as_debug:
                    logger.debug("%s (refreshed)", message)
                else:
                    logger.info(message)
                return True

    def _refresh_spotify_client(self) -> bool:
        logger.debug("Refreshing Spotipy client credentials in MetadataService.")
        return self._initialize_spotify_client(log_success_as_debug=True)

    def _call_spotify_with_retry(self, action: str, call: Callable[[], Any]) -> Optional[Any]:
        if not self.sp:
            logger.error('Spotipy client not initialized. Cannot %s.', action)
            return None
        try:
            return call()
        except SpotifyException as exc:
            if exc.http_status == 401:
                logger.warning('Spotify token expired during %s. Attempting to refresh credentials.', action)
                if self._refresh_spotify_client():
                    try:
                        return call()
                    except SpotifyException as retry_exc:
                        logger.error('Spotify API call failed after token refresh during %s: %s', action, retry_exc, exc_info=True)
                        return None
            logger.error('Spotify API call failed during %s: %s', action, exc, exc_info=True)
            return None
        except Exception as exc:
            logger.error('Unexpected error during %s: %s', action, exc, exc_info=True)
            return None

    def _get_item_type(self, spotify_link):
        """Determines the type of Spotify item from its link."""
        link_lower = spotify_link.lower()
        if "album" in link_lower:
            return "album"
        elif "track" in link_lower:
            return "track"
        elif "playlist" in link_lower:
            return "playlist"
        return "unknown"

    def _extract_id_from_url(self, spotify_link):
        """Extracts the Spotify ID from the provided link.

        This helper normalizes links that may contain query strings or trailing
        slashes which would otherwise result in an empty ID when simply
        splitting on '/' and '?'.
        """
        from urllib.parse import urlparse

        path = urlparse(spotify_link).path
        segments = [segment for segment in path.split('/') if segment]
        if segments:
            return segments[-1]
        return ""

    def get_album_by_id(self, album_id):
        """ Fetches detailed metadata for a specific Spotify album by its ID. """
        cache_key = ('album_metadata', album_id)
        cached = self._cache.get(cache_key, MISSING)
        if cached is not MISSING:
            return cached

        album_info = self._call_spotify_with_retry(
            f'fetch album metadata for {album_id}',
            lambda: self.sp.album(album_id)
        )
        album_data = None
        if album_info:
            try:
                album_data = {
                    'spotify_id': album_info['id'],
                    'title': album_info['name'],
                    'artist': album_info['artists'][0]['name'] if album_info.get('artists') else 'Unknown Artist',
                    'image_url': album_info['images'][0]['url'] if album_info.get('images') else None,
                    'spotify_url': album_info.get('external_urls', {}).get('spotify'),
                    'item_type': 'album',
                    'release_date': album_info.get('release_date'),
                    'total_tracks': album_info.get('total_tracks')
                }
            except Exception as exc:
                logger.exception(f"Error processing Spotify album details for ID {album_id}: {exc}")
                album_data = None
        self._cache.set(cache_key, album_data)
        return album_data

    def get_metadata_from_link(self, spotify_link):
        """ Fetches metadata for a given Spotify link (track, album, or playlist). """
        cache_key = ('metadata_from_link', spotify_link)
        cached = self._cache.get(cache_key, MISSING)
        if cached is not MISSING:
            return cached

        item_type = self._get_item_type(spotify_link)
        try:
            if item_type == 'album':
                album_id = self._extract_id_from_url(spotify_link)
                if not album_id:
                    logger.warning(f"Could not parse album ID from {spotify_link}")
                    return None
                result = self.get_album_by_id(album_id)
                self._cache.set(cache_key, result)
                return result
            if item_type == 'track':
                track_id = self._extract_id_from_url(spotify_link)
                if not track_id:
                    logger.warning(f"Could not parse track ID from {spotify_link}")
                    return None
                raw_track_key = ('track_metadata_raw', track_id)
                track_info = self._cache.get(raw_track_key, MISSING)
                if track_info is MISSING:
                    track_info = self._call_spotify_with_retry(
                        f'fetch track metadata for {track_id}',
                        lambda: self.sp.track(track_id)
                    )
                    if track_info:
                        self._cache.set(raw_track_key, track_info)
                    else:
                        logger.warning(f"No track metadata returned for {track_id}")
                        return None
                album_info = track_info.get('album', {}) if track_info else {}
                result = {
                    'spotify_id': track_info['id'],
                    'title': track_info['name'],
                    'artist': track_info.get('artists', [{}])[0].get('name', 'Unknown Artist') if track_info.get('artists') else 'Unknown Artist',
                    'image_url': album_info.get('images', [{}])[0].get('url') if album_info.get('images') else None,
                    'spotify_url': track_info.get('external_urls', {}).get('spotify'),
                    'item_type': 'track',
                }
                self._cache.set(cache_key, result)
                return result
            if item_type == 'playlist':
                playlist_id = self._extract_id_from_url(spotify_link)
                if not playlist_id:
                    logger.warning(f"Could not parse playlist ID from {spotify_link}")
                    return None
                raw_playlist_key = ('playlist_metadata_raw', playlist_id)
                playlist_info = self._cache.get(raw_playlist_key, MISSING)
                if playlist_info is MISSING:
                    playlist_info = self._call_spotify_with_retry(
                        f'fetch playlist metadata for {playlist_id}',
                        lambda: self.sp.playlist(playlist_id)
                    )
                    if playlist_info:
                        self._cache.set(raw_playlist_key, playlist_info)
                    else:
                        logger.warning(f"No playlist metadata returned for {playlist_id}")
                        return None
                result = {
                    'spotify_id': playlist_info['id'],
                    'title': playlist_info['name'],
                    'artist': playlist_info.get('owner', {}).get('display_name', 'Unknown Owner'),
                    'image_url': playlist_info['images'][0]['url'] if playlist_info.get('images') else None,
                    'spotify_url': playlist_info.get('external_urls', {}).get('spotify'),
                    'item_type': 'playlist',
                }
                self._cache.set(cache_key, result)
                return result
            logger.warning(f"Unsupported Spotify link type: {spotify_link}")
            return None
        except Exception as exc:
            logger.exception(f"Error fetching Spotify metadata for {spotify_link}: {exc}")
            return None

    def get_tracks_details(self, spotify_id, item_type, image_url_from_metadata):
        """ Fetches detailed track information for albums, tracks, or playlists. """
        cache_key = ('track_details', item_type, spotify_id, image_url_from_metadata)
        cached = self._cache.get(cache_key, MISSING)
        if cached is not MISSING:
            return cached

        def _load_album_tracks():
            response = self.sp.album_tracks(spotify_id)
            items = response.get('items', [])
            detailed = []
            for track_item in items:
                track_artists = [a['name'] for a in track_item.get('artists', [])]
                detailed.append({
                    'spotify_id': track_item['id'],
                    'title': track_item['name'],
                    'artists': track_artists,
                    'duration_ms': track_item.get('duration_ms'),
                    'track_number': track_item.get('track_number'),
                    'disc_number': track_item.get('disc_number'),
                    'explicit': track_item.get('explicit'),
                    'spotify_url': track_item.get('external_urls', {}).get('spotify'),
                    'album_image_url': image_url_from_metadata,
                })
            return detailed

        def _load_single_track():
            track_item = self.sp.track(spotify_id)
            track_artists = [a['name'] for a in track_item.get('artists', [])]
            return [{
                'spotify_id': track_item['id'],
                'title': track_item['name'],
                'artists': track_artists,
                'duration_ms': track_item.get('duration_ms'),
                'track_number': track_item.get('track_number'),
                'disc_number': track_item.get('disc_number'),
                'explicit': track_item.get('explicit'),
                'spotify_url': track_item.get('external_urls', {}).get('spotify'),
                'album_name': track_item.get('album', {}).get('name'),
                'album_spotify_id': track_item.get('album', {}).get('id'),
                'album_image_url': image_url_from_metadata,
            }]

        def _load_playlist_tracks():
            playlist_items_response = self.sp.playlist_items(spotify_id)
            all_playlist_tracks = list(playlist_items_response.get('items', []))
            while playlist_items_response.get('next'):
                next_response = self._call_spotify_with_retry(
                    f'fetch next playlist page for {spotify_id}',
                    lambda resp=playlist_items_response: self.sp.next(resp)
                )
                if not next_response:
                    break
                playlist_items_response = next_response
                all_playlist_tracks.extend(playlist_items_response.get('items', []))
            detailed = []
            for item in all_playlist_tracks:
                track_item = item.get('track')
                if track_item and track_item.get('id'):
                    album_images = track_item.get('album', {}).get('images', [])
                    playlist_track_album_image_url = album_images[0]['url'] if album_images else None
                    track_artists = [a['name'] for a in track_item.get('artists', [])]
                    detailed.append({
                        'spotify_id': track_item['id'],
                        'title': track_item['name'],
                        'artists': track_artists,
                        'duration_ms': track_item.get('duration_ms'),
                        'track_number': track_item.get('track_number'),
                        'disc_number': track_item.get('disc_number'),
                        'explicit': track_item.get('explicit'),
                        'spotify_url': track_item.get('external_urls', {}).get('spotify'),
                        'album_name': track_item.get('album', {}).get('name'),
                        'album_spotify_id': track_item.get('album', {}).get('id'),
                        'album_image_url': playlist_track_album_image_url,
                        'added_at': item.get('added_at'),
                        'added_by_id': item.get('added_by', {}).get('id'),
                    })
            return detailed

        loaders = {
            'album': _load_album_tracks,
            'track': _load_single_track,
            'playlist': _load_playlist_tracks,
        }

        loader = loaders.get(item_type)
        if loader is None:
            logger.warning("Unsupported item_type '%s' for detailed track retrieval.", item_type)
            return []

        detailed_tracks_list = self._call_spotify_with_retry(
            f'fetch detailed track list for {item_type} {spotify_id}',
            loader
        )
        if detailed_tracks_list is None:
            return []

        self._cache.set(cache_key, detailed_tracks_list)
        return detailed_tracks_list

