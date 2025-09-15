import importlib
import os


def test_load_app_settings_uses_current_config(monkeypatch):
    # Set overrides before (re)importing modules that read env
    monkeypatch.setenv("BASE_OUTPUT_DIR", "test_downloads")
    monkeypatch.setenv("SPOTDL_AUDIO_SOURCE", "youtube")
    monkeypatch.setenv("SPOTDL_FORMAT", "flac")
    monkeypatch.setenv("SPOTDL_THREADS", "3")
    monkeypatch.setenv("USE_SPOTDL_PIPELINE", "1")
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "abc")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "def")
    monkeypatch.setenv("GENIUS_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("SPOTDL_PRELOAD", "true")

    # Reload config and settings to pick env updates
    import config as _config
    importlib.reload(_config)
    import src.settings as settings
    importlib.reload(settings)

    s = settings.load_app_settings()

    # Core checks (reflect Config defaults after env)
    assert s.base_output_dir == _config.Config.BASE_OUTPUT_DIR
    assert s.use_spotdl_pipeline == _config.Config.USE_SPOTDL_PIPELINE
    assert s.spotify_client_id == _config.Config.SPOTIPY_CLIENT_ID
    assert s.spotify_client_secret == _config.Config.SPOTIPY_CLIENT_SECRET

    # SpotDL related settings
    assert s.audio_providers == ["youtube"]
    assert s.format == "flac"
    assert s.threads == 3
    # preload is computed via env helper in settings at import time
    assert s.preload is True
    assert s.lyrics_providers == ["genius"]
    assert s.genius_token == "tok"


def test_settings_without_genius_token_has_no_lyrics_provider(monkeypatch):
    # No token -> no genius in providers
    monkeypatch.delenv("GENIUS_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("SPOTDL_AUDIO_SOURCE", "youtube-music")
    monkeypatch.setenv("SPOTDL_FORMAT", "mp3")
    monkeypatch.setenv("SPOTDL_THREADS", "1")

    import config as _config
    import importlib
    importlib.reload(_config)
    import src.settings as settings
    importlib.reload(settings)

    s = settings.load_app_settings()
    assert s.genius_token is None
    assert s.lyrics_providers == []


def test_build_spotdl_downloader_options(monkeypatch):
    # Basic sanity: options mirror settings values
    monkeypatch.setenv("SPOTDL_AUDIO_SOURCE", "youtube")
    monkeypatch.setenv("SPOTDL_FORMAT", "flac")
    monkeypatch.setenv("SPOTDL_THREADS", "2")

    import importlib
    import config as _config
    importlib.reload(_config)
    import src.settings as settings
    importlib.reload(settings)

    s = settings.load_app_settings()
    opts = settings.build_spotdl_downloader_options(s)

    # SpotDL's options object may be a dataclass-like or dict; handle both
    def _get(obj, key):
        return getattr(obj, key) if hasattr(obj, key) else obj.get(key)

    assert _get(opts, "format") == "flac"
    assert _get(opts, "threads") == 2
    assert _get(opts, "audio_providers") == ["youtube"]
