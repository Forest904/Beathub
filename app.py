# app.py
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Flask specific imports ---
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
# Note: spotipy is now initialized within SpotifyContentDownloader, so no direct import here
# from spotipy.oauth2 import SpotifyClientCredentials # No longer needed here

# --- Import our new configuration and the main orchestrator ---
from config import Config
from src.spotify_content_downloader import SpotifyContentDownloader 

# --- Import db, DownloadedItem model (formerly Album), and the initialization function ---
from database.db_manager import db, DownloadedItem, initialize_database # Renamed Album to DownloadedItem

# --- Logger Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__, static_folder='build', static_url_path='')
    app.config.from_object(Config)
    CORS(app)

    # Initialize database
    initialize_database(app)

    # Initialize the main orchestrator (SpotifyContentDownloader)
    # It handles internal initialization of Spotipy, Genius, etc., using Config values
    spotify_downloader = SpotifyContentDownloader(
        base_output_dir=app.config.get('BASE_OUTPUT_DIR'),
        spotify_client_id=app.config.get('SPOTIPY_CLIENT_ID'),
        spotify_client_secret=app.config.get('SPOTIPY_CLIENT_SECRET'),
        genius_access_token=app.config.get('GENIUS_ACCESS_TOKEN')
    )

    # --- API Endpoints ---
    @app.route('/api/download', methods=['POST'])
    def download_spotify_item_api():
        data = request.get_json()
        spotify_link = data.get('spotify_link')

        if not spotify_link:
            return jsonify({"status": "error", "message": "Spotify link is required."}), 400

        logger.info(f"Received download request for: {spotify_link}")
        
        # Delegate the entire download process to the orchestrator
        result = spotify_downloader.download_spotify_content(spotify_link)

        if result["status"] == "success":
            # Extract relevant metadata from the result for DB storage
            # These values come directly from the orchestrator's return dictionary
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
            # This logic assumes your DownloadedItem model now has an 'item_type' column.
            # If you only want to store 'albums' in this table, change to `if item_type == "album":`
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
                            item_type=item_type # Pass the item_type to the model
                        )
                        db.session.add(new_item)
                        db.session.commit()
                        logger.info(f"Successfully added new {item_type} to DB: {new_item.title} (DB ID: {new_item.id})")
                    else:
                        # Update existing entry
                        logger.info(f"{item_type.capitalize()} '{existing_item.title}' already in DB (ID: {existing_item.id}). Checking for updates.")
                        # Check if local_path needs updating (e.g., if re-downloaded to a new path)
                        if existing_item.local_path != local_path:
                            existing_item.local_path = local_path
                            db.session.commit()
                            logger.info(f"Updated local_path for '{existing_item.title}' to '{local_path}'")
                        else:
                            logger.info(f"No update needed for existing {item_type} '{existing_item.title}'.")
                
                except Exception as e:
                    db.session.rollback() # IMPORTANT: Rollback the session in case of any database error
                    logger.error(f"DATABASE ERROR: Failed to save/update {item_type} '{title}' (ID: {spotify_id}) to DB: {e}", exc_info=True)
                    # You can decide to return an error to the client here, or just log and continue
                    # return jsonify({"status": "error", "message": f"Download successful, but DB save failed for {item_type}: {str(e)}"}), 500
            else:
                logger.warning(f"Unhandled item_type '{item_type}' encountered. Skipping DB storage for this item.")


            return jsonify(result), 200
        else:
            status_code = 500 if "unexpected" in result.get("message", "").lower() else 400
            return jsonify(result), status_code

    @app.route('/api/albums', methods=['GET'])
    def get_downloaded_items(): # Renamed function for consistency
        # Retrieves all items (albums, tracks, etc.) from the DownloadedItem table
        # You might want to filter by item_type here if needed, e.g., .filter_by(item_type='album')
        items = DownloadedItem.query.order_by(DownloadedItem.title).all()
        return jsonify([item.to_dict() for item in items]), 200 # Iterate through items and call .to_dict()

    @app.route('/api/albums/<int:item_id>/favorite', methods=['POST'])
    def toggle_favorite(item_id): # Renamed parameter for consistency
        item = DownloadedItem.query.get(item_id) # Use DownloadedItem model
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        item.is_favorite = not item.is_favorite
        db.session.commit()
        logger.info(f"Toggled favorite status for {item.item_type}: {item.title} to {item.is_favorite}")
        return jsonify({'success': True, 'is_favorite': item.is_favorite}), 200

    @app.route('/api/albums/<int:item_id>', methods=['DELETE'])
    def delete_downloaded_item(item_id): # Renamed function and parameter for consistency
        item = DownloadedItem.query.get(item_id) # Use DownloadedItem model
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        
        # Optional: Add logic here to delete the actual files from the local_path
        if item.local_path and os.path.exists(item.local_path):
            try:
                import shutil
                shutil.rmtree(item.local_path)
                logger.info(f"Successfully deleted local directory for {item.item_type}: {item.title} at {item.local_path}")
            except Exception as e:
                logger.error(f"Failed to delete local directory {item.local_path} for {item.title}: {e}", exc_info=True)
                # Decide if you want to abort DB deletion if file deletion fails
                return jsonify({'success': False, 'message': f'Failed to delete local files: {str(e)}'}), 500

        db.session.delete(item)
        db.session.commit()
        logger.info(f"Successfully deleted {item.item_type} '{item.title}' from DB.")
        return jsonify({'success': True, 'message': 'Item deleted successfully.'}), 200

    # --- Catch-all route for serving React app in production (remains the same) ---
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react_app(path):
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')
            
    return app

if __name__ == '__main__':
    # Ensure the base downloads directory exists when the app starts
    os.makedirs(Config.BASE_OUTPUT_DIR, exist_ok=True)
    
    # Check API credentials at startup
    if not Config.SPOTIPY_CLIENT_ID or not Config.SPOTIPY_CLIENT_SECRET:
        logger.warning("Spotify API client ID or client secret not found in environment variables.")
        logger.warning("Please set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET for full functionality.")
    if not Config.GENIUS_ACCESS_TOKEN:
        logger.warning("Genius API access token not found. Lyrics fetching will be unavailable.")

    # Create the app instance here
    app = create_app()
    logger.info("Starting Flask application...")
    app.run(debug=True, host='0.0.0.0', port=5000)