import os
import pytest
from tests.support.stubs import SpotipySearchStub


@pytest.mark.unit
def test_delete_nonexistent_item_returns_404(client):
    r = client.delete('/api/albums/999999')
    assert r.status_code == 404


@pytest.mark.unit
def test_metadata_by_id_missing_file_returns_404(app, client, tmp_path):
    from src.database.db_manager import db, DownloadedItem
    # Add an item with a local_path that exists but no metadata file
    mdir = tmp_path / 'no_meta'
    mdir.mkdir(parents=True)
    with app.app_context():
        it = DownloadedItem(
            spotify_id='x1', title='T', artist='A', item_type='album', local_path=str(mdir)
        )
        db.session.add(it)
        db.session.commit()
        item_id = it.id

    r = client.get(f'/api/items/{item_id}/metadata')
    assert r.status_code == 404


@pytest.mark.unit
def test_progress_stream_heartbeat_headers_and_body(app, client):
    class HB:
        def subscribe(self):
            yield 'event: heartbeat\n' + 'data: {"ts": 123}\n\n'

    app.extensions['progress_broker'] = HB()
    resp = client.get('/api/progress/stream')
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type') == 'text/event-stream'
    body = resp.data.decode('utf-8')
    assert 'event: heartbeat' in body


@pytest.mark.unit
def test_download_route_provider_error_maps_to_500(app, client):
    def _err(link: str):
        return {"status": "error", "error_code": "provider_error", "message": "x"}

    app.extensions['spotify_downloader'].download_spotify_content = _err
    # Force direct path (bypass job queue) to preserve error_code mapping
    app.extensions['download_jobs'] = None
    r = client.post('/api/download', json={"spotify_link": "https://open.spotify.com/track/1"})
    assert r.status_code == 500


@pytest.mark.unit
def test_download_route_unexpected_response_500(app, client):
    app.extensions['spotify_downloader'].download_spotify_content = lambda link: "oops"
    # Force direct path to exercise unexpected-response branch
    app.extensions['download_jobs'] = None
    r = client.post('/api/download', json={"spotify_link": "https://open.spotify.com/track/1"})
    assert r.status_code == 500


@pytest.mark.unit
def test_artist_search_success(app, client, monkeypatch):
    response = {
        'artists': {
            'items': [
                {
                    'id': 'a1',
                    'name': 'Artist One',
                    'genres': ['pop'],
                    'followers': {'total': 100},
                    'images': [{'url': 'http://img/a1.jpg'}],
                    'external_urls': {'spotify': 'http://spotify/a1'}
                }
            ]
        }
    }

    app.extensions['spotify_downloader'].get_spotipy_instance = lambda: SpotipySearchStub(response=response)
    r = client.get('/api/search_artists?q=queen')
    assert r.status_code == 200
    data = r.get_json()
    assert data['artists'] and data['artists'][0]['name'] == 'Artist One'


@pytest.mark.unit
def test_artist_search_no_query_returns_empty(client):
    r = client.get('/api/search_artists')
    assert r.status_code == 200
    assert r.get_json() == {"artists": []}


@pytest.mark.unit
def test_artist_search_error_returns_500(app, client):
    app.extensions['spotify_downloader'].get_spotipy_instance = lambda: SpotipySearchStub(error=RuntimeError('boom'))
    r = client.get('/api/search_artists?q=x')
    assert r.status_code == 500


@pytest.mark.unit
def test_album_details_success(app, client, monkeypatch):
    sd = app.extensions['spotify_downloader']

    class Meta:
        def get_album_by_id(self, album_id):
            return {
                'spotify_id': album_id,
                'title': 'Album',
                'artist': 'AR',
                'image_url': 'http://img/a.jpg',
                'spotify_url': 'http://s',
                'release_date': '2020-01-01',
                'total_tracks': 2,
            }

        def get_tracks_details(self, album_id, typ, image_url):
            return [
                {'spotify_id': 't1', 'title': 'T1', 'artists': ['AR'], 'duration_ms': 1000, 'track_number': 1,
                 'disc_number': 1, 'explicit': False, 'spotify_url': 'http://t1', 'album_image_url': image_url}
            ]

    sd.metadata_service = Meta()
    r = client.get('/api/album_details/abc')
    assert r.status_code == 200
    body = r.get_json()
    assert body['spotify_id'] == 'abc'
    assert len(body['tracks']) == 1


@pytest.mark.unit
def test_album_details_not_found_returns_404(app, client):
    sd = app.extensions['spotify_downloader']

    class Meta:
        def get_album_by_id(self, album_id):
            return None

        def get_tracks_details(self, *a, **kw):
            return []

    sd.metadata_service = Meta()
    r = client.get('/api/album_details/abc')
    assert r.status_code == 404


@pytest.mark.unit
def test_album_details_error_returns_500(app, client):
    sd = app.extensions['spotify_downloader']

    class Meta:
        def get_album_by_id(self, album_id):
            raise RuntimeError('boom')

        def get_tracks_details(self, *a, **kw):
            return []

    sd.metadata_service = Meta()
    r = client.get('/api/album_details/abc')
    assert r.status_code == 500
