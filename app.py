import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Flask specific imports ---
from flask import Flask, send_from_directory
from flask_cors import CORS

# --- Import our new configuration and the main orchestrator ---
from config import Config
from src.spotify_content_downloader import SpotifyContentDownloader
from src.spotdl_client import build_default_client
from src.cd_burning_service import CDBurningService, CD_BURN_STATUS_MANAGER # Make sure this import is there

# --- Import db, DownloadedItem model, and the initialization function ---
from src.database.db_manager import initialize_database

# --- Import Blueprints from new routes directory ---
from src.routes.download_routes import download_bp
from src.routes.artist_routes import artist_bp
from src.routes.album_details_routes import album_details_bp
from src.routes.cd_burning_routes import cd_burning_bp


logger = logging.getLogger(__name__)


def configure_logging(log_dir: str) -> str:
    """
    Configure root logging with:
      - FileHandler (INFO+) to a new file per run: LOG-YYYY-MM-DD-HH-MM-SS
      - StreamHandler (WARNING+) to console
      - Werkzueg/Flask loggers routed to root (no extra console spam)

    Returns the path to the created log file.
    """
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    log_filename = f"log-{timestamp}"
    log_path = os.path.join(log_dir, log_filename)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Clear any pre-existing handlers to avoid duplicates
    root.handlers = []

    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File: INFO and above
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Console: WARNING and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # Quiet Flask/Werkzeug own console handlers; let them propagate to root
    for name in ("werkzeug", "flask.app"):
        _l = logging.getLogger(name)
        _l.setLevel(logging.INFO)
        _l.handlers = []
        _l.propagate = True

    return log_path


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
        genius_access_token=app.config.get('GENIUS_ACCESS_TOKEN'),
        spotdl_audio_source=app.config.get('SPOTDL_AUDIO_SOURCE'),
        spotdl_format=app.config.get('SPOTDL_FORMAT'),
    )
    
    # Store the spotify_downloader instance in app.extensions
    # This allows blueprints to access it via current_app.extensions['spotify_downloader']
    app.extensions['spotify_downloader'] = spotify_downloader

    # Initialize a single SpotDL client instance and expose it for reuse
    try:
        spotdl_client = build_default_client(app_logger=app.logger)
        # Basic progress logging hook; can be replaced by SSE/WebSocket later
        def _spotdl_progress(ev: dict):
            try:
                app.logger.info("SpotDL: %s - %s (%s%%)",
                                ev.get('song_display_name'), ev.get('status'), ev.get('progress'))
            except Exception:
                pass
        spotdl_client.set_progress_callback(_spotdl_progress)
        app.extensions['spotdl_client'] = spotdl_client
        app.logger.info("SpotDL client ready: threads=%s, format=%s, providers=%s",
                        spotdl_client.spotdl.downloader.settings.get('threads'),
                        spotdl_client.spotdl.downloader.settings.get('format'),
                        spotdl_client.spotdl.downloader.settings.get('audio_providers'))
    except Exception as e:
        # Keep the app running; the legacy pipeline will still work when feature flag is off
        app.logger.warning("SpotDL client not initialized: %s", e)

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

    # Configure logging only in the reloader child (avoids duplicate files)
    # When not using the reloader, this condition is false and we still configure.
    reloader_child = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    if reloader_child:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'log')
        log_file_path = configure_logging(log_dir)
        logger.info("File logging initialized at %s", log_file_path)

    # Check API credentials at startup
    if not Config.SPOTIPY_CLIENT_ID or not Config.SPOTIPY_CLIENT_SECRET:
        logger.warning("Spotify API client ID or client secret not found in environment variables.")
        logger.warning("Please set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET for full functionality.")
    if not Config.GENIUS_ACCESS_TOKEN:
        logger.warning("Genius API access token not found. Lyrics fetching will be unavailable.")

    # Create the app instance here
    app = create_app()
    # Route app.logger through root handlers, keep levels consistent
    app.logger.handlers = []
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = True
    logger.info("Starting Flask application...")
    app.run(debug=True, host='0.0.0.0', port=5000)
