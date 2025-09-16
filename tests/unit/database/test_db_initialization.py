import os
import tempfile
from flask import Flask


def test_initialize_database_creates_sqlite_directory(tmp_path):
    # Arrange a non-existent subdirectory for the DB file
    target_dir = tmp_path / "nested" / "dbdir"
    db_file = target_dir / "test.db"
    uri = f"sqlite:///{db_file}".replace("\\", "/")

    from src.database.db_manager import initialize_database, db, DownloadedItem

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Act: initialize should create missing directory and tables
    initialize_database(app)

    # Assert directory exists and a simple DB operation works
    assert target_dir.exists()
    with app.app_context():
        count = db.session.query(DownloadedItem).count()
        assert count == 0

