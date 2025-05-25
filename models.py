# models.py
from database import db # Import the db instance

class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    spotify_url = db.Column(db.String(500), nullable=False)
    local_path = db.Column(db.String(500), nullable=True) # Path to the downloaded files/folder
    is_favorite = db.Column(db.Boolean, default=False)

    def to_dict(self): # Helper for jsonify
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

    def __repr__(self):
        return f"<Album {self.title} by {self.artist}>"