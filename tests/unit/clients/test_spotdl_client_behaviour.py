import sys
import types

import pytest

from tests.support.stubs import install_spotdl_module_stub


@pytest.mark.unit
def test_engine_init_failure_without_spotdl_class(monkeypatch):
    for k in list(sys.modules.keys()):
        if k == "spotdl" or k.startswith("spotdl."):
            monkeypatch.delitem(sys.modules, k, raising=False)
    monkeypatch.setitem(sys.modules, "spotdl", types.ModuleType("spotdl"))

    from src.spotdl_client import SpotdlClient

    with pytest.raises(RuntimeError, match="Failed to initialize SpotDL engine thread"):
        SpotdlClient(client_id="id", client_secret="sec", downloader_options={})


@pytest.mark.unit
def test_set_output_template_and_clear_progress_callback():
    install_spotdl_module_stub()
    from src.spotdl_client import SpotdlClient

    cli = SpotdlClient(client_id="id", client_secret="sec", downloader_options={})

    eff = cli.set_output_template("{artist}-{title}.{ext}")
    assert eff == "{artist}-{title}.{ext}"
    assert cli.spotdl.downloader.settings["output"] == "{artist}-{title}.{ext}"

    events = []

    def cb(ev: dict):
        events.append(ev)

    cli.set_progress_callback(cb, web_ui=True)
    ph = cli.spotdl.downloader.progress_handler
    assert ph.web_ui is True
    assert callable(ph.update_callback)

    cli.clear_progress_callback()
    assert cli.spotdl.downloader.progress_handler.update_callback is None


@pytest.mark.unit
def test_progress_callback_wrapper_handles_exceptions():
    install_spotdl_module_stub()
    from src.spotdl_client import SpotdlClient

    cli = SpotdlClient(client_id="id", client_secret="sec", downloader_options={})

    def raising_cb(ev: dict):
        raise RuntimeError("boom")

    cli.set_progress_callback(raising_cb, web_ui=True)
    ph = cli.spotdl.downloader.progress_handler

    Parent = type("P", (), {"overall_completed_tasks": 1, "song_count": 2, "overall_progress": 50})
    Tracker = type("T", (), {"song_name": "S", "progress": 42, "parent": Parent()})

    ph.update_callback(Tracker(), "Downloading")


@pytest.mark.unit
def test_download_songs_silences_stdout(capsys):
    install_spotdl_module_stub(print_on_download=True)
    from src.spotdl_client import SpotdlClient

    cli = SpotdlClient(client_id="id", client_secret="sec", downloader_options={})
    songs = cli.search(["https://open.spotify.com/track/xyz"])

    res = cli.download_songs(songs)
    out, err = capsys.readouterr()

    assert "ENGINE:" not in out
    assert len(res) == 2
    assert str(res[0][1]).endswith("A.mp3")


@pytest.mark.unit
def test_download_link_orchestrates_search_download_and_progress():
    install_spotdl_module_stub()
    from src.spotdl_client import SpotdlClient

    cli = SpotdlClient(client_id="id", client_secret="sec", downloader_options={})

    seen = []

    def cb(ev: dict):
        seen.append(ev)

    res = cli.download_link("https://open.spotify.com/track/xyz", "{title}.{ext}", progress_callback=cb)

    assert len(res) == 2
    assert cli.spotdl.downloader.settings["output"] == "{title}.{ext}"

    Parent = type("P", (), {"overall_completed_tasks": 1, "song_count": 2, "overall_progress": 50})
    Tracker = type("T", (), {"song_name": "A", "progress": 10, "parent": Parent()})
    ph = cli.spotdl.downloader.progress_handler
    ph.update_callback(Tracker(), "Downloading")

    assert seen, "expected progress callback to be invoked"
    assert seen[-1]["song_display_name"] == "A"
