"""Shared test stubs for SpotDL and Spotipy interfaces."""

import sys
import types
from pathlib import Path
from typing import Iterable, Optional, Sequence


def install_spotdl_song_stub(reset: bool = True):
    """Install a minimal spotdl song stub so modules can import it safely."""
    if reset:
        for name in ("spotdl.types.song", "spotdl.types", "spotdl"):
            sys.modules.pop(name, None)

    m_spotdl = types.ModuleType("spotdl")
    m_types = types.ModuleType("spotdl.types")
    m_song = types.ModuleType("spotdl.types.song")

    class Song:
        def __init__(self, json_dict):
            self._json = json_dict
            self.artist = (json_dict.get("artists") or ["Unknown"])[0]
            self.album_name = json_dict.get("album_name")
            self.name = json_dict.get("name")
            self.cover_url = json_dict.get("cover_url")
            self.song_id = json_dict.get("song_id")
            self.album_id = json_dict.get("album_id")
            self.url = json_dict.get("url")

        @property
        def json(self):
            return self._json

    m_song.Song = Song
    sys.modules["spotdl"] = m_spotdl
    sys.modules["spotdl.types"] = m_types
    sys.modules["spotdl.types.song"] = m_song
    return Song


def install_spotdl_options_stub(reset: bool = False):
    """Provide spotdl.types.options.DownloaderOptionalOptions stub."""
    if reset:
        for name in ("spotdl.types.options", "spotdl.types", "spotdl"):
            sys.modules.pop(name, None)

    m_spotdl = sys.modules.get("spotdl") or types.ModuleType("spotdl")
    m_types = sys.modules.get("spotdl.types") or types.ModuleType("spotdl.types")
    m_options = types.ModuleType("spotdl.types.options")

    class DownloaderOptionalOptions(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    m_options.DownloaderOptionalOptions = DownloaderOptionalOptions
    sys.modules["spotdl"] = m_spotdl
    sys.modules["spotdl.types"] = m_types
    sys.modules["spotdl.types.options"] = m_options
    return DownloaderOptionalOptions



def install_spotdl_module_stub(print_on_download: bool = False):
    """Install a stub spotdl module exposing the Spotdl class used by the client."""
    install_spotdl_options_stub()

    m_spotdl = types.ModuleType("spotdl")
    m_types = sys.modules.get("spotdl.types") or types.ModuleType("spotdl.types")

    class DummyProgressHandler:
        def __init__(self):
            self.update_callback = None
            self.web_ui = False

    class DummyDownloader:
        def __init__(self):
            self.settings = {"output": None}
            self.progress_handler = DummyProgressHandler()

    class DummySong:
        def __init__(self, display_name: str = "Song"):
            self.display_name = display_name

    class DummySpotdl:
        def __init__(self, client_id=None, client_secret=None, downloader_settings=None):
            self.downloader = DummyDownloader()
            self._songs = [DummySong("A"), DummySong("B")]

        def search(self, queries):
            return self._songs

        def download_songs(self, songs):
            if print_on_download:
                print("ENGINE: start")
                print("ENGINE: progress 50%")
            return [(s, Path(f"/tmp/{s.display_name}.mp3")) for s in songs]

    m_spotdl.Spotdl = DummySpotdl
    sys.modules["spotdl"] = m_spotdl
    sys.modules["spotdl.types"] = m_types
    return m_spotdl
class SpotDLClientStub:
    """Simplified SpotDL client covering the behaviour tests rely on."""

    def __init__(self, base_dir: Path, songs: Optional[Sequence[dict]] = None):
        self.base_dir = Path(base_dir)
        self._songs_data = list(songs or [])
        self._callback = None
        self.output_template = None

    def set_output_template(self, template: str):
        self.output_template = template
        return template

    def set_progress_callback(self, callback, web_ui: bool = False):
        self._callback = callback

    def clear_progress_callback(self):
        self._callback = None

    def search(self, queries: Iterable[str]):
        song_cls = sys.modules["spotdl.types.song"].Song
        return [song_cls(data) if not hasattr(data, "json") else data for data in self._songs_data]

    def download_songs(self, songs):
        results = []
        for song in songs:
            name = song.json.get("name") or song.json.get("title") or "track"
            target = self.base_dir / f"{name}.mp3"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"stub-audio")
            results.append((song, target))
            if self._callback:
                parent = types.SimpleNamespace(overall_completed_tasks=1, song_count=len(songs), overall_progress=50)
                tracker = types.SimpleNamespace(song_name=name, progress=10, parent=parent)
                self._callback(tracker, "Downloading")
        return results

    def download_link(self, link: str, output_template: str, progress_callback=None):
        if progress_callback:
            self.set_progress_callback(progress_callback)
        songs = self.search([link])
        return self.download_songs(songs)


class SpotipySearchStub:
    """Minimal Spotipy client stub for route tests."""

    def __init__(self, response: Optional[dict] = None, error: Optional[Exception] = None):
        self.response = response or {"artists": {"items": []}}
        self.error = error

    def search(self, *args, **kwargs):
        if self.error:
            raise self.error
        return self.response
