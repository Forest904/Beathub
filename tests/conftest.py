import os
import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path so 'app', 'config', and 'src' import correctly
_TESTS_DIR = os.path.dirname(__file__)
_ROOT_DIR = os.path.abspath(os.path.join(_TESTS_DIR, os.pardir))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from tests.support import factories as test_factories
from tests.support import stubs as test_stubs


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path_factory):
    """Ensure a clean env for tests with per-test sqlite files."""
    db_dir = tmp_path_factory.mktemp("db")
    db_path = Path(db_dir) / "test.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test-client-secret")
    yield


@pytest.fixture
def spotdl_song_stub():
    """Expose the Song stub so tests can customise behaviour easily."""
    return test_stubs.install_spotdl_song_stub()


@pytest.fixture
def app(monkeypatch, spotdl_song_stub):
    # Ensure optional options stub exists for settings tests that import create_app
    test_stubs.install_spotdl_options_stub()

    # Import module, then patch SpotDL builder to avoid spinning real engine threads
    import app as app_module

    def _skip_spotdl(*args, **kwargs):
        raise RuntimeError("skip spotdl client init in tests")

    monkeypatch.setattr(app_module, "build_default_client", _skip_spotdl, raising=True)

    application = app_module.create_app()
    yield application


@pytest.fixture
def app_context(app):
    with app.app_context():
        yield app


@pytest.fixture
def db_session(app_context):
    from src.database.db_manager import db

    test_factories.set_session(db.session)
    try:
        yield db.session
    finally:
        try:
            db.session.rollback()
        except Exception:
            pass
        db.session.remove()
        test_factories.reset_session()


@pytest.fixture
def factories(db_session):
    yield test_factories


@pytest.fixture
def client(app):
    return app.test_client()

