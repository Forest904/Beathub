import os
import importlib
import types
import sys
import pytest

# Ensure project root is on sys.path so 'app', 'config', and 'src' import correctly
_TESTS_DIR = os.path.dirname(__file__)
_ROOT_DIR = os.path.abspath(os.path.join(_TESTS_DIR, os.pardir))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Ensure a clean env for tests, and provide an in-memory DB by default."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    # Provide fake Spotify creds so the app doesn't warn/fail during tests
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test-client-secret")
    yield


@pytest.fixture
def app(monkeypatch):
    # Install minimal stubs for spotdl types to satisfy imports during app/module load
    # This avoids requiring the real spotdl package for route tests.
    m_spotdl = types.ModuleType("spotdl")
    m_types = types.ModuleType("spotdl.types")
    m_song = types.ModuleType("spotdl.types.song")

    class _DummySong:
        def __init__(self):
            self.json = {}

    m_song.Song = _DummySong
    sys.modules["spotdl"] = m_spotdl
    sys.modules["spotdl.types"] = m_types
    sys.modules["spotdl.types.song"] = m_song

    # Import module, then patch SpotDL builder to avoid spinning real engine threads
    import app as app_module
    def _skip_spotdl(*args, **kwargs):
        raise RuntimeError("skip spotdl client init in tests")
    monkeypatch.setattr(app_module, "build_default_client", _skip_spotdl, raising=True)

    application = app_module.create_app()
    yield application


@pytest.fixture
def client(app):
    return app.test_client()
