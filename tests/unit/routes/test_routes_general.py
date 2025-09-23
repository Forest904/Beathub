import json
import os
import uuid


def test_download_route_success_stores_item(app, client, monkeypatch):
    # Force direct path (no job queue)
    app.extensions['download_jobs'] = None

    # Stub orchestrator to return success
    def _mock_download(link: str):
        return {
            "status": "success",
            "item_type": "album",
            "spotify_id": "test123",
            "item_name": "Test Album",
            "artist": "Test Artist",
            "cover_art_url": "http://example/cover.jpg",
            "spotify_url": "https://open.spotify.com/album/test123",
            "output_directory": "downloads/Test Artist - Test Album",
        }

    app.extensions['spotify_downloader'].download_spotify_content = _mock_download

    resp = client.post('/api/download', json={"spotify_link": "https://open.spotify.com/album/test123"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["item_name"] == "Test Album"

    # Verify the item is visible via list endpoint
    r2 = client.get('/api/albums')
    assert r2.status_code == 200
    items = r2.get_json()
    assert any(it.get('spotify_id') == 'test123' for it in items)


def test_download_route_missing_link_returns_400(client):
    resp = client.post('/api/download', json={})
    assert resp.status_code == 400


def test_download_route_async_accepted_with_job_queue(app, client):
    # Stub a lightweight job queue
    class FakeJob:
        def __init__(self):
            self.id = "job-1"

    class FakeQueue:
        def submit(self, link):
            return FakeJob()

        def wait(self, job_id):
            return {"status": "success", "item_name": "Queued", "item_type": "track", "spotify_id": "q1"}

    app.extensions['download_jobs'] = FakeQueue()

    r = client.post('/api/download', json={"spotify_link": "https://open.spotify.com/track/1", "async": True})
    assert r.status_code == 202
    data = r.get_json()
    assert data.get('job_id') == 'job-1'

    # Synchronous path should return the final result via wait()
    r2 = client.post('/api/download', json={"spotify_link": "https://open.spotify.com/track/1", "async": False})
    assert r2.status_code == 200
    d2 = r2.get_json()
    assert d2['status'] == 'success'
    assert d2['item_name'] == 'Queued'


def test_progress_stream_with_stub_broker(app, client):
    class StubBroker:
        def subscribe(self):
            yield 'data: {"ok": 1}\n\n'

    app.extensions['progress_broker'] = StubBroker()

    resp = client.get('/api/progress/stream')
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type') == 'text/event-stream'
    content = resp.data.decode('utf-8')
    assert 'data: {"ok": 1}' in content


def test_progress_stream_503_when_broker_missing(app, client):
    app.extensions['progress_broker'] = None
    resp = client.get('/api/progress/stream')
    assert resp.status_code == 503


def test_delete_downloaded_item_removes_files_and_db(app, client, tmp_path):
    # Create a dummy row and local directory
    from src.database.db_manager import db, DownloadedItem
    with app.app_context():
        local_dir = tmp_path / 'to_remove'
        local_dir.mkdir(parents=True)
        item = DownloadedItem(
            spotify_id='del123', title='T', artist='A', item_type='album', local_path=str(local_dir)
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # Sanity
    assert os.path.isdir(local_dir)

    # Delete via API
    r = client.delete(f'/api/albums/{item_id}')
    assert r.status_code == 200
    assert not os.path.exists(local_dir)

    # Ensure gone from DB
    with app.app_context():
        assert DownloadedItem.query.get(item_id) is None


def test_metadata_endpoints_by_id_and_spotify(app, client, tmp_path):
    from src.database.db_manager import db, DownloadedItem
    # Setup an item with metadata on disk
    mdir = tmp_path / 'meta'
    mdir.mkdir(parents=True)
    meta_path = mdir / 'spotify_metadata.json'
    meta_path.write_text('{"hello": "world"}', encoding='utf-8')

    with app.app_context():
        spotify_id = f"test-{uuid.uuid4().hex}"
        item = DownloadedItem(
            spotify_id=spotify_id, title='MT', artist='AR', item_type='album', local_path=str(mdir)
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # By id
    r1 = client.get(f'/api/items/{item_id}/metadata')
    assert r1.status_code == 200
    assert r1.get_json().get('hello') == 'world'

    # By spotify id
    r2 = client.get(f'/api/items/by-spotify/{spotify_id}/metadata')
    assert r2.status_code == 200
    assert r2.get_json().get('hello') == 'world'
