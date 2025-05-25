# config.py
import os

# Get the base directory of the project
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_key_change_me')

    # Construct the absolute path for the SQLite database file
    db_file_abs_path = os.path.join(basedir, "instance", "cd_collection.db")

    # IMPORTANT: Convert backslashes to forward slashes for the SQLite URI string
    # SQLite URIs prefer forward slashes even on Windows.
    db_uri_path_formatted = db_file_abs_path.replace('\\', '/')

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{db_uri_path_formatted}' # Use the forward-slash formatted path
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SPOTIPY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')