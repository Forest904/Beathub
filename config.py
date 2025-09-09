# config.py
import os
from dotenv import load_dotenv

# This assumes config.py is at the root of your project
basedir = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from a `.env` file located at the project root.
# This ensures that Spotify and Genius credentials are picked up even when they
# aren't exported in the shell environment.
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_super_secret_key_lmao' 
    
    # Updated Database URI to point to 'database/instance/cd_collector.db'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'database', 'instance', 'cd_collector.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SPOTIPY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')

    # Genius API credentials
    GENIUS_ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')

    # You can add other configurations here, e.g., default output directory
    BASE_OUTPUT_DIR = os.getenv('BASE_OUTPUT_DIR', 'downloads') # Default to 'downloads' if not set in .env