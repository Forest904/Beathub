# src/cd_burning_service.py

import os
import json
import logging
import subprocess
import re # For parsing cdrecord output
import tempfile # For temporary WAV storage
import shutil # For removing temporary directories
import threading # For thread-safe status updates

from pydub import AudioSegment 

# Initialize logger for this service
logger = logging.getLogger(__name__)

# --- Global CD Burning Status Manager (Singleton-like) ---
# This class manages the state of the CD burning process,
# allowing the Flask routes to poll for updates.
class CDBurnStatusManager:
    _instance = None
    _status_lock = threading.Lock() # To ensure thread-safe updates

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CDBurnStatusManager, cls).__new__(cls)
            # Initialize state only once
            cls._instance._reset_status()
        return cls._instance

    def _reset_status(self):
        with self._status_lock:
            self._is_burning = False
            self._current_status = 'Idle' # States: 'Idle', 'Scanning Burner', 'Burner Ready', 'No Burner', 'Disc Check', 'Disc Ready', 'No Disc', 'Converting WAVs', 'Burning Disc', 'Completed', 'Error'
            self._progress_percentage = 0 # 0-100
            self._last_error = None
            self._burner_detected = False
            self._disc_present = False
            self._disc_blank_or_erasable = False # True if disc is blank or can be overwritten

    def get_status(self):
        with self._status_lock:
            return {
                'is_burning': self._is_burning,
                'current_status': self._current_status,
                'progress_percentage': self._progress_percentage,
                'last_error': self._last_error,
                'burner_detected': self._burner_detected,
                'disc_present': self._disc_present,
                'disc_blank_or_erasable': self._disc_blank_or_erasable
            }

    def start_burn(self, status="Starting...", progress=0):
        with self._status_lock:
            self._is_burning = True
            self._current_status = status
            self._progress_percentage = progress
            self._last_error = None

    def update_status(self, status, progress=None):
        with self._status_lock:
            self._current_status = status
            if progress is not None:
                self._progress_percentage = progress
            logger.info(f"CD Burn Status: {self._current_status} (Progress: {self._progress_percentage}%)")

    def set_error(self, message):
        with self._status_lock:
            self._is_burning = False
            self._current_status = 'Error'
            self._last_error = message
            logger.error(f"CD Burn Error: {message}")

    def complete_burn(self):
        with self._status_lock:
            self._is_burning = False
            self._current_status = 'Completed'
            self._progress_percentage = 100
            self._last_error = None
            logger.info("CD Burn Completed Successfully.")

    def is_burning(self):
        with self._status_lock:
            return self._is_burning

    def update_burner_state(self, detected=False, present=False, blank_or_erasable=False):
        with self._status_lock:
            self._burner_detected = detected
            self._disc_present = present
            self._disc_blank_or_erasable = blank_or_erasable
            if detected and present and blank_or_erasable:
                self._current_status = 'Burner Ready'
            elif detected and present and not blank_or_erasable:
                self._current_status = 'Disc Not Blank/Erasable'
            elif detected and not present:
                self._current_status = 'No Disc'
            else:
                self._current_status = 'No Burner Detected'
            logger.info(f"Burner State Updated: Detected={detected}, Present={present}, Blank/Erasable={blank_or_erasable}, Status='{self._current_status}'")


# Global instance of the status manager
CD_BURN_STATUS_MANAGER = CDBurnStatusManager()


