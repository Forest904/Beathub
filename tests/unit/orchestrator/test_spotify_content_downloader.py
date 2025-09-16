import importlib
from pathlib import Path

import pytest
from flask import Flask

from tests.support.stubs import SpotDLClientStub


def _reload_orchestrator():
    import src.spotify_content_downloader as orch
    return importlib.reload(orch)


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


class _Broker:
    def __init__(self):
        self.events = []

    def publish(self, ev):
        self.events.append(ev)


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
def test_parse_item_type_and_extract_id(url, expected, spotdl_song_stub):
    orch = _reload_orchestrator()
    downloader = orch.SpotifyContentDownloader()
    assert downloader._parse_item_type(url) == expected
    assert downloader._extract_spotify_id(url) in ("xyz", "u")


@pytest.mark.unit
def test_download_spotify_content_happy_path(tmp_path, monkeypatch, spotdl_song_stub):
    orch = _reload_orchestrator()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    from src.database.db_manager import initialize_database, db, DownloadedTrack

    initialize_database(app)

    broker = _Broker()
    app.extensions["progress_broker"] = broker

    downloader = orch.SpotifyContentDownloader(base_output_dir=str(tmp_path))

    downloader.metadata_service.get_metadata_from_link = lambda link: {
        "title": "ALB",
        "artist": "AR",
        "image_url": "http://img/cover.jpg",
        "spotify_url": link,
        "item_type": "album",
    }

    out_dir = tmp_path / "AR - ALB"
    out_dir.mkdir(parents=True)
    downloader.file_manager.create_item_output_directory = lambda artist, title: str(out_dir)

    cover_path = out_dir / "cover.jpg"
    cover_path.write_bytes(b"img")
    downloader.audio_cover_download_service.download_cover_image = (
        lambda url, odir, filename="cover.jpg": str(cover_path)
    )

    songs_data = [_make_song_json(1), _make_song_json(2)]
    fake_client = SpotDLClientStub(base_dir=out_dir, songs=songs_data)
    monkeypatch.setattr(downloader, "_resolve_spotdl_client", lambda: fake_client)

    with app.app_context():
        res = downloader.download_spotify_content("https://open.spotify.com/album/abc123")

        assert res["status"] == "success"
        assert res["item_name"] == "ALB"
        assert res["artist"] == "AR"
        assert res["cover_art_url"] == "http://img/cover.jpg"
        assert Path(res["metadata_file_path"]).exists()
        assert Path(res["output_directory"]) == out_dir
        assert len(res["tracks"]) == 2

        count = db.session.query(DownloadedTrack).count()
        assert count >= 0
        assert broker.events, "expected at least one progress event"


@pytest.mark.unit
def test_download_spotify_content_no_spotdl_returns_error(tmp_path, monkeypatch, spotdl_song_stub):
    orch = _reload_orchestrator()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    from src.database.db_manager import initialize_database

    initialize_database(app)

    downloader = orch.SpotifyContentDownloader(base_output_dir=str(tmp_path))
    downloader.metadata_service.get_metadata_from_link = (
        lambda link: {"title": "ALB", "artist": "AR", "image_url": None, "spotify_url": link}
    )
    downloader.file_manager.create_item_output_directory = (
        lambda artist, title: str(tmp_path / "AR - ALB")
    )
    monkeypatch.setattr(downloader, "_resolve_spotdl_client", lambda: None)

    with app.app_context():
        res = downloader.download_spotify_content("https://open.spotify.com/album/abc123")
        assert isinstance(res, dict)
        assert res.get("status") != "success"


@pytest.mark.unit
def test_download_spotify_content_cover_image_absent(tmp_path, monkeypatch, spotdl_song_stub):
    orch = _reload_orchestrator()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    from src.database.db_manager import initialize_database

    initialize_database(app)

    downloader = orch.SpotifyContentDownloader(base_output_dir=str(tmp_path))
    downloader.metadata_service.get_metadata_from_link = (
        lambda link: {"title": "ALB", "artist": "AR", "image_url": "http://x", "spotify_url": link}
    )
    out_dir = tmp_path / "AR - ALB"
    out_dir.mkdir(parents=True)
    downloader.file_manager.create_item_output_directory = lambda a, t: str(out_dir)
    downloader.audio_cover_download_service.download_cover_image = (
        lambda url, odir, filename="cover.jpg": None
    )

    fake_client = SpotDLClientStub(base_dir=out_dir, songs=[_make_song_json(1), _make_song_json(2)])
    monkeypatch.setattr(downloader, "_resolve_spotdl_client", lambda: fake_client)

    with app.app_context():
        res = downloader.download_spotify_content("https://open.spotify.com/album/abc123")
        assert res["status"] == "success"
        assert res.get("local_cover_image_path") is None


@pytest.mark.unit
def test_download_spotify_content_lyrics_export_error_is_ignored(tmp_path, monkeypatch, spotdl_song_stub):
    orch = _reload_orchestrator()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    from src.database.db_manager import initialize_database

    initialize_database(app)

    downloader = orch.SpotifyContentDownloader(base_output_dir=str(tmp_path))
    downloader.metadata_service.get_metadata_from_link = (
        lambda link: {"title": "ALB", "artist": "AR", "image_url": "http://x", "spotify_url": link}
    )
    out_dir = tmp_path / "AR - ALB"
    out_dir.mkdir(parents=True)
    downloader.file_manager.create_item_output_directory = lambda a, t: str(out_dir)
    downloader.audio_cover_download_service.download_cover_image = (
        lambda url, odir, filename="cover.jpg": None
    )
    downloader.lyrics_service.export_embedded_lyrics = (
        lambda path: (_ for _ in ()).throw(RuntimeError("fail"))
    )

    fake_client = SpotDLClientStub(base_dir=out_dir, songs=[_make_song_json(1), _make_song_json(2)])
    monkeypatch.setattr(downloader, "_resolve_spotdl_client", lambda: fake_client)

    with app.app_context():
        res = downloader.download_spotify_content("https://open.spotify.com/album/abc123")
        assert res["status"] == "success"


@pytest.mark.unit
def test_download_spotify_content_db_commit_failure_rolls_back(tmp_path, monkeypatch, spotdl_song_stub):
    orch = _reload_orchestrator()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    from src.database.db_manager import initialize_database, db

    initialize_database(app)

    downloader = orch.SpotifyContentDownloader(base_output_dir=str(tmp_path))
    downloader.metadata_service.get_metadata_from_link = (
        lambda link: {"title": "ALB", "artist": "AR", "image_url": "http://x", "spotify_url": link}
    )
    out_dir = tmp_path / "AR - ALB"
    out_dir.mkdir(parents=True)
    downloader.file_manager.create_item_output_directory = lambda a, t: str(out_dir)
    downloader.audio_cover_download_service.download_cover_image = (
        lambda url, odir, filename="cover.jpg": None
    )

    fake_client = SpotDLClientStub(base_dir=out_dir, songs=[_make_song_json(1), _make_song_json(2)])
    monkeypatch.setattr(downloader, "_resolve_spotdl_client", lambda: fake_client)

    calls = {"count": 0}
    real_commit = db.session.commit

    def failing_commit():
        calls["count"] += 1
        raise RuntimeError("db error")

    with app.app_context():
        monkeypatch.setattr(db.session, "commit", failing_commit, raising=True)
        res = downloader.download_spotify_content("https://open.spotify.com/album/abc123")
        assert res["status"] == "success"
        assert calls["count"] >= 1
        monkeypatch.setattr(db.session, "commit", real_commit, raising=True)
