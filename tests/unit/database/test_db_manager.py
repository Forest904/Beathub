import os
from flask import Flask
import pytest
from sqlalchemy.exc import IntegrityError


@pytest.mark.unit
def test_initialize_database_in_memory_only_creates_instance_dir(tmp_path, monkeypatch):
    from src.database.db_manager import initialize_database

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    instance_dir = tmp_path / "instance"
    app.instance_path = str(instance_dir)

    calls = []
    real_makedirs = os.makedirs

    def tracing_makedirs(path, *args, **kwargs):
        calls.append(os.path.abspath(path))
        return real_makedirs(path, *args, **kwargs)

    monkeypatch.setattr(os, "makedirs", tracing_makedirs)

    initialize_database(app)

    assert instance_dir.exists()
    assert len(calls) == 1
    assert os.path.abspath(str(instance_dir)) in calls


@pytest.mark.unit
def test_downloadeditem_to_dict_and_unique_constraint(db_session, factories):
    from src.database.db_manager import DownloadedItem

    item = factories.DownloadedItemFactory(spotify_id="sp-1", title="Title", artist="Artist", item_type="album")
    db_session.commit()

    data = item.to_dict()
    assert data["spotify_id"] == "sp-1"
    assert data["title"] == "Title"
    assert data["artist"] == "Artist"
    assert data["item_type"] == "album"

    dup = factories.DownloadedItemFactory.build(spotify_id="sp-1", title="Other", artist="Other", item_type="track")
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    factories.DownloadedItemFactory(spotify_id="sp-2", title="Another", artist="X", item_type="track")
    db_session.commit()

    assert DownloadedItem.query.filter_by(spotify_id="sp-1").count() == 1
    assert DownloadedItem.query.filter_by(spotify_id="sp-2").count() == 1


@pytest.mark.unit
def test_track_relationship_basic_link(db_session, factories):
    item = factories.DownloadedItemFactory(spotify_id="alb-1", title="Alb", artist="AR", item_type="album")
    track = factories.DownloadedTrackFactory(spotify_id="trk-1", title="T", artists=["AR"], item=item)
    db_session.commit()

    assert track.item.id == item.id
    assert any(t.id == track.id for t in item.tracks)
