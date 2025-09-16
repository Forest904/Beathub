from pathlib import Path

import pytest

from tests.support.stubs import install_spotdl_module_stub


@pytest.mark.unit
def test_spotdl_client_basic_flow(monkeypatch):
    install_spotdl_module_stub()

    from src.spotdl_client import SpotdlClient

    cli = SpotdlClient(client_id="id", client_secret="secret", downloader_options={})

    effective = cli.set_output_template("{title}.{ext}")
    assert effective == "{title}.{ext}"
    assert cli.spotdl.downloader.settings["output"] == "{title}.{ext}"

    events = []

    def cb(ev: dict):
        events.append(ev)

    cli.set_progress_callback(cb, web_ui=True)

    ph = cli.spotdl.downloader.progress_handler
    assert callable(ph.update_callback)
    assert ph.web_ui is True
    parent = type("P", (), {"overall_completed_tasks": 1, "song_count": 2, "overall_progress": 50})()
    tracker = type("T", (), {"song_name": "Song A", "progress": 42, "parent": parent})()
    ph.update_callback(tracker, "Downloading")

    assert events, "Expected at least one progress event"
    assert events[-1]["song_display_name"] == "Song A"
    assert events[-1]["progress"] == 42

    results = cli.download_link("https://open.spotify.com/track/xyz", "{title}.{ext}")
    assert len(results) == 2
    assert isinstance(results[0][1], Path)
    assert str(results[0][1]).endswith("A.mp3") or str(results[0][1]).endswith("Song A.mp3")

    cli.clear_progress_callback()
    assert ph.update_callback is None
