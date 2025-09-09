import os
import shutil
import logging
import threading
import hashlib
import json
import time
from flask import Blueprint, request, jsonify, Response, stream_with_context
from database.db_manager import db, DownloadedItem  # Corrected: relative to project root
from src.download_status_manager import DOWNLOAD_STATUS_MANAGER

logger = logging.getLogger(__name__)

download_bp = Blueprint('download_bp', __name__, url_prefix='/api')

# Helper function to get the SpotifyContentDownloader instance
def get_spotify_downloader():
    from flask import current_app
    return current_app.extensions['spotify_downloader']

@download_bp.route('/download', methods=['POST'])
def download_spotify_item_api():
    data = request.get_json()
    spotify_link = data.get('spotify_link')

    if not spotify_link:
        return jsonify({"status": "error", "message": "Spotify link is required."}), 400

    job_id = hashlib.sha1(spotify_link.encode()).hexdigest()[:16]
    DOWNLOAD_STATUS_MANAGER.create_job(job_id)
    logger.info("Received download request for %s with job id %s", spotify_link, job_id)

    spotify_downloader = get_spotify_downloader()

    # Capture the current Flask app to provide an application context in the thread
    from flask import current_app
    app = current_app._get_current_object()

    def _run_download(flask_app):
        # Ensure DB/session operations run within an application context
        with flask_app.app_context():
            try:
                result = spotify_downloader.download_spotify_content(spotify_link, job_id=job_id)
                if result.get("status") == "success":
                    item_type = result.get('item_type')
                    spotify_id = result.get('spotify_id')
                    title = result.get('item_name')
                    artist = result.get('artist')
                    image_url = result.get('cover_art_url')
                    spotify_url = result.get('spotify_url')
                    local_path = result.get('output_directory')

                    logger.info("Attempting to save to DB: Type='%s', ID='%s', Title='%s', Artist='%s'", item_type, spotify_id, title, artist)

                    if spotify_id and title and item_type in ["album", "track", "playlist"]:
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
                                    item_type=item_type,
                                )
                                db.session.add(new_item)
                                db.session.commit()
                                logger.info("Successfully added new %s to DB: %s", item_type, new_item.title)
                            else:
                                if existing_item.local_path != local_path:
                                    existing_item.local_path = local_path
                                    db.session.commit()
                                logger.info("No update needed for existing %s '%s'.", item_type, existing_item.title)
                        except Exception as e:
                            db.session.rollback()
                            logger.error("DATABASE ERROR: %s", e, exc_info=True)
            finally:
                # Ensure the scoped session is removed for this thread
                try:
                    db.session.remove()
                except Exception:
                    pass

    threading.Thread(target=_run_download, args=(app,), daemon=True).start()

    return jsonify({"job_id": job_id}), 202

@download_bp.route('/download/events/<job_id>')
def stream_download_events(job_id):
    def event_stream():
        while True:
            status = DOWNLOAD_STATUS_MANAGER.get_job(job_id)
            if not status:
                break
            yield f"data: {json.dumps(status)}\n\n"
            if status.get("finished"):
                DOWNLOAD_STATUS_MANAGER.reset_job(job_id)
                break
            time.sleep(1)

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')

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
