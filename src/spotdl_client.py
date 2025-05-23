# spotdl_client.py
import subprocess
import tempfile
import shutil
import json
import logging
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SpotDLClient:
    def __init__(self):
        logger.info("SpotDLClient initialized.")

    def _run_spotdl_command(self, command: List[str], cwd: str | None = None) -> subprocess.CompletedProcess:
        """Helper to run a spotdl command and handle common errors."""
        full_command = ['spotdl'] + command
        logger.info(f"Executing spotdl command: {' '.join(full_command)}")
        try:
            process = subprocess.run(
                full_command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"--- spotdl stdout ---\n{process.stdout}")
            logger.debug(f"--- spotdl stderr ---\n{process.stderr}")
            return process
        except FileNotFoundError:
            logger.error("Error: 'spotdl' command not found. Is spotdl installed and in your PATH?")
            logger.info("Install spotdl using: pip install spotdl")
            raise RuntimeError("SpotDL not found. Please install it: pip install spotdl")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running spotdl subprocess: {e}")
            logger.error(f"Command: {' '.join(e.cmd)}")
            logger.error(f"Stderr: {e.stderr}")
            logger.error(f"Stdout: {e.stdout}")
            raise RuntimeError(f"SpotDL command failed: {e.stderr or e.stdout}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while running spotdl: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred during spotdl operation: {e}")

    def save_metadata(self, spotify_link: str) -> Dict[str, Any] | None:
        """
        Runs the 'spotdl save' command to get metadata in JSON format.
        Returns the parsed JSON metadata.
        """
        logger.info(f"Running spotdl save for: {spotify_link}")
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            output_filename = "metadata.spotdl"
            output_file_path = os.path.join(temp_dir, output_filename)

            command = [
                'save',
                spotify_link,
                '--save-file', output_filename,
                '--log-level', 'ERROR' # spotdl's internal log level
            ]
            self._run_spotdl_command(command, cwd=temp_dir)

            if os.path.exists(output_file_path):
                with open(output_file_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                return metadata
            else:
                logger.error(f"Error: spotdl did not create the expected output file at {output_file_path}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from spotdl output file {output_file_path}: {e}")
            raise RuntimeError(f"Failed to parse spotdl metadata: {e}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")

    def download_item(self, spotify_link: str, output_dir: str) -> bool:
        """
        Runs the 'spotdl download' command to download the Spotify item.
        """
        logger.info(f"Running spotdl download for: {spotify_link} into {output_dir}")
        command = [
            'download',
            spotify_link,
            '--output', os.path.join(output_dir, '{title} - {artist}.{ext}'),
            '--log-level', 'INFO' # spotdl's internal log level
        ]
        try:
            self._run_spotdl_command(command)
            logger.info(f"spotdl download successful for {spotify_link}.")
            return True
        except RuntimeError as e:
            logger.error(f"SpotDL download failed: {e}")
            return False

