import os
import re
import logging

from config import Config

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self, base_output_dir=None):
        """Initializes the FileManager.

        :param base_output_dir: The base directory for all downloads.
        """
        self.base_output_dir = base_output_dir or Config.BASE_OUTPUT_DIR
        os.makedirs(self.base_output_dir, exist_ok=True)
        logger.info(f"FileManager initialized with base output directory: {self.base_output_dir}")

    def sanitize_filename(self, name):
        """
        Sanitizes a string to be used as a filename or directory name.
        """
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        name = name.strip()
        name = re.sub(r'_{2,}', '_', name)
        return name

    def create_item_output_directory(self, artist_name, item_title):
        #Creates a dedicated output directory for a specific Spotify item (album, track, playlist).
        sanitized_artist = self.sanitize_filename(artist_name)
        sanitized_title = self.sanitize_filename(item_title)
        
        item_specific_output_dir = os.path.join(
            self.base_output_dir,
            f"{sanitized_artist} - {sanitized_title}"
        )

        try:
            os.makedirs(item_specific_output_dir, exist_ok=True)
            logger.info(f"Ensured output directory exists: {item_specific_output_dir}")
            return item_specific_output_dir
        except OSError as e:
            logger.error(f"Could not create directory {item_specific_output_dir}: {e}")
            return None

    def save_metadata_json(self, output_dir, metadata):
        #Saves metadata as a JSON file in the specified directory.
        metadata_json_path = os.path.join(output_dir, "spotify_metadata.json")
        try:
            with open(metadata_json_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(metadata, f, ensure_ascii=False, indent=4)
            logger.info(f"Spotify metadata saved to {metadata_json_path}")
            return metadata_json_path
        except IOError as e:
            logger.error(f"Failed to save Spotify metadata to JSON at {metadata_json_path}: {e}")
            return None

    def cleanup_partial_output(self, output_dir: str) -> None:
        """Attempt best-effort cleanup of temporary/incomplete artifacts.

        - Removes files with common temporary extensions ('.part', '.tmp')
        - Removes SpotDL temp directories if present
        - Removes zero-length files
        - Removes the directory if it becomes empty
        """
        try:
            if not output_dir or not os.path.isdir(output_dir):
                return
            removed_any = False
            for root, dirs, files in os.walk(output_dir, topdown=False):
                # Remove SpotDL temporary directories if any conventional names are present
                for d in list(dirs):
                    dn = d.lower()
                    if dn.startswith('.spotdl') or 'spotdl-temp' in dn:
                        full = os.path.join(root, d)
                        try:
                            import shutil
                            shutil.rmtree(full, ignore_errors=True)
                            removed_any = True
                        except Exception:
                            pass
                for f in files:
                    full = os.path.join(root, f)
                    fl = f.lower()
                    try:
                        # Remove temp/partial/zero-length files
                        if fl.endswith('.part') or fl.endswith('.tmp'):
                            os.remove(full)
                            removed_any = True
                            continue
                        try:
                            if os.path.getsize(full) == 0:
                                os.remove(full)
                                removed_any = True
                        except Exception:
                            pass
                    except Exception:
                        pass
                # Attempt to remove empty directories bottom-up
                try:
                    if not os.listdir(root):
                        os.rmdir(root)
                        removed_any = True
                except Exception:
                    pass
            if removed_any:
                logger.info(f"Cleaned up temporary artifacts under {output_dir}")
        except Exception as e:
            logger.debug(f"Cleanup skipped due to error: {e}", exc_info=True)
