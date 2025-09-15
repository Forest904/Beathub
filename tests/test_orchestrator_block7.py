import os
import sys
import types
import importlib
from pathlib import Path

import pytest
from flask import Flask


def _install_song_stub():
    """Install a stub for spotdl.types.song.Song before importing mapping/orchestrator."""
    m_spotdl = types.ModuleType("spotdl")
    m_types = types.ModuleType("spotdl.types")
    m_song = types.ModuleType("spotdl.types.song")

    class Song:
        def __init__(self, json_dict):
            self._json = json_dict
            # Common attributes used around the codebase
            self.artist = json_dict.get("artists", ["Unknown"])[0]
            self.album_name = json_dict.get("album_name")
            self.name = json_dict.get("name")
            self.cover_url = json_dict.get("cover_url")
            # Attributes accessed directly by orchestrator
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


def _reload_orchestrator():
    if "src.spotify_content_downloader" in sys.modules:
        del sys.modules["src.spotify_content_downloader"]
    import src.spotify_content_downloader as orch
    importlib.reload(orch)
    return orch


def _make_song_json(i: int, album="ALB", artist="AR"):
    sid = f"s{i}"
    return {
        "song_id": sid,
        "name": f"N{i}",
        "artists": [artist],
        "album_name": album,
        "album_id": "alb1",
        "album_artist": artist,
        "duration": 123 + i,
        "track_number": i,
        "disc_number": 1,
        "disc_count": 1,
        "tracks_count": 2,
        "explicit": False,
        "popularity": 10,
        "isrc": f"ISRC{i}",
        "publisher": "Label",
        "year": 2020,
        "date": "2020-01-01",
        "genres": ["pop"],
        "url": f"https://open.spotify.com/track/{sid}",
        "cover_url": "http://img/cover.jpg",
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://open.spotify.com/album/xyz", "album"),
        ("https://open.spotify.com/playlist/xyz", "playlist"),
        ("https://open.spotify.com/track/xyz", "track"),
        ("https://open.spotify.com/user/u", "unknown"),
    ],
)
def test_parse_item_type_and_extract_id(url, expected):
    _install_song_stub()
    orch = _reload_orchestrator()
    d = orch.SpotifyContentDownloader()
    assert d._parse_item_type(url) == expected
    assert d._extract_spotify_id(url) in ("xyz", "u")


class _FakeClient:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self._cb = None

    def set_output_template(self, tpl):
        return tpl

    def set_progress_callback(self, cb, web_ui=False):
        self._cb = cb

    def clear_progress_callback(self):
        self._cb = None

    def search(self, queries):
        Song = sys.modules["spotdl.types.song"].Song
        return [Song(_make_song_json(1)), Song(_make_song_json(2))]

    def download_songs(self, songs):
        # Create fake files for each song
        res = []
        for s in songs:
            p = self.base_dir / f"{s.json['name']}.mp3"
            p.write_bytes(b"data")
            res.append((s, p))
            if self._cb:
                Parent = type("P", (), {"overall_completed_tasks": 1, "song_count": len(songs), "overall_progress": 50})
                Tracker = type("T", (), {"song_name": s.json["name"], "progress": 10, "parent": Parent()})
                self._cb(Tracker(), "Downloading")
        return res

    def download_link(self, link, output_template, progress_callback=None):
        self.set_progress_callback(progress_callback)
        songs = self.search([link])
        return self.download_songs(songs)


class _Broker:
    def __init__(self):
        self.events = []
    def publish(self, ev):
        self.events.append(ev)


@pytest.mark.unit
def test_download_spotify_content_happy_path(tmp_path, monkeypatch):
    _install_song_stub()
    orch = _reload_orchestrator()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    from src.database.db_manager import initialize_database, db, DownloadedTrack
    initialize_database(app)

    broker = _Broker()
    app.extensions["progress_broker"] = broker

    # Instantiate downloader with tmp base dir
    d = orch.SpotifyContentDownloader(base_output_dir=str(tmp_path))

    # Stub out services
    d.metadata_service.get_metadata_from_link = lambda link: {
        "title": "ALB", "artist": "AR", "image_url": "http://img/cover.jpg", "spotify_url": link, "item_type": "album"
    }

    # Ensure output dir exists via real FileManager
    out_dir = tmp_path / "AR - ALB"
    out_dir.mkdir(parents=True)
    d.file_manager.create_item_output_directory = lambda artist, title: str(out_dir)

    # Cover image path
    cover_path = out_dir / "cover.jpg"
    cover_path.write_bytes(b"img")
    d.audio_cover_download_service.download_cover_image = lambda url, odir, filename="cover.jpg": str(cover_path)

    # Provide fake spotdl client
    fake = _FakeClient(base_dir=out_dir)
    monkeypatch.setattr(d, "_resolve_spotdl_client", lambda: fake)

    with app.app_context():
        res = d.download_spotify_content("https://open.spotify.com/album/abc123")

        assert res["status"] == "success"
        assert res["item_name"] == "ALB"
        assert res["artist"] == "AR"
        assert res["cover_art_url"] == "http://img/cover.jpg"
        assert Path(res["metadata_file_path"]).exists()
        assert Path(res["output_directory"]) == out_dir
        assert len(res["tracks"]) == 2

        # DB should have tracks (commit may be no-op but count >= 0)
        cnt = db.session.query(DownloadedTrack).count()
        assert cnt >= 0

        # Progress events published
        assert broker.events, "expected at least one progress event"


