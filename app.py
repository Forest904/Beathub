import os
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from urllib.parse import urlparse
from uuid import uuid4

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Flask specific imports ---
from flask import Flask, send_from_directory, request, jsonify, g
from flask_cors import CORS

# --- Import our new configuration and the main orchestrator ---
from config import Config
from src.core import ProgressBroker, BrokerPublisher
from src.database.db_manager import initialize_database
from src.auth import init_auth
from src.domain.downloads import (
    DownloadOrchestrator,
    DefaultDownloadRepository,
    JobQueue,
    AudioCoverDownloadService,
    FileManager,
)
from src.domain.catalog import MetadataService, LyricsService
from src.domain.burning import CDBurningService, BurnSessionManager
from src.infrastructure.spotdl import build_default_client
from src.interfaces.http.routes import (
    download_bp,
    artist_bp,
    album_details_bp,
    cd_burning_bp,
    progress_bp,
    config_bp,
    compilation_bp,
    playlist_bp,
    favorite_bp,
    health_bp,
)
from src.observability import configure_structured_logging, metrics_blueprint, init_tracing


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

    # Preserve structured handlers; remove existing FileHandlers to avoid duplicates
    root.handlers = [h for h in root.handlers if not isinstance(h, logging.FileHandler)]

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
    app.config.update(
        {
            'PUBLIC_MODE': Config.PUBLIC_MODE,
            'ENABLE_CD_BURNER': Config.ENABLE_CD_BURNER,
            'ALLOW_STREAMING_EXPORT': Config.ALLOW_STREAMING_EXPORT,
            'ENABLE_RATE_LIMITING': Config.ENABLE_RATE_LIMITING,
            'RATE_LIMIT_REQUESTS': Config.RATE_LIMIT_REQUESTS,
            'RATE_LIMIT_WINDOW_SECONDS': Config.RATE_LIMIT_WINDOW_SECONDS,
            'READINESS_QUEUE_THRESHOLD': Config.READINESS_QUEUE_THRESHOLD,
            'OAUTH_REDIRECT_ALLOWLIST': tuple(Config.OAUTH_REDIRECT_ALLOWLIST),
            'CONTENT_SECURITY_POLICY': Config.CONTENT_SECURITY_POLICY,
            'OTEL_EXPORTER_OTLP_ENDPOINT': Config.OTEL_EXPORTER_OTLP_ENDPOINT,
            'OTEL_EXPORTER_OTLP_HEADERS': Config.OTEL_EXPORTER_OTLP_HEADERS,
            'OTEL_EXPORTER_OTLP_INSECURE': Config.OTEL_EXPORTER_OTLP_INSECURE,
            'OTEL_SERVICE_NAME': Config.OTEL_SERVICE_NAME,
        }
    )
    configure_structured_logging(app)
    init_tracing(app)

    @app.before_request
    def _assign_request_id():
        g.request_id = request.headers.get('X-Request-ID') or uuid4().hex

    @app.after_request
    def _inject_request_id(response):
        if getattr(g, 'request_id', None):
            response.headers.setdefault('X-Request-ID', g.request_id)
        return response
    allowed_origins = sorted({
        origin.strip()
        for origin in Config.CORS_ALLOWED_ORIGINS
        if origin and origin.strip() and origin.strip() != "*"
    })
    cors_resources = {r"/api/*": {"origins": allowed_origins}}
    CORS(
        app,
        resources=cors_resources,
        supports_credentials=True,
        expose_headers=["Content-Disposition"],
    )

    app.extensions['feature_flags'] = {
        'public_mode': app.config['PUBLIC_MODE'],
        'enable_cd_burner': app.config['ENABLE_CD_BURNER'],
        'allow_streaming_export': app.config['ALLOW_STREAMING_EXPORT'],
        'readiness_queue_threshold': app.config['READINESS_QUEUE_THRESHOLD'],
    }

    redirect_allowlist = {origin.rstrip('/') for origin in app.config['OAUTH_REDIRECT_ALLOWLIST'] if origin}

    def _is_redirect_allowed(target: str) -> bool:
        if not target:
            return False
        try:
            parsed = urlparse(target)
        except Exception:
            return False
        if not parsed.scheme or not parsed.netloc:
            return False
        normalized = f"{parsed.scheme}://{parsed.netloc}".rstrip('/')
        return normalized in redirect_allowlist

    if redirect_allowlist:

        @app.before_request
        def _enforce_redirect_allowlist():
            endpoint = request.endpoint or ""
            if not endpoint.startswith("auth."):
                return None
            candidate = request.args.get("redirect") or request.args.get("redirect_uri")
            if not candidate:
                return None
            if _is_redirect_allowed(candidate):
                return None
            app.logger.warning(
                "Blocked disallowed OAuth redirect",
                extra={
                    "policy": "redirect_allowlist",
                    "path": request.path,
                    "redirect": candidate,
                },
            )
            return jsonify(
                {
                    "error": "policy_violation",
                    "policy": "redirect_allowlist",
                    "message": "Redirect URI is not permitted for this deployment.",
                }
            ), 400

    if (
        app.config['ENABLE_RATE_LIMITING']
        and app.config['RATE_LIMIT_REQUESTS'] > 0
        and app.config['RATE_LIMIT_WINDOW_SECONDS'] > 0
    ):
        rate_limit_state = {
            'lock': threading.RLock(),
            'buckets': defaultdict(deque),
        }
        app.extensions['rate_limiter'] = rate_limit_state

        @app.before_request
        def _apply_rate_limit():
            # Skip rate limiting for CORS preflight
            if request.method == "OPTIONS":
                return None
            limit = app.config['RATE_LIMIT_REQUESTS']
            window = app.config['RATE_LIMIT_WINDOW_SECONDS']
            if limit <= 0 or window <= 0:
                return None
            identifier = (
                request.headers.get('X-Forwarded-For', '')
                or request.remote_addr
                or 'unknown'
            ).split(',')[0].strip()
            now = time.time()
            with rate_limit_state['lock']:
                bucket = rate_limit_state['buckets'].setdefault(identifier, deque())
                threshold = now - window
                while bucket and bucket[0] <= threshold:
                    bucket.popleft()
                if len(bucket) >= limit:
                    app.logger.warning(
                        "Rate limit exceeded",
                        extra={
                            "policy": "rate_limit",
                            "ip": identifier,
                            "path": request.path,
                        },
                    )
                    return jsonify(
                        {
                            "error": "rate_limited",
                            "policy": "rate_limit",
                            "message": "Too many requests. Please slow down.",
                        }
                    ), 429
                bucket.append(now)

    csp_policy = app.config.get('CONTENT_SECURITY_POLICY')
    if csp_policy:

        @app.after_request
        def _apply_csp(response):
            response.headers.setdefault('Content-Security-Policy', csp_policy)
            return response

    # Initialize database
    initialize_database(app)
    init_auth(app)

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

    # Build domain services to keep orchestration wiring at the app boundary
    metadata_service = MetadataService(
        spotify_client_id=app.config.get('SPOTIPY_CLIENT_ID'),
        spotify_client_secret=app.config.get('SPOTIPY_CLIENT_SECRET'),
    )
    audio_service = AudioCoverDownloadService(
        base_output_dir=app.config.get('BASE_OUTPUT_DIR'),
        spotdl_audio_source=app.config.get('SPOTDL_AUDIO_SOURCE'),
        spotdl_format=app.config.get('SPOTDL_FORMAT'),
    )
    lyrics_service = LyricsService(genius_access_token=app.config.get('GENIUS_ACCESS_TOKEN'))
    file_manager = FileManager(base_output_dir=app.config.get('BASE_OUTPUT_DIR'))
    download_repository = DefaultDownloadRepository()

    # Initialize the main orchestrator with explicit dependencies
    download_orchestrator = DownloadOrchestrator(
        base_output_dir=app.config.get('BASE_OUTPUT_DIR'),
        spotify_client_id=app.config.get('SPOTIPY_CLIENT_ID'),
        spotify_client_secret=app.config.get('SPOTIPY_CLIENT_SECRET'),
        genius_access_token=app.config.get('GENIUS_ACCESS_TOKEN'),
        spotdl_audio_source=app.config.get('SPOTDL_AUDIO_SOURCE'),
        spotdl_format=app.config.get('SPOTDL_FORMAT'),
        progress_publisher=progress_publisher,
        spotdl_client=spotdl_client,
        download_repository=download_repository,
        metadata_service=metadata_service,
        audio_service=audio_service,
        lyrics_service=lyrics_service,
        file_manager=file_manager,
    )

    # Expose orchestrator for routes
    app.extensions['download_orchestrator'] = download_orchestrator

    # Initialize job queue orchestrator
    try:
        job_queue = JobQueue(downloader=download_orchestrator, logger=app.logger, flask_app=app)
        app.extensions['download_jobs'] = job_queue
        app.logger.info("Download job queue initialized with %s workers", job_queue.workers)
    except Exception as e:
        app.logger.warning("Job queue not initialized: %s", e)

    # Initialize the CD Burning Service
    # This will log its initialization at app startup
    if app.config['ENABLE_CD_BURNER']:
        cd_burning_service_instance = CDBurningService(app_logger=app.logger, base_output_dir=app.config.get('BASE_OUTPUT_DIR'))
        # This allows blueprints to access it via current_app.extensions['cd_burning_service']
        app.extensions['cd_burning_service'] = cd_burning_service_instance
        # Burn session manager for per-session state
        app.extensions['burn_sessions'] = BurnSessionManager()
    else:
        app.logger.info("CD Burning service disabled by configuration.")
        app.extensions['cd_burning_service'] = None
        app.extensions['burn_sessions'] = None

    # --- Register Blueprints ---
    app.register_blueprint(download_bp)
    app.register_blueprint(artist_bp)
    app.register_blueprint(album_details_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(compilation_bp)
    app.register_blueprint(playlist_bp)
    app.register_blueprint(favorite_bp)
    app.register_blueprint(metrics_blueprint)
    app.register_blueprint(health_bp)
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
