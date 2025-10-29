import logging
from flask import Blueprint, jsonify, current_app
from flask_login import current_user, login_required

from src.support.user_settings import ensure_user_api_keys_applied, user_has_spotify_credentials

logger = logging.getLogger(__name__)

album_details_bp = Blueprint('album_details_bp', __name__, url_prefix='/api')


def _ensure_spotify_ready():
    keys = ensure_user_api_keys_applied(current_user)
    if not user_has_spotify_credentials(keys):
        return jsonify({"error": "Spotify credentials are not configured.", "code": "credentials_missing"}), 412
    if not current_app.extensions.get("spotdl_ready", False):
        return jsonify({"error": "The download engine is not ready yet.", "code": "spotdl_unavailable"}), 503
    return None


def get_download_orchestrator():
    from flask import current_app
    return current_app.extensions['download_orchestrator']

@album_details_bp.route('/album_details/<string:album_id>', methods=['GET'])
@login_required
def get_album_details(album_id):
    """
    Fetches detailed information for a specific Spotify album, including its tracks,
    using the metadata service within DownloadOrchestrator.
    """
    gate = _ensure_spotify_ready()
    if gate is not None:
        return gate
    spotify_downloader = get_download_orchestrator()
    try:
        # Synthetic "Best Of" album for an artist: album_id format 'bestof:<artist_id>'
        if album_id.startswith('bestof:'):
            artist_id = album_id.split(':', 1)[1]
            best_of = spotify_downloader.build_best_of_album_details(artist_id)
            if not best_of:
                logger.warning(f"Best-Of album could not be built for artist: {artist_id}")
                return jsonify({"error": "Best-Of not available"}), 404
            return jsonify(best_of), 200

        # Assuming metadata_service is an attribute of DownloadOrchestrator
        # and has get_album_by_id and get_tracks_details methods.
        album_metadata = spotify_downloader.metadata_service.get_album_by_id(album_id)

        if not album_metadata:
            logger.warning(f"Album not found for ID: {album_id}")
            return jsonify({"error": "Album not found"}), 404

        tracks_details = spotify_downloader.metadata_service.get_tracks_details(
            album_id,
            "album", # Assuming type is always 'album' for album details
            album_metadata.get('image_url')
        )

        album_full_details = {
            "spotify_id": album_metadata.get('spotify_id'),
            "title": album_metadata.get('title'),
            "artist": album_metadata.get('artist'),
            "image_url": album_metadata.get('image_url'),
            "spotify_url": album_metadata.get('spotify_url'),
            "release_date": album_metadata.get('release_date'),
            "total_tracks": album_metadata.get('total_tracks'),
            "tracks": tracks_details
        }

        return jsonify(album_full_details), 200

    except Exception as e:
        logger.exception(f"Error fetching album details for ID {album_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500

