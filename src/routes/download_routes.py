import os
import shutil
import logging
from flask import Blueprint, request, jsonify
from database.db_manager import db, DownloadedItem # Corrected: relative to project root

logger = logging.getLogger(__name__)

download_bp = Blueprint('download_bp', __name__, url_prefix='/api')

# Helper function to get the SpotifyContentDownloader instance
def get_spotify_downloader():
    from flask import current_app
    return current_app.extensions['spotify_downloader']

@download_bp.route('/download', methods=['POST'])
def download_spotify_item_api():
    spotify_downloader = get_spotify_downloader()
    data = request.get_json()
    spotify_link = data.get('spotify_link')

    if not spotify_link:
        return jsonify({"status": "error", "message": "Spotify link is required."}), 400

    logger.info(f"Received download request for: {spotify_link}")

    # Delegate the entire download process to the orchestrator
    result = spotify_downloader.download_spotify_content(spotify_link)

    if result["status"] == "success":
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
            return jsonify(result), 200 # Still return success for download, but warn about DB

        # Determine if this item type should be stored in the DownloadedItem model
        if item_type in ["album", "track", "playlist"]:
            try:
                # Check if an entry with this spotify_id already exists
                existing_item = DownloadedItem.query.filter_by(spotify_id=spotify_id).first()

                if not existing_item:
                    # Create a new entry
                    logger.info(f"Creating new DB entry for {item_type}: '{title}' by '{artist}'")
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
                    logger.info(f"Successfully added new {item_type} to DB: {new_item.title} (DB ID: {new_item.id})")
                else:
                    # Update existing entry
                    logger.info(f"{item_type.capitalize()} '{existing_item.title}' already in DB (ID: {existing_item.id}). Checking for updates.")
                    if existing_item.local_path != local_path:
                        existing_item.local_path = local_path
                        db.session.commit()
                        logger.info(f"Updated local_path for '{existing_item.title}' to '{local_path}'")
                    else:
                        logger.info(f"No update needed for existing {item_type} '{existing_item.title}'.")

            except Exception as e:
                db.session.rollback()
                logger.error(f"DATABASE ERROR: Failed to save/update {item_type} '{title}' (ID: {spotify_id}) to DB: {e}", exc_info=True)
        else:
            logger.warning(f"Unhandled item_type '{item_type}' encountered. Skipping DB storage for this item.")

        return jsonify(result), 200
    else:
        status_code = 500 if "unexpected" in result.get("message", "").lower() else 400
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