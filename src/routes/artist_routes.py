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
def get_famous_artists_api():
    spotify_downloader = get_spotify_downloader()
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

@artist_bp.route('/artist_details/<string:artist_id>', methods=['GET'])
def get_artist_details(artist_id):
    spotify_downloader = get_spotify_downloader()
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

@artist_bp.route('/artist_discography/<string:artist_id>', methods=['GET'])
def get_artist_discography(artist_id):
    spotify_downloader = get_spotify_downloader()
    try:
        sp = spotify_downloader.get_spotipy_instance()
        if not sp:
            return jsonify({"error": "Spotify API not initialized"}), 500

        albums_results = sp.artist_albums(artist_id, album_type='album,single', country='US', limit=50)
        if not albums_results:
            return jsonify({"discography": []}), 200

        discography = []
        seen_albums = set()

        for album_data in albums_results['items']:
            album_name_lower = album_data['name'].lower()
            if album_name_lower in seen_albums:
                continue

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