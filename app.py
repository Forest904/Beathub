import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Flask specific imports ---
from flask import Flask, send_from_directory
from flask_cors import CORS

# --- Import our new configuration and the main orchestrator ---
from config import Config
from src.spotify_content_downloader import SpotifyContentDownloader
from src.cd_burning_service import CDBurningService, CD_BURN_STATUS_MANAGER # Make sure this import is there

# --- Import db, DownloadedItem model, and the initialization function ---
from database.db_manager import initialize_database # Adjusted path to src/database

# --- Import Blueprints from new routes directory ---
from src.routes.download_routes import download_bp
from src.routes.artist_routes import artist_bp
from src.routes.album_details_routes import album_details_bp
from src.routes.cd_burning_routes import cd_burning_bp


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
    app = Flask(__name__, static_folder='frontend/build', static_url_path='') # Assuming frontend/build now for static files
    app.config.from_object(Config)
    CORS(app)

    # Initialize database
    initialize_database(app)

    # Initialize the main orchestrator (SpotifyContentDownloader)
    spotify_downloader = SpotifyContentDownloader(
        base_output_dir=app.config.get('BASE_OUTPUT_DIR'),
        spotify_client_id=app.config.get('SPOTIPY_CLIENT_ID'),
        spotify_client_secret=app.config.get('SPOTIPY_CLIENT_SECRET'),
        genius_access_token=app.config.get('GENIUS_ACCESS_TOKEN')
    )
    
    # Store the spotify_downloader instance in app.extensions
    # This allows blueprints to access it via current_app.extensions['spotify_downloader']
    app.extensions['spotify_downloader'] = spotify_downloader

    # Initialize the CD Burning Service
    # This will log its initialization at app startup
    cd_burning_service_instance = CDBurningService(app_logger=app.logger, base_output_dir=app.config.get('BASE_OUTPUT_DIR'))
    # This allows blueprints to access it via current_app.extensions['cd_burning_service']
    app.extensions['cd_burning_service'] = cd_burning_service_instance

    # --- Register Blueprints ---
    app.register_blueprint(download_bp)
    app.register_blueprint(artist_bp)
    app.register_blueprint(album_details_bp)
    # --- NEW: Register the CD Burning Blueprint ---
    app.register_blueprint(cd_burning_bp)

    # --- Catch-all route for serving React app in production ---
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react_app(path):
        # Adjust path to serve from 'frontend/build' assuming that's where your compiled React app is
        react_build_dir = os.path.join(app.root_path, 'frontend', 'build')
        if path != "" and os.path.exists(os.path.join(react_build_dir, path)):
            return send_from_directory(react_build_dir, path)
        else:
            return send_from_directory(react_build_dir, 'index.html')

    return app

if __name__ == '__main__':
    # Ensure the base downloads directory exists when the app starts
    os.makedirs(Config.BASE_OUTPUT_DIR, exist_ok=True)

    # Check API credentials at startup
    if not Config.SPOTIPY_CLIENT_ID or not Config.SPOTIPY_CLIENT_SECRET:
        logger.warning("Spotify API client ID or client secret not found in environment variables.")
        logger.warning("Please set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET for full functionality.")
    if not Config.GENIUS_ACCESS_TOKEN:
        logger.warning("Genius API access token not found. Lyrics fetching will be unavailable.")

    # Create the app instance here
    app = create_app()
    logger.info("Starting Flask application...")
    app.run(debug=True, host='0.0.0.0', port=5000)