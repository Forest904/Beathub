# src/metadata_service.py
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import logging

from config import Config
from .utils.cache import TTLCache, MISSING

logger = logging.getLogger(__name__)

class MetadataService:
    def __init__(self, spotify_client_id=None,
                 spotify_client_secret=None,
                 spotify_client=None):
        """Initializes the MetadataService using keys from Config by default."""
        # Fallback to values from Config if not explicitly provided
        spotify_client_id = spotify_client_id or Config.SPOTIPY_CLIENT_ID
        spotify_client_secret = spotify_client_secret or Config.SPOTIPY_CLIENT_SECRET

        self.sp = spotify_client
        if not self.sp:
            if spotify_client_id and spotify_client_secret:
                try:
                    self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                        client_id=spotify_client_id,
                        client_secret=spotify_client_secret
                    ))
                    logger.info("Spotipy client initialized successfully in MetadataService.")
                except Exception as e:
                    logger.error(f"Failed to initialize Spotipy client in MetadataService: {e}")
                    self.sp = None
            else:
                logger.warning("Spotify client ID and secret not provided in Config or args. MetadataService will be limited.")

        self._cache = TTLCache(maxsize=Config.METADATA_CACHE_MAXSIZE, ttl=Config.METADATA_CACHE_TTL_SECONDS)

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

        if not self.sp:
            logger.error("Spotipy client not initialized. Cannot fetch album by ID.")
            return None
        try:
            album_info = self.sp.album(album_id)
            album_data = None
            if album_info:
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
            self._cache.set(cache_key, album_data)
            return album_data
        except Exception as e:
            logger.exception(f"Error fetching Spotify album details for ID {album_id}: {e}")
            return None

    def get_metadata_from_link(self, spotify_link):
        """ Fetches metadata for a given Spotify link (track, album, or playlist). """
        cache_key = ('metadata_from_link', spotify_link)
        cached = self._cache.get(cache_key, MISSING)
        if cached is not MISSING:
            return cached

        if not self.sp:
            logger.error("Spotipy client not initialized. Cannot fetch metadata.")
            return None

        item_type = self._get_item_type(spotify_link)
        try:
            if item_type == "album":
                album_id = self._extract_id_from_url(spotify_link)
                if not album_id:
                    logger.warning(f"Could not parse album ID from {spotify_link}")
                    return None
                result = self.get_album_by_id(album_id)
                self._cache.set(cache_key, result)
                return result
            elif item_type == "track":
                track_id = self._extract_id_from_url(spotify_link)
                if not track_id:
                    logger.warning(f"Could not parse track ID from {spotify_link}")
                    return None
                raw_track_key = ('track_metadata_raw', track_id)
                track_info = self._cache.get(raw_track_key, MISSING)
                if track_info is MISSING:
                    track_info = self.sp.track(track_id)
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
            elif item_type == "playlist":
                playlist_id = self._extract_id_from_url(spotify_link)
                if not playlist_id:
                    logger.warning(f"Could not parse playlist ID from {spotify_link}")
                    return None
                raw_playlist_key = ('playlist_metadata_raw', playlist_id)
                playlist_info = self._cache.get(raw_playlist_key, MISSING)
                if playlist_info is MISSING:
                    playlist_info = self.sp.playlist(playlist_id)
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
            else:
                logger.warning(f"Unsupported Spotify link type: {spotify_link}")
                return None
        except Exception as e:
            logger.exception(f"Error fetching Spotify metadata for {spotify_link}: {e}")
            return None

    def get_tracks_details(self, spotify_id, item_type, image_url_from_metadata):
        """ Fetches detailed track information for albums, tracks, or playlists. """
        cache_key = ('track_details', item_type, spotify_id, image_url_from_metadata)
        cached = self._cache.get(cache_key, MISSING)
        if cached is not MISSING:
            return cached

        if not self.sp:
            logger.error("Spotipy client not initialized. Cannot fetch detailed track list.")
            return []

        detailed_tracks_list = []
        try:
            if item_type == "album":
                album_tracks_response = self.sp.album_tracks(spotify_id)
                for track_item in album_tracks_response['items']:
                    track_artists = [a['name'] for a in track_item.get('artists', [])]
                    detailed_tracks_list.append({
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
            elif item_type == "track":
                track_item = self.sp.track(spotify_id)
                track_artists = [a['name'] for a in track_item.get('artists', [])]
                detailed_tracks_list.append({
                    'spotify_id': track_item['id'],
                    'title': track_item['name'],
                    'artists': track_artists,
                    'duration_ms': track_item.get('duration_ms'),
                    'track_number': track_item.get('track_number'),
                    'disc_number': track_item.get('disc_number'),
                    'explicit': track_item.get('explicit'),
                    'spotify_url': track_item.get('external_urls', {}).get('spotify'),
                    'album_name': track_item.get('album',{}).get('name'),
                    'album_spotify_id': track_item.get('album',{}).get('id'),
                    'album_image_url': image_url_from_metadata,
                })
            elif item_type == "playlist":
                playlist_items_response = self.sp.playlist_items(spotify_id)
                all_playlist_tracks = playlist_items_response['items']
                while playlist_items_response['next']:
                    playlist_items_response = self.sp.next(playlist_items_response)
                    all_playlist_tracks.extend(playlist_items_response['items'])

                for item in all_playlist_tracks:
                    track_item = item.get('track')
                    if track_item and track_item.get('id'):
                        album_images = track_item.get('album',{}).get('images', [])
                        playlist_track_album_image_url = album_images[0]['url'] if album_images else None
                        track_artists = [a['name'] for a in track_item.get('artists', [])]
                        detailed_tracks_list.append({
                            'spotify_id': track_item['id'],
                            'title': track_item['name'],
                            'artists': track_artists,
                            'duration_ms': track_item.get('duration_ms'),
                            'track_number': track_item.get('track_number'),
                            'disc_number': track_item.get('disc_number'),
                            'explicit': track_item.get('explicit'),
                            'spotify_url': track_item.get('external_urls', {}).get('spotify'),
                            'album_name': track_item.get('album',{}).get('name'),
                            'album_spotify_id': track_item.get('album',{}).get('id'),
                            'album_image_url': playlist_track_album_image_url,
                            'added_at': item.get('added_at'),
                            'added_by_id': item.get('added_by', {}).get('id'),
                        })
        except Exception as e:
            logger.exception(f"Error fetching detailed track list for {item_type} ID {spotify_id}: {e}")
        else:
            self._cache.set(cache_key, detailed_tracks_list)
        return detailed_tracks_list




