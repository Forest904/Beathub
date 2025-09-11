import os

# Centralized configuration values for services

# Paths
BASE_OUTPUT_DIR = os.getenv('BASE_OUTPUT_DIR', 'downloads')

# SpotDL defaults
SPOTDL_AUDIO_SOURCE = os.getenv('SPOTDL_AUDIO_SOURCE', 'youtube-music')
SPOTDL_FORMAT = os.getenv('SPOTDL_FORMAT', 'mp3')

# API tokens
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
GENIUS_ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')

