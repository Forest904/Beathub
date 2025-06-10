import os
import json
import logging
import subprocess
import re
import tempfile
import shutil
import threading

# Ensure pydub and its dependencies (like ffmpeg) are installed
from pydub import AudioSegment

# Initialize logger for this service module.
# Instance-specific loggers will be used within CDBurningService.
module_logger = logging.getLogger(__name__)

# --- Global CD Burning Status Manager (Singleton-like) ---
# This class manages the state of the CD burning process,
# allowing the Flask routes to poll for updates.
class CDBurnStatusManager:
    _instance = None
    _status_lock = threading.Lock() # To ensure thread-safe updates

    def __new__(cls):
        """Ensures only one instance of the status manager exists."""
        if cls._instance is None:
            cls._instance = super(CDBurnStatusManager, cls).__new__(cls)
            # Initialize state only once when the instance is first created
            cls._instance._reset_status()
        return cls._instance

    def _reset_status(self):
        """Resets the internal status variables of the manager."""
        with self._status_lock:
            self._is_burning = False
            self._current_status = 'Idle' # States: 'Idle', 'Scanning Burner', 'Burner Ready', 'No Burner', 'Disc Check', 'Disc Ready', 'No Disc', 'Converting WAVs', 'Burning Disc', 'Completed', 'Error'
            self._progress_percentage = 0 # 0-100
            self._last_error = None
            self._burner_detected = False
            self._disc_present = False
            self._disc_blank_or_erasable = False # True if disc is blank or can be overwritten

    def get_status(self):
        """Returns the current status of the CD burning process."""
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
        """Sets the status manager to indicate a burn is starting."""
        with self._status_lock:
            self._is_burning = True
            self._current_status = status
            self._progress_percentage = progress
            self._last_error = None
            module_logger.info(f"CD Burn Process Initiated. Status: {status}")

    def update_status(self, status, progress=None):
        """Updates the current status and optionally progress of the burn."""
        with self._status_lock:
            self._current_status = status
            if progress is not None:
                self._progress_percentage = progress
            module_logger.info(f"CD Burn Status: {self._current_status} (Progress: {self._progress_percentage}%)")

    def set_error(self, message):
        """Sets an error state for the burn process."""
        with self._status_lock:
            self._is_burning = False
            self._current_status = 'Error'
            self._last_error = message
            module_logger.error(f"CD Burn Error: {message}")

    def complete_burn(self):
        """Marks the CD burn process as completed successfully."""
        with self._status_lock:
            self._is_burning = False
            self._current_status = 'Completed'
            self._progress_percentage = 100
            self._last_error = None
            module_logger.info("CD Burn Completed Successfully.")

    def is_burning(self):
        """Checks if a CD burning process is currently active."""
        with self._status_lock:
            return self._is_burning

    def update_burner_state(self, detected=False, present=False, blank_or_erasable=False):
        """Updates the detected state of the burner and disc."""
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
            module_logger.info(f"Burner State Updated: Detected={detected}, Present={present}, Blank/Erasable={blank_or_erasable}, Status='{self._current_status}'")


# Global instance of the status manager, initialized on import
CD_BURN_STATUS_MANAGER = CDBurnStatusManager()


