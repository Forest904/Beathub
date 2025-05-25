import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import logging
import os

logger = logging.getLogger(__name__)

class MetadataService:
    def __init__(self, spotify_client_id=None, spotify_client_secret=None, spotify_client=None):
        """
        Initializes the MetadataService.
        :param spotify_client_id: Your Spotify client ID.
        :param spotify_client_secret: Your Spotify client secret.
        :param spotify_client: An initialized Spotipy client instance (optional, will be created if None).
        """
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
                logger.warning("Spotify client ID and secret not provided. MetadataService will be limited.")

    def _get_item_type(self, spotify_link):
        """Determines the type of Spotify item from its link."""
        if "album" in spotify_link:
            return "album"
        elif "track" in spotify_link:
            return "track"
        elif "playlist" in spotify_link:
            return "playlist"
        return "unknown"

    def get_metadata_from_link(self, spotify_link):
        """
        Fetches metadata for a given Spotify link (track, album, or playlist).
        :param spotify_link: The Spotify URL.
        :return: A dictionary containing metadata, or None if an error occurs.
        """
        if not self.sp:
            logger.error("Spotipy client not initialized. Cannot fetch metadata.")
            return None

        item_type = self._get_item_type(spotify_link)
        try:
            if item_type == "album":
                album_id = spotify_link.split('/')[-1].split('?')[0]
                album_info = self.sp.album(album_id)
                return {
                    'spotify_id': album_info['id'],
                    'title': album_info['name'],
                    'artist': album_info['artists'][0]['name'] if album_info.get('artists') else 'Unknown Artist',
                    'image_url': album_info['images'][0]['url'] if album_info.get('images') else None,
                    'spotify_url': album_info.get('external_urls', {}).get('spotify'),
                    'item_type': 'album',
                }
            elif item_type == "track":
                track_id = spotify_link.split('/')[-1].split('?')[0]
                track_info = self.sp.track(track_id)
                album_info = track_info.get('album', {})
                return {
                    'spotify_id': track_info['id'],
                    'title': track_info['name'],
                    'artist': track_info.get('artists', [{}])[0].get('name', 'Unknown Artist') if track_info.get('artists') else 'Unknown Artist',
                    'image_url': album_info.get('images', [{}])[0].get('url') if album_info.get('images') else None,
                    'spotify_url': track_info.get('external_urls', {}).get('spotify'),
                    'item_type': 'track',
                }
            elif item_type == "playlist":
                playlist_id = spotify_link.split('/')[-1].split('?')[0]
                playlist_info = self.sp.playlist(playlist_id)
                return {
                    'spotify_id': playlist_info['id'],
                    'title': playlist_info['name'],
                    'artist': playlist_info.get('owner', {}).get('display_name', 'Unknown Owner'),
                    'image_url': playlist_info['images'][0]['url'] if playlist_info.get('images') else None,
                    'spotify_url': playlist_info.get('external_urls', {}).get('spotify'),
                    'item_type': 'playlist',
                }
            else:
                logger.warning(f"Unsupported Spotify link type: {spotify_link}")
                return None
        except Exception as e:
            logger.exception(f"Error fetching Spotify metadata for {spotify_link}: {e}")
            return None

    def get_tracks_details(self, spotify_id, item_type, image_url_from_metadata):
        """
        Fetches detailed track information for albums, tracks, or playlists.
        This is a helper to get full track lists, often used after initial metadata.
        """
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
        return detailed_tracks_list