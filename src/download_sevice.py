# src/download_service.py
import subprocess
import json
import logging
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials # Only if you want to initialize it here, otherwise pass from app.py

logger = logging.getLogger(__name__)

class DownloadService:
    def __init__(self, base_output_dir, spotify_client=None):
        self.base_output_dir = base_output_dir
        # If spotify_client is None, initialize it here. Otherwise, use the passed one.
        # This allows app.py to manage the spotipy client and pass it.
        self.sp = spotify_client 
        if not self.sp: # Fallback if not passed (less ideal for shared client)
            try:
                self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                    client_id=os.environ.get('SPOTIPY_CLIENT_ID'),
                    client_secret=os.environ.get('SPOTIPY_CLIENT_SECRET')
                ))
            except Exception as e:
                logger.error(f"Failed to initialize Spotipy client in DownloadService: {e}")
                self.sp = None # Ensure it's None if initialization fails

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
                album_info = track_info['album'] # A track belongs to an album
                return {
                    'spotify_id': album_info['id'], # Use album ID for consistent gallery entries
                    'title': album_info['name'],
                    'artist': album_info['artists'][0]['name'],
                    'image_url': album_info['images'][0]['url'] if album_info['images'] else None,
                    'spotify_url': album_info['external_urls']['spotify'],
                    'item_type': 'album' # Still treat as album for gallery purposes
                }
            elif item_type == "playlist":
                playlist_id = spotify_link.split('/')[-1].split('?')[0]
                playlist_info = self.sp.playlist(playlist_id)
                # For playlists, you might choose to show the playlist's own cover
                # or fetch individual track/album covers. For gallery, an album is better.
                # This example just returns placeholder for playlist for now.
                logger.warning("Playlist metadata retrieval is complex for gallery display. Skipping full details.")
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

        # Define output directory based on item type (e.g., artist/album for albums)
        # You'll need to adapt spotdl's output format to match this expectation.
        # A simple approach for now:
        output_dir = os.path.join(self.base_output_dir, metadata['artist'], metadata['title']).replace(" ", "_")
        os.makedirs(output_dir, exist_ok=True)
        
        # spotdl command:
        # --audio youtube-music (or preferred source)
        # --format opus (or mp3)
        # --output "{artist}/{album}/{title}.{ext}" # Example output format
        # --embed-metadata --metadata-tags all # Embed metadata in audio file
        # --save-file <path> # Save a list of downloaded files (useful for tracking)
        # --download-cover # Downloads cover art as separate file

        command = [
            'spotdl',
            spotify_link,
            '--output', os.path.join(output_dir, "{artist} - {album}/{title}.{ext}"), # More structured output
            '--download-cover', # This downloads album.jpg in the album's directory
            '--embed-metadata',
            '--metadata-tags', 'all',
            '--overwrite', 'skip' # Skip if already exists
        ]
        
        try:
            logger.info(f"Executing spotdl command: {' '.join(command)}")
            process = subprocess.run(command, capture_output=True, text=True, check=True)
            logger.info(f"Spotdl stdout: {process.stdout}")
            logger.info(f"Spotdl stderr: {process.stderr}")

            # Parse spotdl output to get actual track details if possible
            # This is a simplification; spotdl doesn't easily return structured track data
            # in its stdout for all downloads.
            # You might need to examine the output_dir for downloaded files.
            
            # For demonstration, let's assume we can get tracks from the metadata
            tracks_info = []
            if item_type == "album":
                album_tracks = self.sp.album_tracks(metadata['spotify_id'])
                for track in album_tracks['items']:
                    tracks_info.append({
                        'title': track['name'],
                        'artists': [a['name'] for a in track['artists']],
                        'cover_url': metadata['image_url'] # All tracks in an album share the same cover
                    })
            elif item_type == "track":
                 track_info = self.sp.track(spotify_link.split('/')[-1].split('?')[0])
                 tracks_info.append({
                    'title': track_info['name'],
                    'artists': [a['name'] for a in track_info['artists']],
                    'cover_url': metadata['image_url']
                 })


            return {
                "status": "success",
                "message": f"Successfully downloaded/processed {item_type}: {metadata['title']}",
                "item_name": metadata['title'],
                "item_type": item_type,
                "output_directory": output_dir, # This is the base directory for the item
                "cover_art_saved": bool(metadata['image_url']),
                "tracks": tracks_info
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Spotdl failed: {e.stderr}")
            return {"status": "error", "message": f"Spotdl download failed: {e.stderr.strip()}"}
        except FileNotFoundError:
            logger.error("Spotdl command not found. Is spotdl installed and in your PATH?")
            return {"status": "error", "message": "Spotdl command not found. Please install it."}
        except Exception as e:
            logger.error(f"An unexpected error occurred during download: {e}")
            return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}