class CDBurningService:
    def __init__(self, app_logger=None, base_output_dir=None):
        self.logger = app_logger if app_logger else logging.getLogger(__name__)
        self.base_output_dir = base_output_dir # Not directly used for input, but good for context
        self.cdrecord_path = "cdrecord" # Assumes cdrecord.exe is in PATH or specify full path
        self.current_burner_device = None # e.g., '0,0,0' or specific Windows drive letter if detected

    def _run_command(self, command, description="", check=True):
        """Helper to run a subprocess command and log output."""
        self.logger.info(f"Executing: {' '.join(command)} ({description})")
        process = None # Initialize process to None
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check,
                encoding='utf-8' # Ensure correct encoding for output
            )
            self.logger.debug(f"Command '{' '.join(command)}' stdout: {process.stdout.strip()}")
            if process.stderr.strip():
                self.logger.warning(f"Command '{' '.join(command)}' stderr: {process.stderr.strip()}")
            return process.stdout.strip()
        except FileNotFoundError:
            error_msg = f"Command not found: '{command[0]}'. Make sure '{command[0]}' (cdrecord.exe, ffmpeg.exe) is installed and in your system's PATH."
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed with exit code {e.returncode}: {e.cmd}\nStdout: {e.stdout}\nStderr: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"An unexpected error occurred running command '{' '.join(command)}': {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        finally:
            # Attempt to terminate the process if it's still running (e.g., if exception occurred early)
            if process and process.poll() is None:
                process.terminate()
                self.logger.warning(f"Terminated hung subprocess: {' '.join(command)}")


    def scan_for_burner(self):
        """
        Scans for available CD/DVD burners using 'cdrecord -scanbus'.
        Updates the global status manager.
        """
        self.logger.info("Scanning for CD/DVD burners...")
        CD_BURN_STATUS_MANAGER.update_status("Scanning Burner...")
        try:
            # Using -scanbus to find devices
            # On Windows, cdrecord.exe is typically used with device address like '0,0,0'
            command = [self.cdrecord_path, '-scanbus']
            output = self._run_command(command, "scanning for burners", check=False) # check=False because it might exit non-zero if no burner

            # Parse output to find burner device (e.g., 'dev=0,0,0')
            # Example output: "scsibus0: 0,0,0   0) 'HL-DT-ST' 'DVDRAM GT30N   ' 'A100' Removable CD-ROM"
            burner_match = re.search(r'scsibus\d+:\s+(\d+,\d+,\d+)\s+\d+\)\s+\'.*?\'\s+\'.*?\'\s+\'.*?\'\s+Removable CD-ROM', output)

            if burner_match:
                self.current_burner_device = burner_match.group(1)
                self.logger.info(f"CD burner detected at device: {self.current_burner_device}")
                CD_BURN_STATUS_MANAGER.update_burner_state(detected=True)
                return True
            else:
                self.logger.warning("No CD/DVD burner found on system.")
                CD_BURN_STATUS_MANAGER.update_burner_state(detected=False)
                return False
        except Exception as e:
            self.logger.error(f"Error during burner scan: {e}")
            CD_BURN_STATUS_MANAGER.update_burner_state(detected=False)
            CD_BURN_STATUS_MANAGER.set_error(f"Burner scan failed: {e}")
            return False

    def check_disc_status(self):
        """
        Checks the status of the disc in the detected burner.
        Updates the global status manager.
        """
        if not self.current_burner_device:
            self.logger.warning("No burner detected to check disc status.")
            CD_BURN_STATUS_MANAGER.update_burner_state(detected=False) # Ensure consistent state
            return False

        self.logger.info(f"Checking disc status in burner {self.current_burner_device}...")
        CD_BURN_STATUS_MANAGER.update_status("Checking Disc...")
        try:
            # -checkmedia for checking disc properties
            command = [self.cdrecord_path, '-v', f'dev={self.current_burner_device}', '-checkmedia']
            output = self._run_command(command, "checking disc status", check=False)

            # Analyze output for disc presence and type (blank/writable)
            disc_present = "Disc present" in output or "Track 1" in output # crude check, improve later
            blank_or_erasable = "Disc status: blank" in output or "Disc status: empty" in output or "appendable" in output or "overwriteable" in output

            CD_BURN_STATUS_MANAGER.update_burner_state(
                detected=True, # We know a burner is detected from scan_for_burner
                present=disc_present,
                blank_or_erasable=blank_or_erasable
            )
            return disc_present and blank_or_erasable

        except Exception as e:
            self.logger.error(f"Error checking disc status: {e}")
            CD_BURN_STATUS_MANAGER.update_burner_state(detected=True, present=False, blank_or_erasable=False) # Reset state
            CD_BURN_STATUS_MANAGER.set_error(f"Disc status check failed: {e}")
            return False

    def _parse_spotify_metadata(self, content_dir):
        """
        Parses the spotify_metadata.json file to get track order and titles.
        Assumes metadata format is consistent (e.g., has a 'tracks' key with 'items' list).
        """
        metadata_path = os.path.join(content_dir, "spotify_metadata.json")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"spotify_metadata.json not found in {content_dir}")

        self.logger.info(f"Parsing spotify_metadata.json from {metadata_path}")
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        tracks_data = []
        # Handle different Spotify item types (album, playlist, track)
        # For simplicity, assuming 'tracks' -> 'items' -> 'track' structure for albums/playlists
        # and direct track info for single tracks.
        if 'tracks' in metadata and 'items' in metadata['tracks']: # Album or Playlist
            for item in metadata['tracks']['items']:
                track_info = item.get('track') if item.get('track') else item # Handle playlist vs album item structure
                if track_info:
                    tracks_data.append({
                        'title': track_info.get('name'),
                        'artist': track_info.get('artists')[0]['name'] if track_info.get('artists') else 'Unknown Artist'
                        # Add other metadata if needed, like duration_ms for total time
                    })
        elif metadata.get('type') == 'track': # Single track
            tracks_data.append({
                'title': metadata.get('name'),
                'artist': metadata.get('artists')[0]['name'] if metadata.get('artists') else 'Unknown Artist'
            })
        else:
            raise ValueError("Unsupported spotify_metadata.json format. Expected album/playlist or single track.")

        if not tracks_data:
            raise ValueError("No tracks found in spotify_metadata.json.")

        self.logger.info(f"Found {len(tracks_data)} tracks in metadata.")
        return tracks_data

    def _convert_mp3_to_wav(self, content_dir, tracks_data, temp_wav_dir):
        """
        Converts MP3 files to WAV format in the specified temporary directory.
        Returns a list of paths to the converted WAV files, in the correct order.
        """
        self.logger.info(f"Starting MP3 to WAV conversion in {content_dir}...")
        wav_file_paths = []
        total_tracks = len(tracks_data)

        for i, track in enumerate(tracks_data):
            # Sanitize track title for filename matching, similar to FileManager
            sanitized_title = track['title']
            # Re-apply FileManager's sanitization logic here for robust matching
            sanitized_title = re.sub(r'[\\/:*?"<>|]', '_', sanitized_title)
            sanitized_title = sanitized_title.strip()
            sanitized_title = re.sub(r'_{2,}', '_', sanitized_title)


            mp3_file_name_pattern = f"{re.escape(sanitized_title)}\.mp3" # Use re.escape for special chars in title
            found_mp3_path = None

            # Look for the MP3 file in the content_dir
            for f_name in os.listdir(content_dir):
                if re.fullmatch(mp3_file_name_pattern, f_name, re.IGNORECASE):
                    found_mp3_path = os.path.join(content_dir, f_name)
                    break

            if not found_mp3_path:
                # Fallback for common cases where 'artist - title' might be the filename
                # This needs to be robust. Given the `FileManager` logic, the `sanitized_title.mp3`
                # should be the primary pattern. If not, this is where you'd debug your download process.
                fallback_name_pattern = f"{re.escape(track['artist'])} - {re.escape(sanitized_title)}\.mp3"
                for f_name in os.listdir(content_dir):
                     if re.fullmatch(fallback_name_pattern, f_name, re.IGNORECASE):
                        found_mp3_path = os.path.join(content_dir, f_name)
                        break
                if not found_mp3_path:
                    self.logger.warning(f"MP3 not found for track '{track['title']}'. Skipping.")
                    CD_BURN_STATUS_MANAGER.set_error(f"MP3 not found for track '{track['title']}'. Aborting.")
                    raise FileNotFoundError(f"MP3 file not found for track: {track['title']}")

            wav_output_path = os.path.join(temp_wav_dir, f"{i+1:02d}_{sanitized_title}.wav") # Prefix with number for order

            try:
                self.logger.info(f"Converting '{os.path.basename(found_mp3_path)}' to WAV...")
                audio = AudioSegment.from_mp3(found_mp3_path)
                # Ensure 44.1 kHz, 16-bit, stereo for audio CD compatibility
                audio = audio.set_frame_rate(44100).set_channels(2).set_sample_width(2)
                audio.export(wav_output_path, format="wav")
                wav_file_paths.append(wav_output_path)
                progress = int(((i + 1) / total_tracks) * 50) # Conversion takes up 50% of total progress
                CD_BURN_STATUS_MANAGER.update_status(f"Converting WAVs ({i+1}/{total_tracks})", progress)
            except Exception as e:
                self.logger.exception(f"Error converting MP3 '{found_mp3_path}' to WAV: {e}")
                raise RuntimeError(f"Failed to convert '{track['title']}' to WAV: {e}")

        self.logger.info(f"Finished converting {len(wav_file_paths)} MP3s to WAV.")
        return wav_file_paths

    def _execute_burn(self, wav_file_paths, disc_title="Audio CD"):
        """
        Executes the cdrecord command to burn the WAV files to an audio CD.
        """
        if not self.current_burner_device:
            raise RuntimeError("No CD burner device selected or detected.")
        if not wav_file_paths:
            raise ValueError("No WAV files provided for burning.")

        self.logger.info(f"Starting actual CD burning process to device {self.current_burner_device}...")
        CD_BURN_STATUS_MANAGER.update_status("Burning Disc...", progress=50) # Burning starts at 50% progress

        # Basic cdrecord command for audio CD
        # -v: verbose
        # dev={device}: specifies the burner device
        # speed=X: burning speed (optional, adjust as needed, e.g., 8, 16, 24)
        # -audio: specifies burning an audio CD
        # driveropts=burnfree: helps prevent buffer underruns
        # track*.wav: list of WAV files in order
        command = [
            self.cdrecord_path,
            '-v',
            f'dev={self.current_burner_device}',
            'speed=16', # You can make this configurable or auto-detect based on disc/drive
            '-audio',
            'driveropts=burnfree',
            # You might need to add -tao (Track At Once) or -dao (Disc At Once) depending on preference
            # -dummy for dry run if needed
            # -volid <name> for disc title (though not typically for audio CDs)
            # You can also use -text for CD-TEXT if you want to add track/artist info (requires more setup)
        ] + wav_file_paths

        try:
            # Execute the command, monitoring output for progress
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Redirect stderr to stdout for easier parsing
                text=True,
                encoding='utf-8',
                bufsize=1 # Line-buffered output
            )

            # This loop attempts to parse progress from cdrecord output
            # cdrecord's output format can vary, so this might need tuning.
            # Look for lines like "Track X: 95.00% done"
            for line in process.stdout:
                line = line.strip()
                self.logger.debug(f"cdrecord output: {line}")
                if "percent done" in line:
                    try:
                        # Example: "Track 1: 95.00% done"
                        match = re.search(r'(\d+\.\d+)% done', line)
                        if match:
                            burn_progress = float(match.group(1))
                            # Scale burn progress (0-100) to overall progress (50-100)
                            total_progress = 50 + (burn_progress / 100) * 50
                            CD_BURN_STATUS_MANAGER.update_status(f"Burning: {line}", int(total_progress))
                    except ValueError:
                        self.logger.warning(f"Could not parse progress from line: {line}")
                elif "writing" in line and "blocks" in line:
                    # General writing status
                    CD_BURN_STATUS_MANAGER.update_status(f"Burning: {line}")
                elif "fatal error" in line or "error" in line:
                    # Catch critical errors early
                    raise RuntimeError(f"cdrecord reported error: {line}")

            process.wait() # Wait for the process to finish

            if process.returncode != 0:
                raise RuntimeError(f"CD record command failed with exit code {process.returncode}.")

            self.logger.info("CD burning command completed successfully.")
            CD_BURN_STATUS_MANAGER.update_status("Burning Completed", progress=100)

        except Exception as e:
            self.logger.exception(f"Error during CD burning execution: {e}")
            raise RuntimeError(f"CD burning failed: {e}")

    def _cleanup_temp_dir(self, temp_dir):
        """Removes the temporary directory and its contents."""
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except OSError as e:
                self.logger.error(f"Error removing temporary directory {temp_dir}: {e}")

    def burn_cd(self, content_dir, item_title):
        """
        Orchestrates the entire CD burning process.
        This method is called in a separate thread.
        """
        temp_wav_dir = None
        try:
            self.logger.info(f"Starting CD burn process for content in: {content_dir}")
            CD_BURN_STATUS_MANAGER.start_burn(status=f"Preparing to burn '{item_title}'...", progress=0)

            # 1. Check burner and disc status again (redundant but safe)
            if not self.scan_for_burner():
                raise RuntimeError("No CD burner found. Aborting burn.")
            if not self.check_disc_status():
                raise RuntimeError("No blank or erasable disc found in burner. Aborting burn.")

            # 2. Parse Spotify metadata
            tracks_data = self._parse_spotify_metadata(content_dir)
            self.logger.info(f"Parsed {len(tracks_data)} tracks from metadata.")

            # 3. Create temporary directory for WAV files
            temp_wav_dir = tempfile.mkdtemp(prefix='cd_burn_wavs_')
            self.logger.info(f"Created temporary WAV directory: {temp_wav_dir}")

            # 4. Convert MP3s to WAVs
            CD_BURN_STATUS_MANAGER.update_status("Converting MP3s to WAVs...", progress=0)
            wav_file_paths = self._convert_mp3_to_wav(content_dir, tracks_data, temp_wav_dir)
            if not wav_file_paths:
                raise RuntimeError("No WAV files were successfully converted for burning.")

            # 5. Execute the CD burning command
            CD_BURN_STATUS_MANAGER.update_status("Initiating CD burn...", progress=50)
            self._execute_burn(wav_file_paths, disc_title=item_title)

            CD_BURN_STATUS_MANAGER.complete_burn()

        except FileNotFoundError as e:
            self.logger.error(f"Required file not found: {e}")
            CD_BURN_STATUS_MANAGER.set_error(f"File Error: {e}")
        except ValueError as e:
            self.logger.error(f"Data parsing error: {e}")
            CD_BURN_STATUS_MANAGER.set_error(f"Data Error: {e}")
        except RuntimeError as e:
            # Catch errors from subprocess or internal logic failures
            self.logger.error(f"CD burning process failed: {e}")
            CD_BURN_STATUS_MANAGER.set_error(f"Burning Failed: {e}")
        except Exception as e:
            # Catch any other unexpected errors
            self.logger.exception("An unhandled error occurred during CD burning.")
            CD_BURN_STATUS_MANAGER.set_error(f"Unexpected Error: {str(e)}")
        finally:
            # Always attempt to clean up temporary WAV directory
            if temp_wav_dir:
                self._cleanup_temp_dir(temp_wav_dir)
            # Ensure is_burning is reset even on unexpected exits
            if CD_BURN_STATUS_MANAGER.is_burning():
                CD_BURN_STATUS_MANAGER.complete_burn() # Or set to error if it wasn't already


# You might want to call scan_for_burner and check_disc_status periodically
# in your frontend or from a Flask background task if you want
# the initial status displayed on the page to be up-to-date
# before a burn request is even made.
# For simplicity, we can also call it on initial page load from the frontend
# and/or immediately before a burn attempt.