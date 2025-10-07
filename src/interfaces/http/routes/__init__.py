"""Route blueprints exposed via Flask."""

from .download import download_bp
from .artist import artist_bp
from .album_details import album_details_bp
from .cd_burning import cd_burning_bp
from .progress import progress_bp
from .config import config_bp
from .auth import auth_bp
from .compilation import compilation_bp

__all__ = [
    "download_bp",
    "artist_bp",
    "album_details_bp",
    "cd_burning_bp",
    "progress_bp",
    "config_bp",
    "auth_bp",
    "compilation_bp",
]