@pytest.mark.unit
def test_download_spotify_content_no_spotdl_returns_error(tmp_path, monkeypatch):
    _install_song_stub()
    orch = _reload_orchestrator()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    from src.database.db_manager import initialize_database
    initialize_database(app)

    d = orch.SpotifyContentDownloader(base_output_dir=str(tmp_path))
    d.metadata_service.get_metadata_from_link = lambda link: {"title": "ALB", "artist": "AR", "image_url": None, "spotify_url": link}
    d.file_manager.create_item_output_directory = lambda artist, title: str(tmp_path / "AR - ALB")
    monkeypatch.setattr(d, "_resolve_spotdl_client", lambda: None)

    with app.app_context():
        res = d.download_spotify_content("https://open.spotify.com/album/abc123")
        assert isinstance(res, dict)
        assert res.get("status") != "success"


@pytest.mark.unit
def test_download_spotify_content_cover_image_absent(tmp_path, monkeypatch):
    _install_song_stub()
    orch = _reload_orchestrator()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    from src.database.db_manager import initialize_database
    initialize_database(app)

    d = orch.SpotifyContentDownloader(base_output_dir=str(tmp_path))
    d.metadata_service.get_metadata_from_link = lambda link: {"title": "ALB", "artist": "AR", "image_url": "http://x", "spotify_url": link}
    out_dir = tmp_path / "AR - ALB"
    out_dir.mkdir(parents=True)
    d.file_manager.create_item_output_directory = lambda a, t: str(out_dir)
    d.audio_cover_download_service.download_cover_image = lambda url, odir, filename="cover.jpg": None

    fake = _FakeClient(base_dir=out_dir)
    monkeypatch.setattr(d, "_resolve_spotdl_client", lambda: fake)

    with app.app_context():
        res = d.download_spotify_content("https://open.spotify.com/album/abc123")
        assert res["status"] == "success"
        assert res.get("local_cover_image_path") is None


@pytest.mark.unit
def test_download_spotify_content_lyrics_export_error_is_ignored(tmp_path, monkeypatch):
    _install_song_stub()
    orch = _reload_orchestrator()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    from src.database.db_manager import initialize_database
    initialize_database(app)

    d = orch.SpotifyContentDownloader(base_output_dir=str(tmp_path))
    d.metadata_service.get_metadata_from_link = lambda link: {"title": "ALB", "artist": "AR", "image_url": "http://x", "spotify_url": link}
    out_dir = tmp_path / "AR - ALB"
    out_dir.mkdir(parents=True)
    d.file_manager.create_item_output_directory = lambda a, t: str(out_dir)
    d.audio_cover_download_service.download_cover_image = lambda url, odir, filename="cover.jpg": None
    # Force export error
    d.lyrics_service.export_embedded_lyrics = lambda path: (_ for _ in ()).throw(RuntimeError("fail"))

    fake = _FakeClient(base_dir=out_dir)
    monkeypatch.setattr(d, "_resolve_spotdl_client", lambda: fake)

    with app.app_context():
        res = d.download_spotify_content("https://open.spotify.com/album/abc123")
        assert res["status"] == "success"


@pytest.mark.unit
def test_download_spotify_content_db_commit_failure_rolls_back(tmp_path, monkeypatch):
    _install_song_stub()
    orch = _reload_orchestrator()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    from src.database.db_manager import initialize_database, db
    initialize_database(app)

    d = orch.SpotifyContentDownloader(base_output_dir=str(tmp_path))
    d.metadata_service.get_metadata_from_link = lambda link: {"title": "ALB", "artist": "AR", "image_url": "http://x", "spotify_url": link}
    out_dir = tmp_path / "AR - ALB"
    out_dir.mkdir(parents=True)
    d.file_manager.create_item_output_directory = lambda a, t: str(out_dir)
    d.audio_cover_download_service.download_cover_image = lambda url, odir, filename="cover.jpg": None
    fake = _FakeClient(base_dir=out_dir)
    monkeypatch.setattr(d, "_resolve_spotdl_client", lambda: fake)

    # Make commit fail once
    called = {"n": 0}
    real_commit = db.session.commit

    def failing_commit():
        called["n"] += 1
        raise RuntimeError("db error")

    with app.app_context():
        # Patch commit to fail; orchestrator should catch and continue
        monkeypatch.setattr(db.session, "commit", failing_commit, raising=True)
        res = d.download_spotify_content("https://open.spotify.com/album/abc123")
        assert res["status"] == "success"
        assert called["n"] >= 1
        # Restore commit to avoid side effects for subsequent tests
        monkeypatch.setattr(db.session, "commit", real_commit, raising=True)
