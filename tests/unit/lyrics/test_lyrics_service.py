import os
from types import SimpleNamespace

import pytest


@pytest.mark.unit
def test_extract_returns_none_when_file_missing(tmp_path):
    from src.lyrics_service import LyricsService

    svc = LyricsService()
    missing = tmp_path / "nope.mp3"
    assert svc.extract_lyrics_from_audio(str(missing)) is None


@pytest.mark.unit
def test_extract_mp3_uslt_frames(tmp_path, monkeypatch):
    import src.lyrics_service as ls
    from src.lyrics_service import LyricsService

    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"")

    class MP3Stub:  # used for isinstance check
        pass

    class ID3Stub:
        def __init__(self, path):
            self._path = path
        def getall(self, name):
            if name == 'USLT':
                return [SimpleNamespace(text=["Line1", "Line2"])]
            return []

    def MutagenFileStub(path, easy=False):
        return MP3Stub()

    monkeypatch.setattr(ls, "MutagenFile", MutagenFileStub, raising=True)
    monkeypatch.setattr(ls, "MP3", MP3Stub, raising=True)
    monkeypatch.setattr(ls, "ID3", ID3Stub, raising=True)

    svc = LyricsService()
    out = svc.extract_lyrics_from_audio(str(audio))
    assert out == "Line1\nLine2"


@pytest.mark.unit
def test_extract_mp4_lyr_atom(tmp_path, monkeypatch):
    import src.lyrics_service as ls
    from src.lyrics_service import LyricsService

    audio = tmp_path / "a.m4a"
    audio.write_bytes(b"")

    class MP4Stub:
        def __init__(self):
            self.tags = {'lyr': ['Hello', 'World']}

    def MutagenFileStub(path, easy=False):
        return MP4Stub()

    monkeypatch.setattr(ls, "MutagenFile", MutagenFileStub, raising=True)
    monkeypatch.setattr(ls, "MP4", MP4Stub, raising=True)

    svc = LyricsService()
    out = svc.extract_lyrics_from_audio(str(audio))
    assert out == "Hello\nWorld"


@pytest.mark.unit
def test_extract_flac_vorbis_comments(tmp_path, monkeypatch):
    import src.lyrics_service as ls
    from src.lyrics_service import LyricsService

    audio = tmp_path / "a.flac"
    audio.write_bytes(b"")

    class OtherStub:
        def __init__(self):
            self.tags = {'lyrics': ['A', 'B']}

    def MutagenFileStub(path, easy=False):
        return OtherStub()

    # Ensure MP3/MP4 isinstance checks fail
    class MP3Stub: pass
    class MP4Stub: pass
    monkeypatch.setattr(ls, "MutagenFile", MutagenFileStub, raising=True)
    monkeypatch.setattr(ls, "MP3", MP3Stub, raising=True)
    monkeypatch.setattr(ls, "MP4", MP4Stub, raising=True)

    svc = LyricsService()
    out = svc.extract_lyrics_from_audio(str(audio))
    assert out == "A\nB"


@pytest.mark.unit
def test_export_embedded_lyrics_writes_txt(tmp_path, monkeypatch):
    import src.lyrics_service as ls
    from src.lyrics_service import LyricsService

    audio = tmp_path / "song.mp3"
    audio.write_bytes(b"")

    def fake_extract(path):
        return "Some lyrics here"

    monkeypatch.setattr(ls.LyricsService, "extract_lyrics_from_audio", staticmethod(fake_extract))

    svc = LyricsService()
    out_txt = svc.export_embedded_lyrics(str(audio))
    assert out_txt is not None
    assert os.path.exists(out_txt)
    with open(out_txt, 'r', encoding='utf-8') as f:
        assert f.read() == "Some lyrics here"


@pytest.mark.unit
def test_export_embedded_lyrics_handles_write_error(tmp_path, monkeypatch):
    import src.lyrics_service as ls
    from src.lyrics_service import LyricsService

    audio = tmp_path / "song.mp3"
    audio.write_bytes(b"")

    monkeypatch.setattr(ls.LyricsService, "extract_lyrics_from_audio", staticmethod(lambda p: "Lyrics"))

    real_open = open
    def bad_open(path, *args, **kwargs):
        raise IOError("disk full")

    monkeypatch.setattr("builtins.open", bad_open, raising=True)
    svc = LyricsService()
    assert svc.export_embedded_lyrics(str(audio)) is None

