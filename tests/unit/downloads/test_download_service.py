from io import BytesIO
import os
import types

import pytest


@pytest.mark.unit
def test_download_cover_image_no_url(tmp_path):
    from src.download_service import AudioCoverDownloadService

    svc = AudioCoverDownloadService(base_output_dir=str(tmp_path))
    assert svc.download_cover_image("", str(tmp_path)) is None


@pytest.mark.unit
def test_download_cover_image_success(tmp_path, monkeypatch):
    from src.download_service import AudioCoverDownloadService
    import src.download_service as ds

    class Resp:
        def __init__(self):
            self.status_code = 200
        def raise_for_status(self):
            return None
        def iter_content(self, chunk_size=8192):
            yield b"hello"
            yield b"world"

    def fake_get(url, stream=True, timeout=15):
        return Resp()

    monkeypatch.setattr(ds.requests, "get", fake_get)

    svc = AudioCoverDownloadService(base_output_dir=str(tmp_path))
    out = svc.download_cover_image("http://example/cover.jpg", str(tmp_path))
    assert out is not None
    with open(out, "rb") as f:
        assert f.read() == b"helloworld"


@pytest.mark.unit
def test_download_cover_image_timeout(tmp_path, monkeypatch):
    from src.download_service import AudioCoverDownloadService
    import src.download_service as ds
    import requests

    def fake_get(url, stream=True, timeout=15):
        raise requests.exceptions.Timeout("slow")

    monkeypatch.setattr(ds.requests, "get", fake_get)
    svc = AudioCoverDownloadService(base_output_dir=str(tmp_path))
    assert svc.download_cover_image("http://example/cover.jpg", str(tmp_path)) is None


@pytest.mark.unit
def test_download_cover_image_request_exception(tmp_path, monkeypatch):
    from src.download_service import AudioCoverDownloadService
    import src.download_service as ds
    import requests

    def fake_get(url, stream=True, timeout=15):
        raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr(ds.requests, "get", fake_get)
    svc = AudioCoverDownloadService(base_output_dir=str(tmp_path))
    assert svc.download_cover_image("http://example/cover.jpg", str(tmp_path)) is None


@pytest.mark.unit
def test_download_cover_image_ioerror_on_write(tmp_path, monkeypatch):
    from src.download_service import AudioCoverDownloadService
    import src.download_service as ds

    class Resp:
        def __init__(self):
            self.status_code = 200
        def raise_for_status(self):
            return None
        def iter_content(self, chunk_size=8192):
            yield b"abc"

    def fake_get(url, stream=True, timeout=15):
        return Resp()

    monkeypatch.setattr(ds.requests, "get", fake_get)

    svc = AudioCoverDownloadService(base_output_dir=str(tmp_path))
    target = os.path.join(str(tmp_path), "cover.jpg")

    real_open = open
    def bad_open(path, *args, **kwargs):
        if os.path.abspath(path) == os.path.abspath(target):
            raise IOError("disk full")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", bad_open, raising=True)
    assert svc.download_cover_image("http://example/cover.jpg", str(tmp_path)) is None

