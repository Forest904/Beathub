import os
import shutil
import logging
from flask import Blueprint, request, jsonify
import json
from src.database.db_manager import db, DownloadedItem

logger = logging.getLogger(__name__)

download_bp = Blueprint('download_bp', __name__, url_prefix='/api')

# Helper function to get the SpotifyContentDownloader instance
def get_spotify_downloader():
    from flask import current_app
    return current_app.extensions['spotify_downloader']

@download_bp.route('/download', methods=['POST'])
def download_spotify_item_api():
    from flask import current_app
    spotify_downloader = get_spotify_downloader()
    jobs = current_app.extensions.get('download_jobs')

    data = request.get_json() or {}
    spotify_link = data.get('spotify_link')
    async_mode = bool(data.get('async', False))

    if not spotify_link:
        return jsonify({"status": "error", "message": "Spotify link is required."}), 400

    logger.info(f"Received download request for: {spotify_link} (async={async_mode})")

    # If job queue is available, use it for idempotent handling and parallelism
    if jobs is not None:
        job = jobs.submit(spotify_link)
        if async_mode:
            return jsonify({"status": "accepted", "job_id": job.id, "link": spotify_link}), 202
        # Synchronous path: wait for completion
        result = jobs.wait(job.id)
    else:
        # Direct call when no job queue is configured
        result = spotify_downloader.download_spotify_content(spotify_link)

    if not isinstance(result, dict):
        return jsonify({"status": "error", "message": "Unexpected orchestrator response."}), 500

    if result.get("status") == "success":
        # Extract relevant metadata from the result for DB storage
        item_type = result.get('item_type')
        spotify_id = result.get('spotify_id')
        title = result.get('item_name')
        artist = result.get('artist')
        image_url = result.get('cover_art_url')
        spotify_url = result.get('spotify_url')
        local_path = result.get('output_directory')

        logger.info(f"Attempting to save to DB: Type='{item_type}', ID='{spotify_id}', Title='{title}', Artist='{artist}'")

        # Validate essential fields before attempting DB save
        if not spotify_id or not title:
            logger.warning(f"Missing crucial data for DB save (Spotify ID or Title). Skipping DB storage for {spotify_link}.")
            return jsonify(result), 200

        # Determine if this item type should be stored in the DownloadedItem model
        if item_type in ["album", "track", "playlist"]:
            try:
                existing_item = DownloadedItem.query.filter_by(spotify_id=spotify_id).first()
                if not existing_item:
                    new_item = DownloadedItem(
                        spotify_id=spotify_id,
                        title=title,
                        artist=artist,
                        image_url=image_url,
                        spotify_url=spotify_url,
                        local_path=local_path,
                        item_type=item_type
                    )
                    db.session.add(new_item)
                    db.session.commit()
                    logger.info(f"Added {item_type} to DB: {new_item.title} (ID: {new_item.id})")
                else:
                    if existing_item.local_path != local_path:
                        existing_item.local_path = local_path
                        db.session.commit()
                        logger.info(f"Updated local_path for '{existing_item.title}' to '{local_path}'")
            except Exception as e:
                db.session.rollback()
                logger.error(f"DATABASE ERROR: Failed to save/update {item_type} '{title}' (ID: {spotify_id}) to DB: {e}", exc_info=True)
        else:
            logger.warning(f"Unhandled item_type '{item_type}' encountered. Skipping DB storage for this item.")

        return jsonify(result), 200

    # Error mapping to HTTP status
    message = result.get("message", "")
    error_code = result.get("error_code")
    status_code = 500 if error_code in ("provider_error", "internal_error") else 400
    return jsonify(result), status_code

@download_bp.route('/albums', methods=['GET'])
def get_downloaded_items():
    items = DownloadedItem.query.order_by(DownloadedItem.title).all()
    return jsonify([item.to_dict() for item in items]), 200

@download_bp.route('/albums/<int:item_id>', methods=['DELETE'])
def delete_downloaded_item(item_id):
    item = DownloadedItem.query.get(item_id)
    if not item:
        return jsonify({'success': False, 'message': 'Item not found'}), 404

    if item.local_path and os.path.exists(item.local_path):
        try:
            shutil.rmtree(item.local_path)
            logger.info(f"Successfully deleted local directory for {item.item_type}: {item.title} at {item.local_path}")
        except Exception as e:
            logger.error(f"Failed to delete local directory {item.local_path} for {item.title}: {e}", exc_info=True)
            return jsonify({'success': False, 'message': f'Failed to delete local files: {str(e)}'}), 500

    db.session.delete(item)
    db.session.commit()
    logger.info(f"Successfully deleted {item.item_type} '{item.title}' from DB.")
    return jsonify({'success': True, 'message': 'Item deleted successfully.'}), 200


@download_bp.route('/items/<int:item_id>/metadata', methods=['GET'])
def get_item_metadata_by_id(item_id: int):
    """Return the saved spotify_metadata.json for a downloaded item by DB id."""
    item = DownloadedItem.query.get(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    if not item.local_path:
        return jsonify({'error': 'Local path not available for this item'}), 404

    metadata_path = os.path.join(item.local_path, 'spotify_metadata.json')
    if not os.path.exists(metadata_path):
        return jsonify({'error': 'Metadata not found'}), 404
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data), 200
    except Exception as e:
        logger.error("Failed to read metadata for item %s: %s", item_id, e, exc_info=True)
        return jsonify({'error': 'Failed to read metadata'}), 500


@download_bp.route('/items/by-spotify/<string:spotify_id>/metadata', methods=['GET'])
def get_item_metadata_by_spotify(spotify_id: str):
    """Return the saved spotify_metadata.json for a downloaded item by Spotify id."""
    item = DownloadedItem.query.filter_by(spotify_id=spotify_id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    if not item.local_path:
        return jsonify({'error': 'Local path not available for this item'}), 404

    metadata_path = os.path.join(item.local_path, 'spotify_metadata.json')
    if not os.path.exists(metadata_path):
        return jsonify({'error': 'Metadata not found'}), 404
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data), 200
    except Exception as e:
        logger.error("Failed to read metadata for spotify %s: %s", spotify_id, e, exc_info=True)
        return jsonify({'error': 'Failed to read metadata'}), 500
