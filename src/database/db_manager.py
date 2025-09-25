# database/db_manager.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
import os  # Import os for path handling
import logging
from datetime import datetime
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

SYSTEM_USER_EMAIL = "system@beathub.local"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_system = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    downloads = relationship("DownloadedItem", back_populates="owner", lazy=True)
    download_jobs = relationship("DownloadJob", back_populates="owner", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_id(self) -> str:
        return str(self.id)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<User {self.email}>"

# --- Define Your Database Models Here ---
class DownloadedItem(db.Model):
    __tablename__ = 'downloaded_items' # Explicitly set table name

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    spotify_id = db.Column(db.String(50), unique=True, nullable=False, index=True) # Shorter string, added index for speed
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False) # Can be album artist or track artist
    image_url = db.Column(db.String(500), nullable=True) # Cover art URL
    spotify_url = db.Column(db.String(500), nullable=True) # Made nullable
    local_path = db.Column(db.String(500), nullable=True) # Path to the downloaded item's directory
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    item_type = db.Column(db.String(20), nullable=False) # 'album', 'track', 'playlist'

    owner = relationship('User', back_populates='downloads')

    def __repr__(self):
        # Improved representation for debugging
        return f'<DownloadedItem {self.item_type.capitalize()}: {self.title} by {self.artist}>'

    def to_dict(self):
        """Converts the DownloadedItem object to a dictionary for API responses."""
        return {
            'id': self.id,
            'spotify_id': self.spotify_id,
            'user_id': self.user_id,
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
    user_id = db.Column(db.Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)

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
    owner = relationship('User')


class DownloadJob(db.Model):
    __tablename__ = 'download_jobs'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    link = db.Column(db.String(512), nullable=False)
    status = db.Column(db.String(32), nullable=False, default='pending')
    result = db.Column(db.JSON, nullable=True)
    error = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = relationship('User', back_populates='download_jobs')

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

def ensure_system_user():
    """Ensure a non-interactive system user exists for legacy/anonymous data."""
    from sqlalchemy.exc import IntegrityError

    try:
        system = User.query.filter_by(email=SYSTEM_USER_EMAIL).first()
        if system:
            return system
        system = User(email=SYSTEM_USER_EMAIL, is_active=False, is_system=True)
        # Generate an irreversible password to avoid interactive login
        system_password = os.urandom(32).hex()
        system.set_password(system_password)
        db.session.add(system)
        db.session.commit()
        return system
    except IntegrityError:
        db.session.rollback()
        return User.query.filter_by(email=SYSTEM_USER_EMAIL).first()


def get_system_user_id() -> int:
    system = ensure_system_user()
    if system is None:
        raise RuntimeError("System user could not be created")
    return system.id


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
        ensure_system_user()
