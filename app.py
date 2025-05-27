import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Flask specific imports ---
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# --- Import our new configuration and the main orchestrator ---
from config import Config
from src.spotify_content_downloader import SpotifyContentDownloader

# --- Import db, DownloadedItem model, and the initialization function ---
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

    @app.route('/api/albums', methods=['GET'])
    def get_downloaded_items():
        items = DownloadedItem.query.order_by(DownloadedItem.title).all()
        return jsonify([item.to_dict() for item in items]), 200


    @app.route('/api/albums/<int:item_id>', methods=['DELETE'])
    def delete_downloaded_item(item_id):
        item = DownloadedItem.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404

        if item.local_path and os.path.exists(item.local_path):
            try:
                import shutil
                shutil.rmtree(item.local_path)
                logger.info(f"Successfully deleted local directory for {item.item_type}: {item.title} at {item.local_path}")
            except Exception as e:
                logger.error(f"Failed to delete local directory {item.local_path} for {item.title}: {e}", exc_info=True)
                return jsonify({'success': False, 'message': f'Failed to delete local files: {str(e)}'}), 500

        db.session.delete(item)
        db.session.commit()
        logger.info(f"Successfully deleted {item.item_type} '{item.title}' from DB.")
        return jsonify({'success': True, 'message': 'Item deleted successfully.'}), 200

    @app.route('/api/search_artists', methods=['GET'])
    def search_artists_api():
        query = request.args.get('q', '')
        if not query:
            return jsonify({"artists": []})

        try:
            sp = spotify_downloader.get_spotipy_instance()
            if not sp:
                return jsonify({"error": "Spotify API not initialized"}), 500

            results = sp.search(q=query, type='artist', limit=20)
            artists = []
            for artist in results['artists']['items']:
                artists.append({
                    'id': artist['id'],
                    'name': artist['name'],
                    'genres': artist['genres'],
                    'followers': artist['followers']['total'],
                    'image': artist['images'][0]['url'] if artist['images'] else None,
                    'external_urls': artist['external_urls']['spotify']
                })
            return jsonify({"artists": artists})
        except Exception as e:
            logger.error(f"Error searching artists: {e}", exc_info=True)
            return jsonify({"error": "Failed to search artists"}), 500

    @app.route('/api/famous_artists', methods=['GET'])
    def get_famous_artists_api():
        famous_artist_names = [
            "Queen", "Michael Jackson", "The Beatles",
            "Taylor Swift", "Eminem", "Rihanna",
            "Coldplay", "Ariana Grande", "Post Malone",
            "Madonna", "Elton John", "The Rolling Stones",
            "Katy Perry", "Maroon 5", "U2",
        ]

        artists_data = []
        try:
            sp = spotify_downloader.get_spotipy_instance()
            if not sp:
                return jsonify({"error": "Spotify API not initialized"}), 500

            for name in famous_artist_names:
                try:
                    results = sp.search(q=name, type='artist', limit=1)
                    if results and results['artists']['items']:
                        artist = results['artists']['items'][0]
                        artists_data.append({
                            'id': artist['id'],
                            'name': artist['name'],
                            'genres': artist['genres'],
                            'followers': artist['followers']['total'],
                            'image': artist['images'][0]['url'] if artist['images'] else None,
                            'external_urls': artist['external_urls']['spotify']
                        })
                except Exception as e:
                    logger.warning(f"Error fetching data for famous artist {name}: {e}")
                    continue
            return jsonify({"artists": artists_data})
        except Exception as e:
            logger.error(f"General error fetching famous artists: {e}", exc_info=True)
            return jsonify({"error": "Failed to retrieve famous artists"}), 500

    @app.route('/api/artist_details/<string:artist_id>', methods=['GET'])
    def get_artist_details(artist_id):
        try:
            sp = spotify_downloader.get_spotipy_instance()
            if not sp:
                return jsonify({"error": "Spotify API not initialized"}), 500

            artist_data = sp.artist(artist_id)
            if not artist_data:
                return jsonify({"message": "Artist not found"}), 404

            details = {
                'id': artist_data['id'],
                'name': artist_data['name'],
                'genres': artist_data['genres'],
                'followers': artist_data['followers']['total'],
                'popularity': artist_data['popularity'],
                'image': artist_data['images'][0]['url'] if artist_data['images'] else None,
                'external_urls': artist_data['external_urls']['spotify']
            }
            logger.info(f"Fetched details for artist: {artist_data['name']}")
            return jsonify(details), 200

        except Exception as e:
            logger.error(f"Error fetching artist details for ID {artist_id}: {e}", exc_info=True)
            return jsonify({"error": "Failed to retrieve artist details"}), 500

    @app.route('/api/artist_discography/<string:artist_id>', methods=['GET'])
    def get_artist_discography(artist_id):
        try:
            sp = spotify_downloader.get_spotipy_instance()
            if not sp:
                return jsonify({"error": "Spotify API not initialized"}), 500

            albums_results = sp.artist_albums(artist_id, album_type='album,single', country='US', limit=50) # You can adjust limit and country
            if not albums_results:
                return jsonify({"discography": []}), 200

            discography = []
            seen_albums = set() # To filter out duplicates (e.g., deluxe versions, multiple markets)

            for album_data in albums_results['items']:
                # Use a unique identifier, e.g., combine album name and release date to check for uniqueness
                album_name_lower = album_data['name'].lower()
                if album_name_lower in seen_albums:
                    continue # Skip if we've already added this album name

                artists = [a['name'] for a in album_data.get('artists', [])]

                discography.append({
                    'id': album_data['id'],
                    'name': album_data['name'],
                    'album_type': album_data['album_type'],
                    'release_date': album_data.get('release_date'),
                    'total_tracks': album_data.get('total_tracks'),
                    'image_url': album_data['images'][0]['url'] if album_data['images'] else None,
                    'spotify_url': album_data['external_urls']['spotify'],
                    'artist': artists[0] if artists else 'Various Artists',
                    'artists': artists
                })
                seen_albums.add(album_name_lower)

            logger.info(f"Fetched discography for artist ID {artist_id}. Found {len(discography)} unique items.")
            return jsonify({"discography": discography}), 200

        except Exception as e:
            logger.error(f"Error fetching artist discography for ID {artist_id}: {e}", exc_info=True)
            return jsonify({"error": "Failed to retrieve artist discography"}), 500
        
    @app.route('/api/album_details/<string:album_id>', methods=['GET'])
    def get_album_details(album_id):
        """
        Fetches detailed information for a specific Spotify album, including its tracks,
        using the new get_album_by_id method.
        """
        try:
            album_metadata = spotify_downloader.metadata_service.get_album_by_id(album_id)

            if not album_metadata:
                logger.warning(f"Album not found for ID: {album_id}")
                return jsonify({"error": "Album not found"}), 404

            tracks_details = spotify_downloader.metadata_service.get_tracks_details(
                album_id,
                "album",
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