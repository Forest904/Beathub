import sys
import types
from pathlib import Path

import pytest


def _install_spotdl_stubs():
    """Install minimal stub modules for 'spotdl' to satisfy SpotdlClient."""
    # spotdl module with Spotdl class
    m_spotdl = types.ModuleType("spotdl")

    class DummyProgressHandler:
        def __init__(self):
            self.update_callback = None
            self.web_ui = False

    class DummyDownloader:
        def __init__(self):
            self.settings = {"output": None, "lyrics_providers": ["genius"]}
            self.progress_handler = DummyProgressHandler()

    class DummySong:
        def __init__(self, display_name: str = "Song A"):
            self.display_name = display_name

    class DummySpotdl:
        def __init__(self, client_id=None, client_secret=None, downloader_settings=None):
            self.downloader = DummyDownloader()
            self._songs = [DummySong("Song A"), DummySong("Song B")]

        def search(self, queries):
            return self._songs

        def download_songs(self, songs):
            # Return tuples (song, path)
            return [(s, Path(f"/tmp/{s.display_name}.mp3")) for s in songs]

    m_spotdl.Spotdl = DummySpotdl
    sys.modules["spotdl"] = m_spotdl


def test_spotdl_client_basic_flow(monkeypatch):
    _install_spotdl_stubs()

    # Now import the client under test
    from src.spotdl_client import SpotdlClient

    cli = SpotdlClient(client_id="id", client_secret="secret", downloader_options={})

    # Setting template updates downloader settings
    effective = cli.set_output_template("{title}.{ext}")
    assert effective == "{title}.{ext}"
    assert cli.spotdl.downloader.settings["output"] == "{title}.{ext}"

    # Progress callback wrapping produces a dict and invokes our function
    events = []

    def cb(ev: dict):
        events.append(ev)

    cli.set_progress_callback(cb, web_ui=True)

    # Simulate progress update through the wrapped handler
    ph = cli.spotdl.downloader.progress_handler
    assert callable(ph.update_callback)
    assert ph.web_ui is True
    ph.update_callback(type("T", (), {"song_name": "Song A", "progress": 42, "parent": type("P", (), {"overall_completed_tasks": 1, "song_count": 2, "overall_progress": 50})()})(), "Downloading")

    assert events, "Expected at least one progress event"
    assert events[-1]["song_display_name"] == "Song A"
    assert events[-1]["progress"] == 42

    # Download link convenience path (calls search + download)
    results = cli.download_link("https://open.spotify.com/track/xyz", "{title}.{ext}")
    assert len(results) == 2
    assert str(results[0][1]).endswith("Song A.mp3")

    # Clearing callback detaches handler
    cli.clear_progress_callback()
    assert ph.update_callback is None
