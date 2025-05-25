import os
import logging
from flask import Flask, request, jsonify, send_from_directory  # Removed send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy # New
import spotipy # New
from spotipy.oauth2 import SpotifyClientCredentials # New

# --- Import your refactored modules ---
from src.download_service import DownloadService

# --- Logger Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Flask Application Setup ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes (important for React frontend)

# --- Configuration ---
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_key_change_me_asap') # Good practice
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/cd_collection.db' # Ensure 'instance' folder exists
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Spotify API credentials from environment variables
SPOTIPY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize Spotipy (for fetching metadata for gallery)
# This will be used by new API endpoints to fetch album details from Spotify
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID,
                                                           client_secret=SPOTIPY_CLIENT_SECRET))

# Initialize the DownloadService
download_service = DownloadService(base_output_dir="./downloads", spotify_client=sp) # Pass sp client if DownloadService needs it

# --- Database Model (Moved from previous example) ---
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

# Create database tables
with app.app_context():
    db.create_all()
    # Ensure instance directory exists for sqlite
    os.makedirs(os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')), exist_ok=True)

# --- API Endpoints ---

@app.route('/api/download', methods=['POST']) # Changed endpoint name for API clarity
def download_spotify_item_api():
    """API endpoint to trigger Spotify content download."""
    data = request.get_json()
    spotify_link = data.get('spotify_link')

    if not spotify_link:
        return jsonify({"status": "error", "message": "Spotify link is required."}), 400

    logger.info(f"Received download request for: {spotify_link}")
    
    # Delegate the heavy lifting to the DownloadService
    # The DownloadService should ideally return metadata including album art URL
    result = download_service.download_spotify_content(spotify_link)

    if result["status"] == "success":
        # After successful download (or even just metadata retrieval),
        # add/update the album in your database
        album_data = download_service.get_metadata_from_link(spotify_link) # Assuming DownloadService has this helper
        if album_data:
            existing_album = Album.query.filter_by(spotify_id=album_data['spotify_id']).first()
            if not existing_album:
                new_album = Album(
                    spotify_id=album_data['spotify_id'],
                    title=album_data['title'],
                    artist=album_data['artist'],
                    image_url=album_data['image_url'],
                    spotify_url=album_data['spotify_url'],
                    local_path=result.get('output_directory') # Assuming spotdl result contains this
                )
                db.session.add(new_album)
                db.session.commit()
                logger.info(f"Added new album to DB: {new_album.title}")
            else:
                logger.info(f"Album already in DB, skipping add: {existing_album.title}")
                # You might want to update local_path if it changed or was empty
                if not existing_album.local_path and result.get('output_directory'):
                    existing_album.local_path = result.get('output_directory')
                    db.session.commit()

        return jsonify(result), 200
    else:
        status_code = 500 if "unexpected" in result.get("message", "").lower() else 400
        return jsonify(result), status_code

@app.route('/api/albums', methods=['GET'])
def get_albums():
    """Returns a list of all albums in the collection."""
    albums = Album.query.order_by(Album.title).all()
    return jsonify([album.to_dict() for album in albums]), 200

@app.route('/api/albums/<int:album_id>/favorite', methods=['POST'])
def toggle_favorite(album_id):
    """Toggles the favorite status of an album."""
    album = Album.query.get(album_id)
    if not album:
        return jsonify({'success': False, 'message': 'Album not found'}), 404
    album.is_favorite = not album.is_favorite
    db.session.commit()
    return jsonify({'success': True, 'is_favorite': album.is_favorite}), 200

@app.route('/api/albums/<int:album_id>', methods=['DELETE'])
def delete_album(album_id):
    """Deletes an album from the collection."""
    album = Album.query.get(album_id)
    if not album:
        return jsonify({'success': False, 'message': 'Album not found'}), 404
    
    # Optional: Add logic to delete local files associated with this album
    # if album.local_path and os.path.exists(album.local_path):
    #     try:
    #         shutil.rmtree(album.local_path) # Requires 'import shutil'
    #         logger.info(f"Deleted local files for album: {album.title} at {album.local_path}")
    #     except Exception as e:
    #         logger.error(f"Error deleting local files for {album.title}: {e}")

    db.session.delete(album)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Album deleted successfully.'}), 200


# --- Catch-all route for serving React app in production ---
# In development, React's dev server handles requests.
# In production, this serves the built React app.
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Ensure the 'downloads' directory exists when the app starts
    os.makedirs("./downloads", exist_ok=True)
    os.makedirs("./instance", exist_ok=True) # Ensure instance directory for DB
    
    if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
        logger.warning("Spotify API credentials not found in environment variables.")
        logger.warning("Please set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET for full functionality.")
        # For local testing, you might uncomment these and fill them:
        # os.environ['SPOTIPY_CLIENT_ID'] = 'YOUR_ACTUAL_CLIENT_ID'
        # os.environ['SPOTIPY_CLIENT_SECRET'] = 'YOUR_ACTUAL_CLIENT_SECRET'

    app.run(debug=True, host='0.0.0.0', port=5000)