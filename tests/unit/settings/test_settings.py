import importlib
import os
import sys
from unittest.mock import patch

from tests.support.stubs import install_spotdl_options_stub

import pytest
from hypothesis import given, strategies as st


@pytest.mark.unit
def test_overwrite_validator_accepts_known_values_and_defaults():
    import src.settings as settings
    # Accepted values remain unchanged
    assert settings.AppSettings(overwrite="skip").overwrite == "skip"
    assert settings.AppSettings(overwrite="force").overwrite == "force"
    assert settings.AppSettings(overwrite="metadata").overwrite == "metadata"
    # Unknown becomes 'skip'
    assert settings.AppSettings(overwrite="unknown").overwrite == "skip"


@pytest.mark.unit
def test_env_precedence_for_core_fields(monkeypatch):
    # Set environment overrides prior to reloading modules
    monkeypatch.setenv("BASE_OUTPUT_DIR", "t_out")
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "cid")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "csec")
    monkeypatch.setenv("SPOTDL_AUDIO_SOURCE", "youtube")
    monkeypatch.setenv("SPOTDL_FORMAT", "flac")
    monkeypatch.setenv("SPOTDL_THREADS", "4")
    monkeypatch.setenv("SPOTDL_PRELOAD", "true")
    monkeypatch.setenv("GENIUS_ACCESS_TOKEN", "gtok")

    import config as _config
    importlib.reload(_config)
    import src.settings as settings
    importlib.reload(settings)

    s = settings.load_app_settings()
    assert s.base_output_dir == _config.Config.BASE_OUTPUT_DIR == "t_out"
    assert s.spotify_client_id == _config.Config.SPOTIPY_CLIENT_ID == "cid"
    assert s.spotify_client_secret == _config.Config.SPOTIPY_CLIENT_SECRET == "csec"
    assert s.audio_providers == ["youtube"]
    assert s.format == "flac"
    assert s.threads == 4
    assert s.preload is True
    assert s.genius_token == "gtok"
    assert s.lyrics_providers == ["genius"]


@pytest.mark.unit
def test_settings_without_genius_token_has_no_lyrics_provider(monkeypatch):
    monkeypatch.delenv("GENIUS_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("SPOTDL_AUDIO_SOURCE", "youtube-music")
    monkeypatch.setenv("SPOTDL_FORMAT", "mp3")
    monkeypatch.setenv("SPOTDL_THREADS", "1")

    import config as _config
    importlib.reload(_config)
    import src.settings as settings
    importlib.reload(settings)

    s = settings.load_app_settings()
    assert s.genius_token is None
    assert s.lyrics_providers == []


@pytest.mark.unit
def test_build_spotdl_downloader_options_with_stub(monkeypatch):
    """Ensure mapping works without importing real spotdl."""
    install_spotdl_options_stub(reset=True)

    class DummyDownloaderOptionalOptions:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    sys.modules["spotdl.types.options"].DownloaderOptionalOptions = DummyDownloaderOptionalOptions
    # Ensure env values exist for mapping
    monkeypatch.setenv("SPOTDL_AUDIO_SOURCE", "youtube")
    monkeypatch.setenv("SPOTDL_FORMAT", "flac")
    monkeypatch.setenv("SPOTDL_THREADS", "2")
    monkeypatch.setenv("SPOTDL_PRELOAD", "1")
    monkeypatch.setenv("GENIUS_ACCESS_TOKEN", "tok")

    import config as _config
    importlib.reload(_config)
    import src.settings as settings
    importlib.reload(settings)

    s = settings.load_app_settings()
    opts = settings.build_spotdl_downloader_options(s)

    # Assert mapped attributes
    assert getattr(opts, "output") is None
    assert getattr(opts, "format") == "flac"
    assert getattr(opts, "audio_providers") == ["youtube"]
    assert getattr(opts, "threads") == 2
    assert getattr(opts, "overwrite") in {"skip", "force", "metadata"}
    assert getattr(opts, "lyrics_providers") == ["genius"]
    assert getattr(opts, "preload") is True
    assert getattr(opts, "genius_token") == "tok"


@pytest.mark.unit
@given(
    audio=st.sampled_from(["youtube", "youtube-music", "soundcloud"]),
    fmt=st.sampled_from(["mp3", "flac", "opus"]),
    threads=st.integers(min_value=1, max_value=8),
)
def test_property_based_env_permutations(audio, fmt, threads):
    with patch.dict(os.environ, {
        "SPOTDL_AUDIO_SOURCE": audio,
        "SPOTDL_FORMAT": fmt,
        "SPOTDL_THREADS": str(threads),
    }, clear=False):
        import config as _config
        importlib.reload(_config)
        import src.settings as settings
        importlib.reload(settings)

        s = settings.load_app_settings()
        assert s.audio_providers == [audio]
        assert s.format == fmt
        assert s.threads == threads


@pytest.mark.unit
@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("off", False),
        (None, False),
    ],
)
def test_env_bool_helper(value, expected, monkeypatch):
    import src.settings as settings
    name = "TEST_BOOL"
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)
    assert settings._env_bool(name, default=False) is expected


