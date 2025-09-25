#!/usr/bin/env python
# config.py
import os
from typing import List

# This assumes config.py is at the root of your project
basedir = os.path.abspath(os.path.dirname(__file__))


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _get_csv_list(name: str, default: str) -> List[str]:
    raw = os.getenv(name)
    source = raw if raw is not None else default
    return [token.strip() for token in source.split(",") if token and token.strip()]


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_super_secret_key_lmao'

    # Database (BeatHub)
    # Always use the new DB filename; the app creates it and tables at startup.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'src', 'database', 'instance', 'beathub.db')
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
    SPOTDL_THREADS = _get_int('SPOTDL_THREADS', 1)

    # Download orchestration
    DOWNLOAD_QUEUE_WORKERS = _get_int('DOWNLOAD_QUEUE_WORKERS', 2)
    DOWNLOAD_MAX_RETRIES = _get_int('DOWNLOAD_MAX_RETRIES', 2)

    # Metadata caching (Spotify/SpotDL lookups)
    METADATA_CACHE_TTL_SECONDS = _get_int('METADATA_CACHE_TTL_SECONDS', 300)
    METADATA_CACHE_MAXSIZE = max(1, _get_int('METADATA_CACHE_MAXSIZE', 256))

    # Popular artists sourcing (fully controlled by app)
    # Curated editorial/viral playlists used to seed the pool. Not configurable via env.
    POPULAR_ARTIST_PLAYLIST_IDS = [
        # Global/Editorial
        '37i9dQZEVXbLRQDuF5jeBP',  # Top 50 - Global
        '37i9dQZF1DXcBWIGoYBM5M',  # Today's Top Hits
        '37i9dQZEVXbMDoHDwVN2tF',  # Top 50 - Italy (example regional)
        '37i9dQZEVXbLiRSasKsNU9',  # Viral 50 - Global
        # Genre anchors (IDs are stable public Spotify/editorial playlists)
        '37i9dQZF1DX0XUsuxWHRQd',  # RapCaviar
        '37i9dQZF1DWXRqgorJj26U',  # Rock Classics
        '37i9dQZF1DX4SBhb3fqCJd',  # Are & Be (R&B)
        '37i9dQZF1DX4dyzvuaRJ0n',  # mint (Dance/Electronic)
        '37i9dQZF1DX10zKzsJ2jva',  # Viva Latino
        '37i9dQZF1DX4JAvHpjipBk',  # New Music Friday
    ]
    # Default page size if none specified
    POPULAR_ARTIST_LIMIT = max(1, _get_int('POPULAR_ARTIST_LIMIT', 20))
    # Cache TTL for popular artist pool/pages
    POPULAR_ARTIST_CACHE_TTL_SECONDS = _get_int('POPULAR_ARTIST_CACHE_TTL_SECONDS', 900)
    # Target size for the cached popular-artist pool (fixed, app-controlled)
    POPULAR_ARTIST_POOL_SIZE = 500

    # Runtime behavior
    # Turn Flask debug on/off from env; default off to avoid noisy console
    DEBUG = _get_bool('DEBUG', False)
    # Control console logging; when disabled, logs go only to file
    ENABLE_CONSOLE_LOGS = _get_bool('ENABLE_CONSOLE_LOGS', False)

    # CD capacity configuration (minutes)
    # Primary target capacity (e.g., 80 for 80-min CD-R)
    CD_CAPACITY_MINUTES = _get_int('CD_CAPACITY_MINUTES', 80)
    # Optional secondary capacity to display (e.g., 74 for older 74-min discs). Set 0 to hide.
    CD_ALT_CAPACITY_MINUTES = _get_int('CD_ALT_CAPACITY_MINUTES', 74)


