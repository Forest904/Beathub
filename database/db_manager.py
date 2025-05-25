# database/db_manager.py

from flask_sqlalchemy import SQLAlchemy
import os # Import os for path handling

# Initialize the SQLAlchemy object
db = SQLAlchemy()

# --- Define Your Database Models Here ---
# Renamed from Album to DownloadedItem for more flexibility
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
        print(f"Created instance folder: {instance_path}")

    # Create database tables within the application context
    with app.app_context():
        db.create_all()
        print("Database tables created or already exist.")