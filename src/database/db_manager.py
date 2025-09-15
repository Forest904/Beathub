# database/db_manager.py

from flask_sqlalchemy import SQLAlchemy
import os  # Import os for path handling
import logging
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
try:
    # SQLAlchemy 2.x
    from sqlalchemy.engine import make_url
except Exception:  # pragma: no cover
    # Fallback for older SQLAlchemy
    from sqlalchemy.engine.url import make_url

# Initialize the SQLAlchemy object
db = SQLAlchemy()
logger = logging.getLogger(__name__)

# --- Define Your Database Models Here ---
class DownloadedItem(db.Model):
    __tablename__ = 'downloaded_items' # Explicitly set table name

    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(50), unique=True, nullable=False, index=True) # Shorter string, added index for speed
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False) # Can be album artist or track artist
    image_url = db.Column(db.String(500), nullable=True) # Cover art URL
    spotify_url = db.Column(db.String(500), nullable=True) # Made nullable
    local_path = db.Column(db.String(500), nullable=True) # Path to the downloaded item's directory
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    item_type = db.Column(db.String(20), nullable=False) # 'album', 'track', 'playlist'

    def __repr__(self):
        # Improved representation for debugging
        return f'<DownloadedItem {self.item_type.capitalize()}: {self.title} by {self.artist}>'

    def to_dict(self):
        """Converts the DownloadedItem object to a dictionary for API responses."""
        return {
            'id': self.id,
            'spotify_id': self.spotify_id,
            'title': self.title,
            'artist': self.artist,
            'image_url': self.image_url,
            'spotify_url': self.spotify_url,
            'local_path': self.local_path,
            'is_favorite': self.is_favorite,
            'item_type': self.item_type
        }


class DownloadedTrack(db.Model):
    __tablename__ = 'downloaded_tracks'

    id = db.Column(db.Integer, primary_key=True)

    # Parent item (album/playlist/track container)
    item_id = db.Column(db.Integer, ForeignKey('downloaded_items.id', ondelete='CASCADE'), nullable=True, index=True)

    # Core identifiers
    spotify_id = db.Column(db.String(50), nullable=False, index=True)
    spotify_url = db.Column(db.String(500), nullable=True)
    isrc = db.Column(db.String(32), nullable=True)

    # Names & artists
    title = db.Column(db.String(255), nullable=False)
    artists = db.Column(db.JSON, nullable=False)  # list[str]
    album_name = db.Column(db.String(255), nullable=True)
    album_id = db.Column(db.String(64), nullable=True)
    album_artist = db.Column(db.String(255), nullable=True)

    # Positioning
    track_number = db.Column(db.Integer, nullable=True)
    disc_number = db.Column(db.Integer, nullable=True)
    disc_count = db.Column(db.Integer, nullable=True)
    tracks_count = db.Column(db.Integer, nullable=True)

    # Misc metadata
    duration_ms = db.Column(db.Integer, nullable=True)
    explicit = db.Column(db.Boolean, default=False, nullable=False)
    popularity = db.Column(db.Integer, nullable=True)
    publisher = db.Column(db.String(255), nullable=True)
    year = db.Column(db.Integer, nullable=True)
    date = db.Column(db.String(32), nullable=True)
    genres = db.Column(db.JSON, nullable=True)  # list[str]

    # Artwork
    cover_url = db.Column(db.String(500), nullable=True)

    # Local paths
    local_path = db.Column(db.String(500), nullable=True)
    local_lyrics_path = db.Column(db.String(500), nullable=True)

    # Relationship back to container item
    item = relationship('DownloadedItem', backref=db.backref('tracks', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'spotify_id': self.spotify_id,
            'spotify_url': self.spotify_url,
            'isrc': self.isrc,
            'title': self.title,
            'artists': self.artists,
            'album_name': self.album_name,
            'album_id': self.album_id,
            'album_artist': self.album_artist,
            'track_number': self.track_number,
            'disc_number': self.disc_number,
            'disc_count': self.disc_count,
            'tracks_count': self.tracks_count,
            'duration_ms': self.duration_ms,
            'explicit': self.explicit,
            'popularity': self.popularity,
            'publisher': self.publisher,
            'year': self.year,
            'date': self.date,
            'genres': self.genres,
            'cover_url': self.cover_url,
            'local_path': self.local_path,
            'local_lyrics_path': self.local_lyrics_path,
        }

def initialize_database(app):
    """
    Initializes the SQLAlchemy extension with the Flask app instance
    and creates all database tables if they don't already exist.
    """
    db.init_app(app)
    # Ensure the instance folder exists for SQLite database file
    instance_path = app.instance_path
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
        logger.info("Created instance folder: %s", instance_path)

    # Ensure the directory for the configured SQLite file exists
    try:
        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        if uri:
            url = make_url(uri)
            # Only handle file-based SQLite (not :memory:)
            if url.get_backend_name() == 'sqlite' and url.database and url.database != ':memory:':
                db_dir = os.path.dirname(url.database)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                    logger.info("Created SQLite DB directory: %s", db_dir)
    except Exception as e:
        # Don't block app startup on path parsing issues; log and continue
        logger.warning("Could not ensure SQLite directory exists: %s", e)

    # Create database tables within the application context
    with app.app_context():
        db.create_all()
        logger.info("Database tables created or already exist.")
