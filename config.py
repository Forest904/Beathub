# config.py
import os

# This assumes config.py is at the root of your project
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_super_secret_key_lmao' 
    
    # Updated Database URI to point to 'database/instance/site.db'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'database', 'instance', 'cd_collector.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SPOTIPY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')

    # Genius API credentials
    GENIUS_ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')

    # You can add other configurations here, e.g., default output directory
    BASE_OUTPUT_DIR = os.getenv('BASE_OUTPUT_DIR', 'downloads') # Default to 'downloads' if not set in .env