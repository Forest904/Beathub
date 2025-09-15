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

    # Must create the instance folder
    assert instance_dir.exists()
    # No other directories should be created for the DB since it's in-memory
    # There should be exactly one makedirs call for the instance path
    assert len(calls) == 1
    assert os.path.abspath(str(instance_dir)) in calls


@pytest.mark.unit
def test_downloadeditem_to_dict_and_unique_constraint(app):
    from src.database.db_manager import db, DownloadedItem

    with app.app_context():
        item = DownloadedItem(
            spotify_id="sp-1",
            title="Title",
            artist="Artist",
            image_url="http://i",
            spotify_url="http://s",
            local_path="/tmp/x",
            item_type="album",
        )
        db.session.add(item)
        db.session.commit()

        d = item.to_dict()
        assert d["spotify_id"] == "sp-1"
        assert d["title"] == "Title"
        assert d["artist"] == "Artist"
        assert d["item_type"] == "album"

        # Duplicate spotify_id should violate unique constraint
        dup = DownloadedItem(
            spotify_id="sp-1",
            title="Other",
            artist="Other",
            item_type="track",
        )
        db.session.add(dup)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        # Session remains usable after rollback
        ok = DownloadedItem(
            spotify_id="sp-2",
            title="Another",
            artist="X",
            item_type="track",
        )
        db.session.add(ok)
        db.session.commit()

        assert DownloadedItem.query.count() == 2


@pytest.mark.unit
def test_track_relationship_basic_link(app):
    from src.database.db_manager import db, DownloadedItem, DownloadedTrack

    with app.app_context():
        item = DownloadedItem(
            spotify_id="alb-1",
            title="Alb",
            artist="AR",
            item_type="album",
        )
        db.session.add(item)
        db.session.commit()

        tr = DownloadedTrack(
            item_id=item.id,
            spotify_id="trk-1",
            title="T",
            artists=["AR"],
        )
        db.session.add(tr)
        db.session.commit()

        # Relationship backref works
        assert tr.item.id == item.id
        assert any(t.id == tr.id for t in item.tracks)

