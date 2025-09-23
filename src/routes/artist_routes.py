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
            artists.append({
                'id': artist.get('id'),
                'name': artist.get('name'),
                'genres': artist.get('genres', []),
                'followers': (artist.get('followers') or {}).get('total'),
                'image': images[0]['url'] if images else None,
                'external_urls': (artist.get('external_urls') or {}).get('spotify'),
                'popularity': artist.get('popularity'),
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
    spotify_downloader = get_spotify_downloader()
    sp = spotify_downloader.get_spotipy_instance()
    if not sp:
        return jsonify({"error": "Spotify API not initialized"}), 500

    limit_param = request.args.get('limit')
    page_param = request.args.get('page')
    market = request.args.get('market', 'US')
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
    # Fetch enough to determine next-page availability (+1 sentinel)
    internal_limit = page * page_size + 1
    # Soft cap to avoid excessive work
    internal_limit = min(internal_limit, 500)
    try:
        full_list = spotify_downloader.fetch_popular_artists(limit=internal_limit, market=market)
        start = (page - 1) * page_size
        end = start + page_size
        artists = full_list[start:end]
        has_next = len(full_list) > end
        has_prev = page > 1
        # We don't have a true total from the data source; expose lower-bound
        total_lower_bound = len(full_list) if not has_next else end + 1
        total_pages = max(1, (total_lower_bound + page_size - 1) // page_size)
        return jsonify({
            "artists": artists,
            "pagination": {
                "page": page,
                "limit": page_size,
                "total": total_lower_bound,
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


@artist_bp.route('/artist_top_tracks/<string:artist_id>', methods=['GET'])
def get_artist_top_tracks(artist_id):
    spotify_downloader = get_spotify_downloader()
    sp = spotify_downloader.get_spotipy_instance()
    if not sp:
        return jsonify({"error": "Spotify API not initialized"}), 500

    market = request.args.get('market', 'US')
    try:
        tracks = spotify_downloader.fetch_artist_top_tracks(artist_id, market=market)
        return jsonify({"tracks": tracks}), 200
    except Exception as e:
        logger.error(f"Error fetching artist top tracks for ID {artist_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve artist top tracks"}), 500
