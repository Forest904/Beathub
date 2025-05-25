# app.py
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Flask specific imports ---
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# --- Import our new configuration and refactored service module ---
from config import Config
from src.download_sevice import DownloadService

# --- NEW: Import db, Album model, and the initialization function from our database manager ---
from database.db_manager import db, Album, initialize_database

# --- Logger Configuration (remains the same) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__, static_folder='build', static_url_path='')
    app.config.from_object(Config)
    CORS(app)

    # NEW: Initialize database extensions by calling the function from db_manager
    # This will also call db.create_all() internally.
    initialize_database(app)

    # Initialize Spotipy (for fetching metadata for gallery)
    spotipy_client = spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=app.config.get('SPOTIPY_CLIENT_ID'),
            client_secret=app.config.get('SPOTIPY_CLIENT_SECRET')
        )
    )

    # Initialize the DownloadService
    download_service = DownloadService(
        base_output_dir="./downloads",
        spotify_client=spotipy_client
    )

    # --- API Endpoints (referencing Album from db_manager) ---
    @app.route('/api/download', methods=['POST'])
    def download_spotify_item_api():
        data = request.get_json()
        spotify_link = data.get('spotify_link')

        if not spotify_link:
            return jsonify({"status": "error", "message": "Spotify link is required."}), 400

        logger.info(f"Received download request for: {spotify_link}")
        result = download_service.download_spotify_content(spotify_link)

        if result["status"] == "success":
            album_data = download_service.get_metadata_from_link(spotify_link)
            if album_data:
                existing_album = Album.query.filter_by(spotify_id=album_data['spotify_id']).first()
                if not existing_album:
                    new_album = Album(
                        spotify_id=album_data['spotify_id'],
                        title=album_data['title'],
                        artist=album_data['artist'],
                        image_url=album_data['image_url'],
                        spotify_url=album_data['spotify_url'],
                        local_path=result.get('output_directory_base')
                    )
                    db.session.add(new_album)
                    db.session.commit()
                    logger.info(f"Added new album to DB: {new_album.title}")
                else:
                    logger.info(f"Album already in DB, skipping add: {existing_album.title}")
                    if not existing_album.local_path and result.get('output_directory_base'):
                        existing_album.local_path = result.get('output_directory_base')
                        db.session.commit()
            return jsonify(result), 200
        else:
            status_code = 500 if "unexpected" in result.get("message", "").lower() else 400
            return jsonify(result), status_code

    @app.route('/api/albums', methods=['GET'])
    def get_albums():
        albums = Album.query.order_by(Album.title).all()
        return jsonify([album.to_dict() for album in albums]), 200

    @app.route('/api/albums/<int:album_id>/favorite', methods=['POST'])
    def toggle_favorite(album_id):
        album = Album.query.get(album_id)
        if not album:
            return jsonify({'success': False, 'message': 'Album not found'}), 404
        album.is_favorite = not album.is_favorite
        db.session.commit()
        return jsonify({'success': True, 'is_favorite': album.is_favorite}), 200

    @app.route('/api/albums/<int:album_id>', methods=['DELETE'])
    def delete_album(album_id):
        album = Album.query.get(album_id)
        if not album:
            return jsonify({'success': False, 'message': 'Album not found'}), 404
        db.session.delete(album)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Album deleted successfully.'}), 200

    # --- Catch-all route for serving React app in production (remains the same) ---
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react_app(path):
        if path != "" and os.path.exists(app.static_folder + '/' + path):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')
            
    return app

if __name__ == '__main__':
    # Ensure the 'downloads' directory exists when the app starts
    os.makedirs("./downloads", exist_ok=True)
    
    # Check Spotify credentials at startup (informative)
    if not Config.SPOTIPY_CLIENT_ID or not Config.SPOTIPY_CLIENT_SECRET:
        logger.warning("Spotify API credentials not found in environment variables.")
        logger.warning("Please set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET for full functionality.")

    # Create the app instance here
    app = create_app()
    logger.info("Starting Flask application...")
    app.run(debug=True, host='0.0.0.0', port=5000)