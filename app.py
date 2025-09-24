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
from src.cd_burning_service import CDBurningService

# --- Import db, DownloadedItem model, and the initialization function ---
from src.database.db_manager import initialize_database

# --- Import Blueprints from new routes directory ---
from src.routes.download_routes import download_bp
from src.routes.artist_routes import artist_bp
from src.routes.album_details_routes import album_details_bp
from src.routes.cd_burning_routes import cd_burning_bp
from src.routes.progress_routes import progress_bp
from src.routes.config_routes import config_bp
from src.routes.compilation_routes import compilation_bp
from src.progress import ProgressBroker, BrokerPublisher
from src.repository import DefaultDownloadRepository
from src.burn_sessions import BurnSessionManager
from src.jobs import JobQueue


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

    # Console handler optional: keep backend console quiet unless explicitly enabled
    try:
        from config import Config as _Cfg
        enable_console = bool(_Cfg.ENABLE_CONSOLE_LOGS)
    except Exception:
        # Fallback to env if Config import fails here
        enable_console = os.getenv('ENABLE_CONSOLE_LOGS', '0').strip().lower() in ('1', 'true', 'yes', 'on')
    if enable_console:
        console_handler = logging.StreamHandler()
        # If console logging is enabled, keep it concise: warnings and above
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

    # Prepare progress broker and SpotDL client first so we can inject
    app.extensions['progress_broker'] = ProgressBroker()
    progress_publisher = BrokerPublisher(app.extensions['progress_broker'])
    spotdl_client = None
    try:
        spotdl_client = build_default_client(app_logger=app.logger)
        # Progress hook publishes to broker for SSE
        def _spotdl_progress(ev: dict):
            try:
                app.logger.info(
                    "SpotDL: %s - %s (%s%%)",
                    ev.get('song_display_name'), ev.get('status'), ev.get('progress')
                )
                app.extensions['progress_broker'].publish(ev)
            except Exception:
                pass
        spotdl_client.set_progress_callback(_spotdl_progress, web_ui=True)
        app.extensions['spotdl_client'] = spotdl_client
        app.logger.info(
            "SpotDL client ready: threads=%s, format=%s, providers=%s",
            spotdl_client.spotdl.downloader.settings.get('threads'),
            spotdl_client.spotdl.downloader.settings.get('format'),
            spotdl_client.spotdl.downloader.settings.get('audio_providers'),
        )
    except Exception as e:
        # Log full traceback to aid diagnosing missing deps (ffmpeg/yt-dlp),
        # credential issues, or Windows event loop quirks.
        app.logger.warning(
            "SpotDL client not initialized; download features unavailable: %s",
            e,
            exc_info=True,
        )

    # Initialize the main orchestrator (SpotifyContentDownloader) with DI
    spotify_downloader = SpotifyContentDownloader(
        base_output_dir=app.config.get('BASE_OUTPUT_DIR'),
        spotify_client_id=app.config.get('SPOTIPY_CLIENT_ID'),
        spotify_client_secret=app.config.get('SPOTIPY_CLIENT_SECRET'),
        genius_access_token=app.config.get('GENIUS_ACCESS_TOKEN'),
        spotdl_audio_source=app.config.get('SPOTDL_AUDIO_SOURCE'),
        spotdl_format=app.config.get('SPOTDL_FORMAT'),
        progress_publisher=progress_publisher,
        spotdl_client=spotdl_client,
        download_repository=DefaultDownloadRepository(),
    )

    # Expose orchestrator for routes
    app.extensions['spotify_downloader'] = spotify_downloader

    # Initialize job queue orchestrator
    try:
        job_queue = JobQueue(downloader=spotify_downloader, logger=app.logger, flask_app=app)
        app.extensions['download_jobs'] = job_queue
        app.logger.info("Download job queue initialized with %s workers", job_queue.workers)
    except Exception as e:
        app.logger.warning("Job queue not initialized: %s", e)

    # Initialize the CD Burning Service
    # This will log its initialization at app startup
    cd_burning_service_instance = CDBurningService(app_logger=app.logger, base_output_dir=app.config.get('BASE_OUTPUT_DIR'))
    # This allows blueprints to access it via current_app.extensions['cd_burning_service']
    app.extensions['cd_burning_service'] = cd_burning_service_instance
    # Burn session manager for per-session state
    app.extensions['burn_sessions'] = BurnSessionManager()

    # --- Register Blueprints ---
    app.register_blueprint(download_bp)
    app.register_blueprint(artist_bp)
    app.register_blueprint(album_details_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(compilation_bp)
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

    # Configure logging:
    # - In debug with reloader: only in the child process to avoid duplicate files
    # - In non-debug: always configure here
    debug_mode = bool(Config.DEBUG)
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'log')
    if debug_mode:
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            log_file_path = configure_logging(log_dir)
            logger.info("File logging initialized at %s", log_file_path)
    else:
        log_file_path = configure_logging(log_dir)
        logger.info("File logging initialized at %s", log_file_path)

    # Check API credentials at startup
    if not Config.SPOTIPY_CLIENT_ID or not Config.SPOTIPY_CLIENT_SECRET:
        logger.warning("Spotify API client ID or client secret not found in environment variables.")
        logger.warning("Please set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET for full functionality.")
    # Optional: SpotDL can use a GENIUS_ACCESS_TOKEN to improve embedded lyrics

    # Create the app instance here
    app = create_app()
    # Route app.logger through root handlers, keep levels consistent
    app.logger.handlers = []
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = True
    logger.info("Starting Flask application...")
    # Enable threaded mode so SSE can stream while downloads run in parallel requests
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000, threaded=True)
