import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

artist_bp = Blueprint('artist_bp', __name__, url_prefix='/api')

def get_spotify_downloader():
    from flask import current_app
    return current_app.extensions['spotify_downloader']

@artist_bp.route('/search_artists', methods=['GET'])
def search_artists_api():
    spotify_downloader = get_spotify_downloader()
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

@artist_bp.route('/famous_artists', methods=['GET'])
def get_popular_artists_api():
    spotify_downloader = get_spotify_downloader()
    sp = spotify_downloader.get_spotipy_instance()
    if not sp:
        return jsonify({"error": "Spotify API not initialized"}), 500

    limit_param = request.args.get('limit')
    market = request.args.get('market', 'US')
    limit = None
    if limit_param:
        try:
            limit = max(1, int(limit_param))
        except ValueError:
            logger.warning(f"Invalid limit parameter for popular artists: {limit_param}")
    try:
        artists = spotify_downloader.fetch_popular_artists(limit=limit, market=market)
        return jsonify({"artists": artists})
    except Exception as e:
        logger.error(f"General error fetching famous artists: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve famous artists"}), 500

@artist_bp.route('/artist_details/<string:artist_id>', methods=['GET'])
def get_artist_details(artist_id):
    spotify_downloader = get_spotify_downloader()
    sp = spotify_downloader.get_spotipy_instance()
    if not sp:
        return jsonify({"error": "Spotify API not initialized"}), 500
    try:
        details = spotify_downloader.fetch_artist_details(artist_id)
        if not details:
            return jsonify({"message": "Artist not found"}), 404
        logger.info(f"Fetched details for artist: {details['name']}")
        return jsonify(details), 200
    except Exception as e:
        logger.error(f"Error fetching artist details for ID {artist_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve artist details"}), 500

@artist_bp.route('/artist_discography/<string:artist_id>', methods=['GET'])
def get_artist_discography(artist_id):
    spotify_downloader = get_spotify_downloader()
    sp = spotify_downloader.get_spotipy_instance()
    if not sp:
        return jsonify({"error": "Spotify API not initialized"}), 500
    try:
        discography = spotify_downloader.fetch_artist_discography(artist_id)
        logger.info(f"Fetched discography for artist ID {artist_id}. Found {len(discography)} unique items.")
        return jsonify({"discography": discography}), 200
    except Exception as e:
        logger.error(f"Error fetching artist discography for ID {artist_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve artist discography"}), 500
