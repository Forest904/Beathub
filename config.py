#!/usr/bin/env python
# config.py
import os

# This assumes config.py is at the root of your project
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_super_secret_key_lmao'

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'src', 'database', 'instance', 'cd_collector.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Spotify API
    SPOTIPY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')

    # Genius API
    GENIUS_ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')

    # Downloads
    BASE_OUTPUT_DIR = os.getenv('BASE_OUTPUT_DIR', 'downloads')

    # spotDL configuration (optional)
    SPOTDL_AUDIO_SOURCE = os.getenv('SPOTDL_AUDIO_SOURCE', 'youtube-music')
    SPOTDL_FORMAT = os.getenv('SPOTDL_FORMAT', 'mp3')
    # Limit spotDL concurrency to reduce provider rate limits
    SPOTDL_THREADS = int(os.getenv('SPOTDL_THREADS', '1'))

    # Feature flag: toggle the new SpotDL-based pipeline (default: off)
    USE_SPOTDL_PIPELINE = os.getenv('USE_SPOTDL_PIPELINE', '0').strip().lower() in (
        '1', 'true', 'yes', 'on'
    )

    # Lyrics fetching window size (for sliding-window processing)
    LYRICS_WINDOW_SIZE = int(os.getenv('LYRICS_WINDOW_SIZE', '5'))

    # Download orchestration
    DOWNLOAD_QUEUE_WORKERS = int(os.getenv('DOWNLOAD_QUEUE_WORKERS', '2'))
    DOWNLOAD_MAX_RETRIES = int(os.getenv('DOWNLOAD_MAX_RETRIES', '2'))

    # Runtime behavior
    # Turn Flask debug on/off from env; default off to avoid noisy console
    DEBUG = os.getenv('DEBUG', '0').strip().lower() in (
        '1', 'true', 'yes', 'on'
    )
    # Control console logging; when disabled, logs go only to file
    ENABLE_CONSOLE_LOGS = os.getenv('ENABLE_CONSOLE_LOGS', '0').strip().lower() in (
        '1', 'true', 'yes', 'on'
    )
