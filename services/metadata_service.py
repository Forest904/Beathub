# services/metadata_service.py

import json # Import json for serialization
import dataclasses # Import dataclasses for converting data classes

# Import models
from models.playlist import Playlist # Uncomment when models are ready
from models.track import Track # Uncomment when models are ready

# Assuming mutagen is used for applying metadata
# from mutagen.mp3 import MP3 # Example import
# from mutagen.id3 import ID3, TPE1, TIT2, TALB, TDRC, APIC # Example ID3 tags
# import requests # For downloading cover art

class MetadataService:
    """
    Handles serialization of Playlist/Track data to various formats (JSON, DB, etc.)
    and applying metadata (including cover art and lyrics) to downloaded files.
    """
    def __init__(self):
        print("MetadataService initialized.")
        pass

    def serialize_playlist_to_json(self, playlist: Playlist) -> str:
        """
        Serializes a Playlist object to a JSON string.

        Args:
            playlist: The Playlist object to serialize.

        Returns:
            A JSON string representation of the playlist.
        """
        print(f"MetadataService: Serializing playlist '{playlist.name}' to JSON.")
        # Implement JSON serialization
        try:
            # Convert the dataclass to a dictionary
            playlist_dict = dataclasses.asdict(playlist)
            # Serialize the dictionary to a JSON string
            json_string = json.dumps(playlist_dict, indent=4)
            return json_string
        except Exception as e:
            print(f"Error serializing playlist to JSON: {e}")
            return "{}" # Return empty JSON in case of error

    def apply_metadata_to_file(self, file_path: str, track: Track, cover_art_path: str | None = None):
        """
        Applies metadata from a Track object to a downloaded audio file.
        Optionally embeds cover art.

        Args:
            file_path: The path to the audio file.
            track: The Track object containing metadata.
            cover_art_path: The path to the cover art image file (optional).
        """
        print(f"MetadataService: Applying metadata for track '{track.title}' to file: {file_path}")
        # TODO: Implement metadata application using a library like mutagen
        # Example using mutagen (for MP3 files):
        # try:
        #     audio = MP3(file_path, ID3=ID3)
        #     audio.tags.add(TPE1(encoding=3, text=track.artists)) # Artist
        #     audio.tags.add(TIT2(encoding=3, text=track.title)) # Title
        #     if track.album:
        #         audio.tags.add(TALB(encoding=3, text=track.album)) # Album
        #     if track.duration_ms:
        #         audio.tags.add(TDRC(encoding=3, text=str(track.duration_ms // 1000))) # Duration in seconds

        #     # Embed cover art if path is provided
        #     if cover_art_path and os.path.exists(cover_art_path):
        #         with open(cover_art_path, 'rb') as f:
        #             audio.tags.add(APIC(
        #                 encoding=3, # 3 is UTF-8
        #                 mime='image/jpeg', # Adjust mime type based on image file
        #                 type=3, # 3 is for front cover
        #                 desc='Cover',
        #                 data=f.read()
        #             ))

        #     # TODO: Implement lyrics embedding if spotdl provides them or you fetch them
        #     # Example (requires a lyrics tag, e.g., USLT for unsynchronized lyrics):
        #     # if track.lyrics:
        #     #     audio.tags.add(USLT(encoding=3, lang='eng', desc='Lyrics', text=track.lyrics))


        #     audio.save()
        #     print(f"Metadata successfully applied to {file_path}")
        # except Exception as e:
        #     print(f"Error applying metadata to {file_path}: {e}")

        print("MetadataService: Placeholder metadata application.")
        pass # Placeholder

