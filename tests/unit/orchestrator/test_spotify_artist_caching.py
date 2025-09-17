import pytest

from src.spotify_content_downloader import SpotifyContentDownloader


class _PopularArtistsSpotipyStub:
    def __init__(self):
        self.playlist_items_calls = 0
        self.next_calls = 0
        self.artists_calls = 0

    def playlist_items(self, playlist_id, limit=100, market=None):
        self.playlist_items_calls += 1
        return {
            'items': [
                {'track': {'artists': [{'id': 'a1'}, {'id': 'a2'}]}},
                {'track': {'artists': [{'id': 'a3'}]}}
            ],
            'next': None,
        }

    def next(self, payload):  # pragma: no cover - not triggered in this stub
        self.next_calls += 1
        return payload

    def artists(self, ids):
        self.artists_calls += 1
        artists = []
        for idx, artist_id in enumerate(ids):
            artists.append({
                'id': artist_id,
                'name': artist_id.upper(),
                'genres': ['pop'],
                'followers': {'total': 1000 - (idx * 10)},
                'popularity': 90 - idx,
                'images': [{'url': f'http://images/{artist_id}.jpg'}],
                'external_urls': {'spotify': f'https://spotify.com/{artist_id}'},
            })
        return {'artists': artists}

class _FallbackSpotipyStub:
    def __init__(self):
        self.search_calls = 0

    def playlist_items(self, playlist_id, limit=100, market=None):
        return {'items': [], 'next': None}

    def next(self, payload):  # pragma: no cover - pagination unused in fallback
        return payload

    def artists(self, ids):  # pragma: no cover - fallback path bypasses this
        return {'artists': []}

    def search(self, q, type=None, market=None, limit=None):
        self.search_calls += 1
        return {
            'artists': {
                'items': [
                    {
                        'id': 'fb1',
                        'name': 'Fallback One',
                        'genres': ['pop'],
                        'followers': {'total': 1500},
                        'popularity': 95,
                        'images': [{'url': 'http://images/fb1.jpg'}],
                        'external_urls': {'spotify': 'https://spotify.com/fb1'},
                    },
                    {
                        'id': 'fb2',
                        'name': 'Fallback Two',
                        'genres': ['rock'],
                        'followers': {'total': 900},
                        'popularity': 88,
                        'images': [{'url': 'http://images/fb2.jpg'}],
                        'external_urls': {'spotify': 'https://spotify.com/fb2'},
                    },
                ]
            }
        }


class _ArtistDetailSpotipyStub:
    def __init__(self):
        self.calls = 0

    def artist(self, artist_id):
        self.calls += 1
        return {
            'id': artist_id,
            'name': f'Artist {artist_id}',
            'genres': ['rock'],
            'followers': {'total': 321},
            'popularity': 77,
            'images': [{'url': 'http://image/artist.jpg'}],
            'external_urls': {'spotify': f'https://spotify.com/{artist_id}'},
        }


class _DiscographySpotipyStub:
    def __init__(self):
        self.albums_calls = 0
        self.next_calls = 0

    def artist_albums(self, artist_id, album_type=None, country=None, limit=None):
        self.albums_calls += 1
        return {
            'items': [
                {
                    'id': 'alb1',
                    'name': 'First Hit',
                    'album_type': 'album',
                    'release_date': '2024-01-01',
                    'total_tracks': 10,
                    'images': [{'url': 'http://img/a1.jpg'}],
                    'external_urls': {'spotify': 'https://spotify.com/alb1'},
                    'artists': [{'name': 'The Band'}],
                },
                {
                    'id': 'alb2',
                    'name': 'Second Hit',
                    'album_type': 'album',
                    'release_date': '2024-02-02',
                    'total_tracks': 9,
                    'images': [{'url': 'http://img/a2.jpg'}],
                    'external_urls': {'spotify': 'https://spotify.com/alb2'},
                    'artists': [{'name': 'The Band'}],
                },
            ],
            'next': 'next-page',
        }

    def next(self, payload):
        self.next_calls += 1
        return {
            'items': [
                {
                    'id': 'alb3',
                    'name': 'Second Hit',  # Duplicate title should be ignored
                    'album_type': 'single',
                    'release_date': '2024-03-03',
                    'total_tracks': 1,
                    'images': [{'url': 'http://img/a3.jpg'}],
                    'external_urls': {'spotify': 'https://spotify.com/alb3'},
                    'artists': [{'name': 'The Band'}],
                }
            ],
            'next': None,
        }



@pytest.mark.unit
def test_fetch_popular_artists_batches_and_caches():
    downloader = SpotifyContentDownloader()
    stub = _PopularArtistsSpotipyStub()
    downloader.sp = stub
    downloader._popular_artist_playlist_ids = ['playlist-1']
    downloader._popular_artist_limit = 2

    first = downloader.fetch_popular_artists()
    assert [artist['id'] for artist in first] == ['a1', 'a2']
    assert stub.artists_calls == 1

    second = downloader.fetch_popular_artists()
    assert [artist['id'] for artist in second] == ['a1', 'a2']
    assert stub.artists_calls == 1, 'expected cached popular artists to avoid repeat lookups'


@pytest.mark.unit
def test_fetch_popular_artists_fallback_uses_genre_search():
    downloader = SpotifyContentDownloader()
    stub = _FallbackSpotipyStub()
    downloader.sp = stub
    downloader._popular_artist_playlist_ids = ['playlist-unavailable']
    downloader._popular_artist_limit = 2

    artists = downloader.fetch_popular_artists()

    assert stub.search_calls >= 1
    assert [artist['id'] for artist in artists] == ['fb1', 'fb2']


@pytest.mark.unit
def test_fetch_artist_details_uses_cache():
    downloader = SpotifyContentDownloader()
    stub = _ArtistDetailSpotipyStub()
    downloader.sp = stub

    first = downloader.fetch_artist_details('artist-42')
    second = downloader.fetch_artist_details('artist-42')

    assert stub.calls == 1
    assert first == second
    assert first['popularity'] == 77


@pytest.mark.unit
def test_fetch_artist_discography_dedupes_and_caches():
    downloader = SpotifyContentDownloader()
    stub = _DiscographySpotipyStub()
    downloader.sp = stub

    discs = downloader.fetch_artist_discography('artist-1')
    assert len(discs) == 2
    assert stub.albums_calls == 1

    discs_again = downloader.fetch_artist_discography('artist-1')
    assert stub.albums_calls == 1
    assert discs_again == discs
