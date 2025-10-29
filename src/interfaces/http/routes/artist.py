import logging
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

artist_bp = Blueprint('artist_bp', __name__, url_prefix='/api')


def _ensure_spotify_ready():
    if not current_app.extensions.get("spotify_credentials_ready", False):
        return jsonify({"error": "Spotify credentials are not configured.", "code": "credentials_missing"}), 412
    return None


def get_download_orchestrator():
    from flask import current_app
    return current_app.extensions['download_orchestrator']

@artist_bp.route('/search_artists', methods=['GET'])
def search_artists_api():

    gate = _ensure_spotify_ready()
    if gate is not None:
        return gate
    spotify_downloader = get_download_orchestrator()
    query = request.args.get('q', '')
    if not query:
        # Keep response shape backward-compatible
        return jsonify({"artists": []})

    # Server-driven pagination parameters
    try:
        page = int(request.args.get('page', '1'))
    except ValueError:
        page = 1
    try:
        limit = int(request.args.get('limit', '20'))
    except ValueError:
        limit = 20
    page = max(1, page)
    # Spotify API caps at 50
    limit = min(max(1, limit), 50)
    offset = (page - 1) * limit

    try:
        sp = spotify_downloader.get_spotipy_instance()
        if not sp:
            return jsonify({"error": "Spotify API not initialized"}), 500

        results = sp.search(q=query, type='artist', limit=limit, offset=offset)
        artists = []
        for artist in results.get('artists', {}).get('items', []):
            images = artist.get('images') or []
            followers_obj = (artist.get('followers') or {})
            raw_followers = followers_obj.get('total')
            raw_popularity = artist.get('popularity')
            followers_available = isinstance(raw_followers, int)
            popularity_available = isinstance(raw_popularity, int)
            norm_followers = int(raw_followers) if isinstance(raw_followers, int) else 0
            norm_popularity = int(raw_popularity) if isinstance(raw_popularity, int) else 0
            artists.append({
                'id': artist.get('id'),
                'name': artist.get('name'),
                'genres': artist.get('genres', []),
                'followers': norm_followers,
                'popularity': norm_popularity,
                'followers_available': followers_available,
                'popularity_available': popularity_available,
                'image': images[0]['url'] if images else None,
                'external_urls': (artist.get('external_urls') or {}).get('spotify'),
            })

        total_items = (results.get('artists') or {}).get('total', 0)
        total_pages = max(1, (total_items + limit - 1) // max(1, limit)) if total_items else page
        has_next = bool((results.get('artists') or {}).get('next'))
        has_prev = bool((results.get('artists') or {}).get('previous'))

        return jsonify({
            "artists": artists,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_items,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
            }
        })
    except Exception as e:
        logger.error(f"Error searching artists: {e}", exc_info=True)
        return jsonify({"error": "Failed to search artists"}), 500

@artist_bp.route('/famous_artists', methods=['GET'])
def get_popular_artists_api():

    gate = _ensure_spotify_ready()
    if gate is not None:
        return gate
    spotify_downloader = get_download_orchestrator()
    sp = spotify_downloader.get_spotipy_instance()
    if not sp:
        return jsonify({"error": "Spotify API not initialized"}), 500

    limit_param = request.args.get('limit')
    page_param = request.args.get('page')
    market = request.args.get('market', 'US')
    order_by = (request.args.get('order_by') or 'popularity').strip().lower()
    order_dir = (request.args.get('order_dir') or 'desc').strip().lower()
    if order_by not in ('popularity', 'followers'):
        order_by = 'popularity'
    if order_dir not in ('asc', 'desc'):
        order_dir = 'desc'
    page = 1
    page_size = 20
    if page_param:
        try:
            page = max(1, int(page_param))
        except ValueError:
            page = 1
    if limit_param:
        try:
            page_size = max(1, int(limit_param))
        except ValueError:
            logger.warning(f"Invalid limit parameter for popular artists: {limit_param}")
            page_size = 20
    # Cap page size to a reasonable value
    page_size = min(page_size, 50)
    try:
        # Use full cached pool to support flexible ordering, then slice
        full_list = spotify_downloader.get_popular_artist_pool(market=market)
        # Normalize metrics (defensive in case of legacy cache entries)
        for a in full_list:
            if a is None:
                continue
            pop = a.get('popularity')
            fol = a.get('followers')
            a['popularity_available'] = bool(a.get('popularity_available')) if 'popularity_available' in a else isinstance(pop, int)
            a['followers_available'] = bool(a.get('followers_available')) if 'followers_available' in a else isinstance(fol, int)
            a['popularity'] = int(pop) if isinstance(pop, int) else 0
            a['followers'] = int(fol) if isinstance(fol, int) else 0

        reverse = (order_dir == 'desc')
        secondary = 'followers' if order_by == 'popularity' else 'popularity'
        full_list.sort(key=lambda d: (d.get(order_by, 0) or 0, d.get(secondary, 0) or 0), reverse=reverse)

        start = (page - 1) * page_size
        end = start + page_size
        artists = full_list[start:end]
        has_next = len(full_list) > end
        has_prev = page > 1
        total_items = len(full_list)
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        return jsonify({
            "artists": artists,
            "pagination": {
                "page": page,
                "limit": page_size,
                "total": total_items,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
            }
        })
    except Exception as e:
        logger.error(f"General error fetching famous artists: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve famous artists"}), 500

@artist_bp.route('/artist_details/<string:artist_id>', methods=['GET'])
def get_artist_details(artist_id):

    gate = _ensure_spotify_ready()
    if gate is not None:
        return gate
    spotify_downloader = get_download_orchestrator()
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

    gate = _ensure_spotify_ready()
    if gate is not None:
        return gate
    spotify_downloader = get_download_orchestrator()
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
