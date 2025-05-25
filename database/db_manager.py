# database/db_manager.py

from flask_sqlalchemy import SQLAlchemy

# Initialize the SQLAlchemy object
# It's not yet bound to a specific Flask app.
db = SQLAlchemy()

# --- Define Your Database Models Here ---
class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    spotify_url = db.Column(db.String(500), nullable=False)
    local_path = db.Column(db.String(500), nullable=True)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<Album {self.title} by {self.artist}>'

    def to_dict(self):
        return {
            'id': self.id,
            'spotify_id': self.spotify_id,
            'title': self.title,
            'artist': self.artist,
            'image_url': self.image_url,
            'spotify_url': self.spotify_url,
            'local_path': self.local_path,
            'is_favorite': self.is_favorite
        }

def initialize_database(app):
    """
    Initializes the SQLAlchemy extension with the Flask app instance
    and creates all database tables if they don't already exist.
    """
    db.init_app(app)
    # Create database tables within the application context
    with app.app_context():
        db.create_all()
        print("Database tables created or already exist.")