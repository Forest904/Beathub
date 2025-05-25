import subprocess
import logging
import os
import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import sys
import json
import requests
import lyricsgenius

# Import configurations from your config.py
# Adjust this import path if config.py is in a different location
try:
    from config import (
        SPOTIPY_CLIENT_ID,
        SPOTIPY_CLIENT_SECRET,
        GENIUS_ACCESS_TOKEN,
        BASE_OUTPUT_DIR
    )
except ImportError:
    logging.error("Could not import configuration from config.py. Make sure it exists and contains the necessary variables.")
    # Fallback to environment variables if config.py import fails (less ideal, but for robustness)
    SPOTIPY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')
    GENIUS_ACCESS_TOKEN = os.environ.get('GENIUS_ACCESS_TOKEN')
    BASE_OUTPUT_DIR = os.environ.get('BASE_OUTPUT_DIR', 'downloads') # Default if not found

logger = logging.getLogger(__name__)

class DownloadService:
    def __init__(self, base_output_dir=None, spotify_client=None, spotdl_audio_source="youtube-music", spotdl_format="opus"):
        """
        Initializes the DownloadService.
        :param base_output_dir: The base directory where downloaded content will be saved. Defaults to BASE_OUTPUT_DIR from config.
        :param spotify_client: An initialized Spotipy client instance (optional, will be created if None).
        :param spotdl_audio_source: The audio source to use for spotdl (e.g., "youtube-music", "youtube", "spotify").
                                    Currently not used in the direct spotdl command to rely on defaults.
        :param spotdl_format: The audio format to download (e.g., "opus", "mp3", "flac").
                               Currently not used in the direct spotdl command to rely on defaults.
        """
        # Use provided base_output_dir or fallback to config.py's value
        self.base_output_dir = base_output_dir if base_output_dir is not None else BASE_OUTPUT_DIR
        
        self.spotdl_audio_source = spotdl_audio_source
        self.spotdl_format = spotdl_format

        self.sp = spotify_client
        if not self.sp:
            try:
                # Use imported variables directly
                self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                    client_id=SPOTIPY_CLIENT_ID,
                    client_secret=SPOTIPY_CLIENT_SECRET
                ))
                logger.info("Spotipy client initialized successfully in DownloadService (fallback).")
            except Exception as e:
                logger.error(f"Failed to initialize Spotipy client in DownloadService: {e}")
                self.sp = None
        
        # Initialize lyricsgenius for lyrics
        self.genius_client = None
        if GENIUS_ACCESS_TOKEN: # Use imported variable directly
            try:
                self.genius_client = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN, verbose=False, retries=3)
                logger.info("LyricsGenius client initialized successfully for lyrics.")
            except Exception as e:
                logger.error(f"Failed to initialize LyricsGenius client: {e}")
        else:
            logger.warning("GENIUS_ACCESS_TOKEN not set in config.py or .env. Lyrics will not be downloaded.")

        os.makedirs(self.base_output_dir, exist_ok=True)
        logger.info(f"DownloadService initialized with base output directory: {self.base_output_dir}")

    def _sanitize_filename(self, name):
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        name = name.strip()
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
                    'title': track_info['name'], # Changed to track name
                    'artist': track_info.get('artists', [{}])[0].get('name', 'Unknown Artist') if track_info.get('artists') else 'Unknown Artist', # Changed to track artist
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

    def _download_lyrics(self, track_title, track_artist, output_dir):
        if not self.genius_client:
            logger.warning("LyricsGenius client not initialized. Cannot download lyrics.")
            return None

        sanitized_track_title = self._sanitize_filename(track_title)
        sanitized_track_artist = self._sanitize_filename(track_artist)
        lyrics_filename = f"{sanitized_track_title} - {sanitized_track_artist}.txt"
        local_lyrics_path = os.path.join(output_dir, lyrics_filename)

        try:
            logger.info(f"Attempting to download lyrics for '{track_title}' by '{track_artist}'")
            song = self.genius_client.search_song(track_title, track_artist)
            if song and song.lyrics:
                with open(local_lyrics_path, 'w', encoding='utf-8') as f:
                    f.write(song.lyrics)
                logger.info(f"Successfully downloaded lyrics to {local_lyrics_path}")
                return local_lyrics_path
            else:
                logger.info(f"No lyrics found for '{track_title}' by '{track_artist}' on Genius.")
                return None
        except Exception as e:
            logger.error(f"Failed to download lyrics for '{track_title}' by '{track_artist}': {e}")
            return None

    def download_spotify_content(self, spotify_link):
        item_type = self._get_item_type(spotify_link)
        initial_metadata = self.get_metadata_from_link(spotify_link)

        if not initial_metadata:
            return {"status": "error", "message": "Could not retrieve initial metadata for the given Spotify link."}

        # Ensure artist and title are strings, even if metadata fetching had issues
        artist_name = initial_metadata.get('artist', 'Unknown Artist')
        title_name = initial_metadata.get('title', 'Unknown Title')

        sanitized_main_artist_or_owner = self._sanitize_filename(artist_name)
        sanitized_main_title = self._sanitize_filename(title_name)

        item_specific_output_dir = os.path.join(
            self.base_output_dir,
            f"{sanitized_main_artist_or_owner} - {sanitized_main_title}"
        )
        
        try:
            os.makedirs(item_specific_output_dir, exist_ok=True)
            logger.info(f"Ensured output directory exists: {item_specific_output_dir}")
        except OSError as e:
            logger.error(f"Could not create directory {item_specific_output_dir}: {e}")
            return {"status": "error", "message": f"Could not create output directory: {e}"}

        # --- Download and save album cover ---
        local_cover_image_path = None
        image_url_from_metadata = initial_metadata.get('image_url')
        if image_url_from_metadata:
            try:
                cover_filename = "cover.jpg"
                local_cover_image_path = os.path.join(item_specific_output_dir, cover_filename)

                logger.info(f"Attempting to download cover art from {image_url_from_metadata} to {local_cover_image_path}")
                response = requests.get(image_url_from_metadata, stream=True, timeout=15)
                response.raise_for_status() 

                with open(local_cover_image_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Successfully downloaded cover art to {local_cover_image_path}")
            except requests.exceptions.Timeout:
                logger.error(f"Timeout while trying to download cover art from {image_url_from_metadata}")
                local_cover_image_path = None
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to download cover art from {image_url_from_metadata}: {e}")
                local_cover_image_path = None
            except IOError as e:
                logger.error(f"Failed to save cover art to {local_cover_image_path}: {e}")
                local_cover_image_path = None
        else:
            logger.info("No image_url found in metadata, skipping cover art download.")
        # --- End download and save album cover ---

        output_template = os.path.join(
            item_specific_output_dir,
            "{title}.{ext}" # spotdl will fill in {title} and {ext}
        )

        command = [
            sys.executable, '-m', 'spotdl',
            spotify_link,
            '--output', output_template,
            '--overwrite', 'skip', # Prevent re-downloading existing files
        ]
        
        try:
            logger.info(f"Executing spotdl command: {' '.join(command)}")
            process = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
            logger.info(f"Spotdl stdout: {process.stdout}")
            if process.stderr:
                logger.warning(f"Spotdl stderr: {process.stderr.strip()}")

            detailed_tracks_list = []
            if not self.sp:
                logger.warning("Spotipy client not available for fetching detailed track list for JSON.")
            else:
                # Logic for fetching detailed_tracks_list
                if item_type == "album":
                    album_tracks_response = self.sp.album_tracks(initial_metadata['spotify_id'])
                    for track_item in album_tracks_response['items']:
                        track_artists = [a['name'] for a in track_item.get('artists', [])]
                        lyrics_path = self._download_lyrics(
                            track_item['name'], 
                            track_artists[0] if track_artists else 'Unknown Artist',
                            item_specific_output_dir
                        )
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
                            'local_lyrics_path': lyrics_path
                        })
                elif item_type == "track":
                    track_item = self.sp.track(initial_metadata['spotify_id']) 
                    track_artists = [a['name'] for a in track_item.get('artists', [])]
                    lyrics_path = self._download_lyrics(
                        track_item['name'], 
                        track_artists[0] if track_artists else 'Unknown Artist',
                        item_specific_output_dir
                    )
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
                        'local_lyrics_path': lyrics_path
                    })
                elif item_type == "playlist":
                    playlist_items_response = self.sp.playlist_items(initial_metadata['spotify_id'])
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
                            lyrics_path = self._download_lyrics(
                                track_item['name'], 
                                track_artists[0] if track_artists else 'Unknown Artist',
                                item_specific_output_dir
                            )
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
                                'local_lyrics_path': lyrics_path
                            })
            
            comprehensive_metadata_to_save = initial_metadata.copy()
            comprehensive_metadata_to_save['tracks_details'] = detailed_tracks_list
            
            metadata_json_path = os.path.join(item_specific_output_dir, "spotify_metadata.json")
            json_save_success = False
            try:
                with open(metadata_json_path, 'w', encoding='utf-8') as f:
                    json.dump(comprehensive_metadata_to_save, f, ensure_ascii=False, indent=4)
                logger.info(f"Spotify metadata saved to {metadata_json_path}")
                json_save_success = True
            except IOError as e:
                logger.error(f"Failed to save Spotify metadata to JSON at {metadata_json_path}: {e}")
            
            simplified_tracks_info_for_return = []
            if detailed_tracks_list:
                for t_detail in detailed_tracks_list:
                    simplified_tracks_info_for_return.append({
                        'title': t_detail.get('title'), 
                        'artists': t_detail.get('artists'), 
                        'cover_url': t_detail.get('album_image_url', image_url_from_metadata),
                        'local_lyrics_path': t_detail.get('local_lyrics_path')
                    })

            return {
                "status": "success",
                "message": f"Successfully processed {item_type}: {title_name}",
                "item_name": title_name,
                "item_type": item_type,
                "output_directory": item_specific_output_dir,
                "cover_art_url": image_url_from_metadata,
                "local_cover_image_path": local_cover_image_path,
                "tracks": simplified_tracks_info_for_return,
                "metadata_file_path": metadata_json_path if json_save_success else None
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Spotdl failed with exit code {e.returncode}. stdout: {e.stdout.strip() if e.stdout else ''}, stderr: {e.stderr.strip() if e.stderr else 'No stderr'}")
            return {"status": "error", "message": f"Spotdl download failed. Stderr: {e.stderr.strip() if e.stderr else 'No stderr'}"}
        except FileNotFoundError:
            logger.error("Python executable or spotdl module not found for subprocess call. Check your environment.")
            return {"status": "error", "message": "Python executable or spotdl module not found. Check your environment."}
        except Exception as e:
            logger.exception(f"An unexpected error occurred during download for {spotify_link}: {e}")
            return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}