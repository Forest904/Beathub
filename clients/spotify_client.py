# clients/spotify_client.py

import subprocess
import json
import os
import tempfile
import shutil
from typing import List, Dict, Any, Union

# Import models
from models.playlist import Playlist
from models.track import Track

# Function to execute spotdl command and capture JSON output
def _run_spotdl_save(spotify_link: str) -> Dict[str, Any] | None:
    """
    Runs the 'spotdl save' command as a subprocess within a temporary directory
    to get metadata in JSON format.

    Args:
        spotify_link: The URL of the Spotify item (playlist, album, or track).

    Returns:
        A dictionary containing the parsed JSON metadata (which is typically a list of track dicts),
        or None if an error occurs.
    """
    print(f"Running spotdl save for: {spotify_link}")

    temp_dir = None
    try:
        # Create a temporary directory to run the command from and save the .spotdl file
        temp_dir = tempfile.mkdtemp()
        # The expected output filename when running from within the directory
        output_filename = "metadata.spotdl"
        output_file_path = os.path.join(temp_dir, output_filename) # Full expected path

        print(f"Temporary directory created: {temp_dir}")
        print(f"Expected output file path: {output_file_path}")

        # Construct the spotdl command
        # Use 'save' operation and specify the filename with --save-file.
        # We run the command from temp_dir using cwd.
        command = [
            'spotdl',
            'save',
            spotify_link,
            '--save-file', output_filename, # Re-added --save-file with just the filename
            '--log-level', 'ERROR' # Reduce noise
        ]

        print(f"Executing command: {' '.join(command)} in directory: {temp_dir}")

        # Execute the command, setting the current working directory (cwd)
        process = subprocess.run(
            command,
            cwd=temp_dir, # Set the current working directory for the subprocess
            capture_output=True,
            text=True,
            check=True
        )

        print("spotdl command executed successfully.")
        # Print spotdl's stdout and stderr for debugging
        print("--- spotdl stdout ---")
        print(process.stdout)
        print("--- spotdl stderr ---")
        print(process.stderr)
        print("---------------------")

        # --- Debugging: List contents of the temporary directory ---
        print(f"Listing contents of temporary directory: {temp_dir}")
        try:
            dir_contents = os.listdir(temp_dir)
            print(f"Contents: {dir_contents}")
            if output_filename in dir_contents:
                print(f"'{output_filename}' found in temporary directory.")
            else:
                print(f"'{output_filename}' NOT found in temporary directory.")
        except Exception as list_e:
            print(f"Error listing directory contents: {list_e}")
        # --- End Debugging ---


        # Read the saved metadata file
        if os.path.exists(output_file_path):
            print(f"Attempting to read metadata from {output_file_path}")
            with open(output_file_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            print(f"Successfully read metadata from {output_file_path}")
            # The .spotdl file contains a list of track dictionaries
            return metadata # Return the loaded list
        else:
            print(f"Error: spotdl did not create the expected output file at {output_file_path}")
            return None

    except FileNotFoundError:
        print("Error: 'spotdl' command not found. Is spotdl installed and in your PATH?")
        print("Install spotdl using: pip install spotdl")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running spotdl subprocess: {e}")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"Stderr: {e.stderr}")
        print(f"Stdout: {e.stdout}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from spotdl output file {output_file_path}: {e}")
        try:
            with open(output_file_path, 'r', encoding='utf-8') as f:
                print("File content:")
                print(f.read())
        except Exception as read_e:
            print(f"Could not read content of {output_file_path}: {read_e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while running spotdl: {e}")
        return None
    finally:
        # Clean up the temporary directory
        if temp_dir and os.path.exists(temp_dir):
            print(f"Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir)

# Function to execute spotdl url command to get download URL
def _run_spotdl_url(spotify_track_url: str) -> str | None:
    """
    Runs the 'spotdl url' command as a subprocess to get the download URL for a track.

    Args:
        spotify_track_url: The URL of the Spotify track.

    Returns:
        The download URL (YouTube URL), or None if not found or an error occurs.
    """
    print(f"Running spotdl url for track: {spotify_track_url}")

    try:
        # Construct the spotdl command
        # Use 'url' operation and the Spotify track URL
        command = [
            'spotdl',
            'url',
            spotify_track_url,
            '--log-level', 'ERROR' # Reduce noise
        ]

        print(f"Executing command: {' '.join(command)}")

        # Execute the command
        # spotdl url typically prints the URL to stdout
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        print("spotdl url command executed successfully.")
        print("--- spotdl url stdout ---")
        print(process.stdout)
        print("--- spotdl url stderr ---")
        print(process.stderr)
        print("-------------------------")

        # The download URL is usually the first line of stdout
        download_url = process.stdout.strip().split('\n')[0]
        if download_url and download_url.startswith("http"): # Basic check if it looks like a URL
             print(f"Found download URL: {download_url}")
             return download_url
        else:
             print("spotdl url did not return a valid URL in stdout.")
             return None

    except FileNotFoundError:
        print("Error: 'spotdl' command not found. Is spotdl installed and in your PATH?")
        print("Install spotdl using: pip install spotdl")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running spotdl url subprocess: {e}")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"Stderr: {e.stderr}")
        print(f"Stdout: {e.stdout}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while running spotdl url: {e}")
        return None


class SpotifyClient:
    """
    Wraps spotDL functionality to fetch playlists, albums, and tracks from Spotify.
    Uses spotdl's 'save' operation to get metadata and 'url' operation to get download URLs.
    """
    def __init__(self):
        print("SpotifyClient initialized.")
        pass

    def fetch_spotify_item(self, spotify_link: str) -> Union[List[Track], None]:
        """
        Fetches metadata for a Spotify item (playlist, album, or track) using spotdl save,
        and then fetches download URLs for each track using spotdl url.

        Args:
            spotify_link: The URL of the Spotify item.

        Returns:
            A list of Track objects populated with metadata and download URLs,
            or None if fetching metadata fails or no tracks are found.
        """
        print(f"SpotifyClient: Fetching data and download URLs for link: {spotify_link}")

        # Step 1: Get initial metadata using spotdl save
        tracks_data = _run_spotdl_save(spotify_link)

        if not tracks_data: # Check if the list is None or empty
            if tracks_data is None:
                 print(f"SpotifyClient: Failed to fetch metadata for {spotify_link}")
            else: # tracks_data is an empty list
                 print(f"SpotifyClient: No track data found in metadata for {spotify_link}")
            return None # Return None if fetching failed or no tracks were found

        # The 'save' command output (.spotdl file) is typically a JSON list of track objects.
        if not isinstance(tracks_data, list):
             print(f"SpotifyClient: Unexpected metadata structure received for {spotify_link}. Expected a list of tracks.")
             print(f"Received type: {type(tracks_data)}")
             return None

        # Step 2: Convert raw track data to Track objects and fetch download URLs
        tracks = []
        for i, t in enumerate(tracks_data):
            try:
                # Correctly access data based on the structure from your error output
                track = Track(
                    id=t.get('song_id', ''), # Use 'song_id' for track ID
                    title=t.get('name', 'Unknown Title'), # Use 'name' for track title
                    artists=t.get('artists', ['Unknown Artist']), # 'artists' is a list of strings
                    album=t.get('album_name'), # Use 'album_name' for album name
                    duration_ms=t.get('duration') * 1000 if t.get('duration') is not None else None, # Convert seconds to milliseconds
                    # download_url will be fetched in the next step
                    download_url=None,
                    isrc=t.get('isrc')
                )

                # Step 3: Fetch download URL for the current track
                # Use the Spotify track URL from the metadata for the 'spotdl url' command
                spotify_track_url = t.get('url') # spotdl save output includes the track URL
                if spotify_track_url:
                    download_url = _run_spotdl_url(spotify_track_url)
                    track.download_url = download_url
                else:
                    print(f"SpotifyClient: No Spotify URL found for track '{track.title}'. Cannot fetch download URL.")

                tracks.append(track)

            except Exception as e:
                print(f"SpotifyClient: Error processing track data or fetching URL for track {i+1}: {e}")
                # Continue processing other tracks

        print(f"SpotifyClient: Successfully processed and attempted to fetch URLs for {len(tracks)} tracks.")
        # Note: Some tracks might still have download_url as None if fetching failed
        return tracks # Return list of Track objects with download URLs

