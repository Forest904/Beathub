# src/download_service.py
import subprocess
import json
import logging
import os
import re # For filename sanitization
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

logger = logging.getLogger(__name__)

class DownloadService:
    def __init__(self, base_output_dir, spotify_client=None, spotdl_audio_source="youtube-music", spotdl_format="opus"):
        """
        Initializes the DownloadService.
        :param base_output_dir: The base directory where downloaded content will be saved.
        :param spotify_client: An initialized Spotipy client instance (optional, will be created if None).
        :param spotdl_audio_source: The audio source to use for spotdl (e.g., "youtube-music", "youtube", "spotify").
        :param spotdl_format: The audio format to download (e.g., "opus", "mp3", "flac").
        """
        self.base_output_dir = base_output_dir
        self.spotdl_audio_source = spotdl_audio_source
        self.spotdl_format = spotdl_format

        # Initialize Spotipy client
        self.sp = spotify_client 
        if not self.sp: # Fallback if not passed (less ideal for shared client)
            try:
                self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                    client_id=os.environ.get('SPOTIPY_CLIENT_ID'),
                    client_secret=os.environ.get('SPOTIPY_CLIENT_SECRET')
                ))
                # Test connection
                self.sp.current_user() 
                logger.info("Spotipy client initialized successfully in DownloadService (fallback).")
            except Exception as e:
                logger.error(f"Failed to initialize Spotipy client in DownloadService: {e}")
                self.sp = None # Ensure it's None if initialization fails

        # Ensure base output directory exists
        os.makedirs(self.base_output_dir, exist_ok=True)
        logger.info(f"DownloadService initialized with base output directory: {self.base_output_dir}")

    def _sanitize_filename(self, name):
        """
        Sanitizes a string to be used as a safe filename or directory name.
        Removes/replaces characters that are illegal or problematic in file paths.
        """
        # Replace common problematic characters with underscore
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        # Remove any leading/trailing spaces
        name = name.strip()
        # Replace multiple underscores with a single one
        name = re.sub(r'_{2,}', '_', name)
        return name

    def _get_item_type(self, spotify_link):
        if "album" in spotify_link:
            return "album"
        elif "track" in spotify_link:
            return "track"
        elif "playlist" in spotify_link:
            return "playlist"
        return "unknown"

    def get_metadata_from_link(self, spotify_link):
        """
        Fetches metadata (title, artist, cover_url, spotify_id)
        from Spotify API for a given Spotify link without downloading.
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
                    'artist': album_info['artists'][0]['name'],
                    'image_url': album_info['images'][0]['url'] if album_info['images'] else None,
                    'spotify_url': album_info['external_urls']['spotify'],
                    'item_type': 'album'
                }
            elif item_type == "track":
                track_id = spotify_link.split('/')[-1].split('?')[0]
                track_info = self.sp.track(track_id)
                album_info = track_info['album'] # A track belongs to an album for consistent gallery display
                return {
                    'spotify_id': track_info['id'], # This is the track's spotify ID
                    'title': album_info['name'], # Use album name for gallery title
                    'artist': album_info['artists'][0]['name'], # Use album artist for gallery artist
                    'image_url': album_info['images'][0]['url'] if album_info['images'] else None,
                    'spotify_url': track_info['external_urls']['spotify'], # Use track's spotify URL
                    'item_type': 'track' # Report actual item type
                }
            elif item_type == "playlist":
                playlist_id = spotify_link.split('/')[-1].split('?')[0]
                playlist_info = self.sp.playlist(playlist_id)
                return {
                    'spotify_id': playlist_info['id'],
                    'title': playlist_info['name'],
                    'artist': playlist_info['owner']['display_name'],
                    'image_url': playlist_info['images'][0]['url'] if playlist_info['images'] else None,
                    'spotify_url': playlist_info['external_urls']['spotify'],
                    'item_type': 'playlist'
                }
            else:
                logger.warning(f"Unsupported Spotify link type: {spotify_link}")
                return None
        except Exception as e:
            logger.error(f"Error fetching Spotify metadata for {spotify_link}: {e}")
            return None

    def download_spotify_content(self, spotify_link):
        """
        Downloads content using spotdl and returns structured information.
        """
        item_type = self._get_item_type(spotify_link)
        metadata = self.get_metadata_from_link(spotify_link)

        if not metadata:
            return {"status": "error", "message": "Could not retrieve metadata for the given Spotify link."}

        # spotdl command:
        # --output "{artist} - {album}/{title}.{ext}" ensures structure like Artist Name - Album Name/Track.ext
        # within the base_output_dir.
        # Sanitizing artist/title for path safety.
        # Note: spotdl itself often sanitizes, but doing it beforehand adds robustness.
        sanitized_artist = self._sanitize_filename(metadata['artist'])
        sanitized_album_title = self._sanitize_filename(metadata['title'])

        # Use spotdl's templating directly from the base_output_dir
        # This will create a directory structure like:
        # base_output_dir/Artist - Album/Track.ext
        # For tracks, {album} will be the album the track belongs to.
        output_template = os.path.join(
            self.base_output_dir,
            f"{sanitized_artist} - {sanitized_album_title}",
            "{title}.{ext}" # spotdl will replace {title} and {ext}
        )

        command = [
            'spotdl',
            spotify_link,
            '--output', output_template,
            '--download-cover', 
            '--embed-metadata',
            '--metadata-tags', 'all',
            '--overwrite', 'skip', # Skip if already exists
            '--audio', self.spotdl_audio_source, # Use configurable audio source
            '--format', self.spotdl_format # Use configurable audio format
        ]
        
        try:
            logger.info(f"Executing spotdl command: {' '.join(command)}")
            process = subprocess.run(command, capture_output=True, text=True, check=True)
            logger.info(f"Spotdl stdout: {process.stdout}")
            # Check for errors in stderr, as spotdl often puts warnings/errors there
            if process.stderr:
                logger.warning(f"Spotdl stderr: {process.stderr.strip()}")

            tracks_info = []
            # For albums/playlists, we need to iterate over the items from Spotify API
            # or try to parse spotdl's output (which is less straightforward).
            # The current approach populates tracks_info from Spotify API calls
            # before download, but spotdl's actual downloaded files might vary.
            # A more advanced approach would be to parse spotdl's --log-level debug output
            # or scan the output_directory after download.

            if item_type == "album":
                album_tracks_response = self.sp.album_tracks(metadata['spotify_id'])
                for track in album_tracks_response['items']:
                    tracks_info.append({
                        'title': track['name'],
                        'artists': [a['name'] for a in track['artists']],
                        'cover_url': metadata['image_url'] # All tracks in an album share the same cover
                    })
            elif item_type == "track":
                # For a single track download, populate its info
                track_info = self.sp.track(metadata['spotify_id']) # Use the track's spotify_id directly
                tracks_info.append({
                    'title': track_info['name'],
                    'artists': [a['name'] for a in track_info['artists']],
                    'cover_url': metadata['image_url'] # Use album cover from metadata
                })
            elif item_type == "playlist":
                # Fetch tracks for playlist for the returned `tracks` array
                # Note: This might involve multiple API calls for large playlists
                playlist_tracks = []
                results = self.sp.playlist_items(metadata['spotify_id'])
                playlist_tracks.extend(results['items'])
                while results['next']:
                    results = self.sp.next(results)
                    playlist_tracks.extend(results['items'])
                
                for item in playlist_tracks:
                    track = item['track']
                    if track: # Ensure track is not None (e.g. if item was removed from playlist)
                        tracks_info.append({
                            'title': track['name'],
                            'artists': [a['name'] for a in track['artists']],
                            'cover_url': track['album']['images'][0]['url'] if track['album']['images'] else None
                        })
            
            return {
                "status": "success",
                "message": f"Successfully downloaded/processed {item_type}: {metadata['title']}",
                "item_name": metadata['title'],
                "item_type": item_type,
                "output_directory_base": os.path.join(self.base_output_dir, f"{sanitized_artist} - {sanitized_album_title}"), # The specific directory spotdl used
                "cover_art_saved": bool(metadata['image_url']), # Spotdl saves cover.jpg
                "tracks": tracks_info
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Spotdl failed with exit code {e.returncode}. Stderr: {e.stderr.strip()}")
            return {"status": "error", "message": f"Spotdl download failed: {e.stderr.strip()}"}
        except FileNotFoundError:
            logger.error("Spotdl command not found. Is spotdl installed and in your system's PATH?")
            return {"status": "error", "message": "Spotdl command not found. Please install it (e.g., `pip install spotdl`)."}
        except Exception as e:
            logger.error(f"An unexpected error occurred during download: {e}")
            return {"status": "error", "message": f"An unexpected error occurred during download: {str(e)}"}