class CDBurningService:
    def __init__(self, app_logger=None, base_output_dir=None):
        # Use the provided app_logger or create a new one for this instance
        self.logger = app_logger if app_logger else logging.getLogger(self.__class__.__name__)
        self.base_output_dir = base_output_dir
        # Ensure cdrecord/wodim and ffmpeg are in PATH or provide full path
        self.cdrecord_path = "cdrecord" # Or "wodim" on some Linux systems
        self.ffmpeg_path = "ffmpeg"    # pydub typically handles this, but good to note
        self.current_burner_device = None
        self.logger.info("CDBurningService initialized with cdrecord path: {}".format(self.cdrecord_path))

    def _run_command(self, command, description="", check=True):
        """Helper to run a subprocess command and log output, with improved error handling."""
        full_command_str = ' '.join(command)
        self.logger.info(f"Executing: {full_command_str} ({description})")
        process = None
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check,
                encoding='utf-8',
                errors='replace' # Handle potential encoding errors more gracefully
            )
            stdout = process.stdout.strip()
            stderr = process.stderr.strip()

            if stdout:
                self.logger.debug(f"Command '{full_command_str}' stdout: {stdout}")
            if stderr:
                self.logger.warning(f"Command '{full_command_str}' stderr: {stderr}") # Log stderr even if check=True

            return stdout
        except FileNotFoundError:
            error_msg = f"Command not found: '{command[0]}'. Make sure '{command[0]}' (e.g., cdrecord/wodim, ffmpeg) is installed and in your system's PATH."
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed with exit code {e.returncode}: {e.cmd}\nStdout: {e.stdout}\nStderr: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"An unexpected error occurred running command '{full_command_str}': {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        finally:
            # If the process was started and hasn't exited, attempt to terminate it
            if process and process.poll() is None:
                self.logger.warning(f"Attempting to terminate hung subprocess: {full_command_str}")
                process.terminate()
                process.wait(timeout=5) # Give it some time to terminate
                if process.poll() is None:
                    self.logger.error(f"Failed to terminate subprocess, killing: {full_command_str}")
                    process.kill()


    def scan_for_burner(self):
        """
        Scans for available CD/DVD burners using 'cdrecord -scanbus'.
        Updates the global status manager and sets self.current_burner_device.
        Returns True if a burner is found, False otherwise.
        """
        self.logger.info("Scanning for CD/DVD burners...")
        CD_BURN_STATUS_MANAGER.update_status("Scanning Burner...")
        try:
            # Using -scanbus to find devices. Output format can vary by OS/cdrecord version.
            command = [self.cdrecord_path, '-scanbus']
            # We set check=False because -scanbus might exit with a non-zero code if no burner is found
            output = self._run_command(command, "scanning for burners", check=False)

            # Regex to find burner device: 'bus,target,lun' format
            # Example output: "scsibus0: 0,0,0   0) 'VENDOR' 'PRODUCT' 'REVISION' Removable CD-ROM"
            # This regex is an improvement over the original by being more specific.
            burner_match = re.search(r'^\s*(\d+,\d+,\d+)\s+\d+\)\s+\'(.+?)\'\s+\'(.+?)\'\s+\'(.+?)\'\s+Removable CD-ROM', output, re.MULTILINE)

            if burner_match:
                self.current_burner_device = burner_match.group(1)
                self.logger.info(f"CD burner detected at device: {self.current_burner_device} ({burner_match.group(2)} {burner_match.group(3)})")
                CD_BURN_STATUS_MANAGER.update_burner_state(detected=True)
                return True
            else:
                self.logger.warning("No CD/DVD burner found on system or output format not recognized.")
                CD_BURN_STATUS_MANAGER.update_burner_state(detected=False)
                return False
        except RuntimeError as e:
            # Catch errors propagated from _run_command
            self.logger.error(f"Runtime error during burner scan: {e}")
            CD_BURN_STATUS_MANAGER.update_burner_state(detected=False)
            CD_BURN_STATUS_MANAGER.set_error(f"Burner scan failed: {e}")
            return False
        except Exception as e:
            self.logger.exception("An unexpected error occurred during burner scan.")
            CD_BURN_STATUS_MANAGER.update_burner_state(detected=False)
            CD_BURN_STATUS_MANAGER.set_error(f"Burner scan failed unexpectedly: {e}")
            return False

    def check_disc_status(self):
        """
        Checks the status of the disc in the detected burner using 'cdrecord -checkmedia'.
        Updates the global status manager.
        Returns True if a blank/erasable disc is present, False otherwise.
        """
        if not self.current_burner_device:
            self.logger.warning("No burner detected to check disc status. Please run scan_for_burner first.")
            CD_BURN_STATUS_MANAGER.update_burner_state(detected=False) # Ensure consistent state
            return False

        self.logger.info(f"Checking disc status in burner {self.current_burner_device}...")
        CD_BURN_STATUS_MANAGER.update_status("Checking Disc...")
        try:
            command = [self.cdrecord_path, '-v', f'dev={self.current_burner_device}', '-checkmedia']
            output = self._run_command(command, "checking disc status", check=False) # check=False as it might exit non-zero for empty tray

            disc_present = "Disc present" in output or "Track 1" in output or "Media tag:" in output
            # Look for indicators of blank/erasable media
            blank_or_erasable = (
                "Disc status: blank" in output or
                "Disc status: empty" in output or
                "appendable" in output or
                "overwriteable" in output or
                "CD-RW" in output # Implies erasable
            )

            CD_BURN_STATUS_MANAGER.update_burner_state(
                detected=True, # Assumed to be True if we have a current_burner_device
                present=disc_present,
                blank_or_erasable=blank_or_erasable
            )
            return disc_present and blank_or_erasable

        except RuntimeError as e:
            self.logger.error(f"Runtime error checking disc status: {e}")
            CD_BURN_STATUS_MANAGER.update_burner_state(detected=True, present=False, blank_or_erasable=False)
            CD_BURN_STATUS_MANAGER.set_error(f"Disc status check failed: {e}")
            return False
        except Exception as e:
            self.logger.exception("An unexpected error occurred during disc status check.")
            CD_BURN_STATUS_MANAGER.update_burner_state(detected=True, present=False, blank_or_erasable=False)
            CD_BURN_STATUS_MANAGER.set_error(f"Disc status check failed unexpectedly: {e}")
            return False

    def _parse_spotify_metadata(self, content_dir):
        """
        Parses the spotify_metadata.json file to get track order and titles.
        Returns a list of dictionaries, each containing 'title' and 'artist' for a track.
        """
        metadata_path = os.path.join(content_dir, "spotify_metadata.json")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"spotify_metadata.json not found in {content_dir}")

        self.logger.info(f"Parsing spotify_metadata.json from {metadata_path}")
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        tracks_data = []
        # Handle different Spotify item types (album, playlist, track)
        if 'tracks' in metadata and 'items' in metadata['tracks']: # Album or Playlist
            for item in metadata['tracks']['items']:
                track_info = item.get('track') if item.get('track') else item # Handle playlist vs album item structure
                if track_info:
                    tracks_data.append({
                        'title': track_info.get('name'),
                        'artist': track_info.get('artists')[0]['name'] if track_info.get('artists') else 'Unknown Artist'
                    })
        elif metadata.get('type') == 'track': # Single track
            tracks_data.append({
                'title': metadata.get('name'),
                'artist': metadata.get('artists')[0]['name'] if metadata.get('artists') else 'Unknown Artist'
            })
        else:
            raise ValueError("Unsupported spotify_metadata.json format. Expected album/playlist or single track.")

        if not tracks_data:
            raise ValueError("No tracks found in spotify_metadata.json to burn.")

        self.logger.info(f"Found {len(tracks_data)} tracks in metadata.")
        return tracks_data

    def _convert_mp3_to_wav(self, content_dir, tracks_data, temp_wav_dir):
        """
        Converts MP3 files to WAV format in the specified temporary directory.
        Ensures 44.1 kHz, 16-bit, stereo for audio CD compatibility.
        Returns a list of paths to the converted WAV files, in the correct order.
        """
        self.logger.info(f"Starting MP3 to WAV conversion for {len(tracks_data)} tracks in {content_dir}...")
        wav_file_paths = []
        total_tracks = len(tracks_data)

        # Ensure ffmpeg/libav is accessible by pydub.
        # pydub.AudioSegment.ffmpeg = self.ffmpeg_path # Can explicitly set if needed

        for i, track in enumerate(tracks_data):
            # Sanitize track title for filename matching. This should mirror the download logic.
            # Replace invalid filename characters
            sanitized_title = re.sub(r'[\\/:*?"<>|]', '_', track['title'])
            sanitized_title = sanitized_title.strip()
            # Replace multiple underscores with a single one
            sanitized_title = re.sub(r'_{2,}', '_', sanitized_title)
            # This pattern attempts to match files named after the sanitized title
            mp3_file_name_pattern = f"{re.escape(sanitized_title)}\.mp3"
            found_mp3_path = None

            # Search for the MP3 file in the content_dir
            for f_name in os.listdir(content_dir):
                if re.fullmatch(mp3_file_name_pattern, f_name, re.IGNORECASE):
                    found_mp3_path = os.path.join(content_dir, f_name)
                    break

            # Fallback for "Artist - Title.mp3" format if initial match fails
            if not found_mp3_path:
                fallback_name_pattern = f"{re.escape(track['artist'])} - {re.escape(sanitized_title)}\.mp3"
                for f_name in os.listdir(content_dir):
                    if re.fullmatch(fallback_name_pattern, f_name, re.IGNORECASE):
                        found_mp3_path = os.path.join(content_dir, f_name)
                        break

            if not found_mp3_path:
                error_msg = f"MP3 file not found for track: '{track['title']}' (expected: {sanitized_title}.mp3 or {track['artist']} - {sanitized_title}.mp3). Aborting conversion."
                self.logger.error(error_msg)
                CD_BURN_STATUS_MANAGER.set_error(error_msg)
                raise FileNotFoundError(error_msg)

            # Prefix with number for correct burning order
            wav_output_path = os.path.join(temp_wav_dir, f"{i+1:02d}_{sanitized_title}.wav")

            try:
                self.logger.info(f"Converting '{os.path.basename(found_mp3_path)}' to WAV...")
                audio = AudioSegment.from_mp3(found_mp3_path)
                # Ensure 44.1 kHz, 16-bit, stereo for audio CD compatibility
                audio = audio.set_frame_rate(44100).set_channels(2).set_sample_width(2)
                audio.export(wav_output_path, format="wav")
                wav_file_paths.append(wav_output_path)
                # Conversion takes up 50% of overall progress (0-50%)
                progress = int(((i + 1) / total_tracks) * 50)
                CD_BURN_STATUS_MANAGER.update_status(f"Converting WAVs ({i+1}/{total_tracks})", progress)
            except Exception as e:
                self.logger.exception(f"Error converting MP3 '{found_mp3_path}' to WAV: {e}")
                raise RuntimeError(f"Failed to convert '{track['title']}' to WAV: {e}")

        self.logger.info(f"Finished converting {len(wav_file_paths)} MP3s to WAV.")
        return wav_file_paths

    def _execute_burn(self, wav_file_paths, disc_title="Audio CD"):
        """
        Executes the cdrecord command to burn the WAV files to an audio CD.
        Monitors output for progress updates.
        """
        if not self.current_burner_device:
            raise RuntimeError("No CD burner device selected or detected. Burn cannot proceed.")
        if not wav_file_paths:
            raise ValueError("No WAV files provided for burning. Burn cannot proceed.")

        self.logger.info(f"Starting actual CD burning process to device {self.current_burner_device} with title '{disc_title}'...")
        CD_BURN_STATUS_MANAGER.update_status("Burning Disc...", progress=50) # Burning progress (50-100%)

        # Basic cdrecord command for audio CD
        command = [
            self.cdrecord_path,
            '-v',              # Verbose output
            f'dev={self.current_burner_device}', # Specify the burner device
            'speed=16',        # Burning speed (adjust as needed or make configurable)
            '-audio',          # Specify burning an audio CD
            'driveropts=burnfree', # Helps prevent buffer underruns
            '-dao',            # Disc At Once mode (recommended for audio CDs)
            # Add -text or -text_us if you want CD-TEXT (requires more complex track info)
            # Add -dummy for a dry run (useful for testing without wasting a disc)
        ] + wav_file_paths # List of WAV files in order

        try:
            # Execute the command, capturing stdout/stderr for progress parsing
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Redirect stderr to stdout for easier parsing
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1 # Line-buffered output
            )

            # This loop attempts to parse progress from cdrecord output.
            # Note: cdrecord's output format can vary greatly across versions and OS,
            # so this parsing might need fine-tuning for your specific environment.
            for line in process.stdout:
                line = line.strip()
                self.logger.debug(f"cdrecord output: {line}")

                if "percent done" in line:
                    try:
                        # Example: "Track 1: 95.00% done"
                        match = re.search(r'(\d+\.?\d*)%\s+done', line)
                        if match:
                            burn_progress = float(match.group(1))
                            # Scale burn progress (0-100) to overall progress (50-100)
                            total_progress = 50 + (burn_progress / 100) * 50
                            CD_BURN_STATUS_MANAGER.update_status(f"Burning: {line}", int(total_progress))
                    except ValueError:
                        self.logger.warning(f"Could not parse progress percentage from line: {line}")
                elif "writing" in line and "blocks" in line:
                    # General writing status update
                    CD_BURN_STATUS_MANAGER.update_status(f"Burning: {line}")
                elif "fatal error" in line or "error" in line:
                    # Catch critical errors reported in output
                    raise RuntimeError(f"cdrecord reported error: {line}")

            # Wait for the subprocess to complete and check its return code
            process.wait()

            if process.returncode != 0:
                raise RuntimeError(f"CD record command failed with exit code {process.returncode}. Check logs for details.")

            self.logger.info("CD burning command completed successfully.")
            CD_BURN_STATUS_MANAGER.update_status("Burning Completed", progress=100)

        except Exception as e:
            self.logger.exception(f"Error during CD burning execution: {e}")
            raise RuntimeError(f"CD burning failed: {e}")
        finally:
            # Ensure process is truly terminated if an exception occurred during parsing
            if process and process.poll() is None:
                self.logger.warning(f"Terminating hanging cdrecord process.")
                process.terminate()
                process.wait(timeout=5)


    def _cleanup_temp_dir(self, temp_dir):
        """Removes the temporary directory and its contents, used for WAV files."""
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except OSError as e:
                self.logger.error(f"Error removing temporary directory {temp_dir}: {e}")

    def burn_cd(self, content_dir, item_title):
        """
        Orchestrates the entire CD burning process.
        This method is designed to be called in a separate thread.
        """
        temp_wav_dir = None
        try:
            self.logger.info(f"Starting CD burn process for content from: {content_dir}")
            CD_BURN_STATUS_MANAGER.start_burn(status=f"Preparing to burn '{item_title}'...", progress=0)

            # 1. Scan for burner and check disc status
            if not self.scan_for_burner():
                raise RuntimeError("No compatible CD burner found. Please ensure a burner is connected.")
            if not self.check_disc_status():
                raise RuntimeError("No blank or erasable disc found in the burner. Please insert a disc.")

            # 2. Parse Spotify metadata to get track order and details
            tracks_data = self._parse_spotify_metadata(content_dir)
            self.logger.info(f"Successfully parsed {len(tracks_data)} tracks from metadata.")

            # 3. Create a temporary directory for converted WAV files
            temp_wav_dir = tempfile.mkdtemp(prefix='cd_burn_wavs_')
            self.logger.info(f"Created temporary WAV directory: {temp_wav_dir}")

            # 4. Convert MP3s to WAVs suitable for audio CD
            CD_BURN_STATUS_MANAGER.update_status("Converting MP3s to WAVs...", progress=0)
            wav_file_paths = self._convert_mp3_to_wav(content_dir, tracks_data, temp_wav_dir)
            if not wav_file_paths:
                raise RuntimeError("No WAV files were successfully converted. Aborting burn.")

            # 5. Execute the actual CD burning command
            CD_BURN_STATUS_MANAGER.update_status("Initiating CD burn...", progress=50)
            self._execute_burn(wav_file_paths, disc_title=item_title)

            CD_BURN_STATUS_MANAGER.complete_burn()
            self.logger.info(f"CD burn for '{item_title}' completed successfully.")

        except (FileNotFoundError, ValueError, RuntimeError) as e:
            # Catch specific errors from internal methods
            self.logger.error(f"CD burning process failed due to: {e}")
            CD_BURN_STATUS_MANAGER.set_error(f"Burning Failed: {e}")
        except Exception as e:
            # Catch any other unexpected errors
            self.logger.exception("An unhandled error occurred during CD burning process.")
            CD_BURN_STATUS_MANAGER.set_error(f"Unexpected Error during burn: {str(e)}")
        finally:
            # Always attempt to clean up temporary WAV directory
            if temp_wav_dir:
                self._cleanup_temp_dir(temp_wav_dir)
            # Ensure is_burning is reset even if an exception occurs mid-process
            # Only reset if it's still marked as burning and not already set to error/completed
            if CD_BURN_STATUS_MANAGER.is_burning():
                CD_BURN_STATUS_MANAGER.set_error("Burn process interrupted or failed unexpectedly.")
