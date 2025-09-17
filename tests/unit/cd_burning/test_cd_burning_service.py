import json
import os
import re
from pathlib import Path

import pytest


import src.cd_burning_service as svc_mod
from src.burn_sessions import BurnSession


@pytest.mark.unit
def test_parse_spotify_metadata_album_and_track(tmp_path):
    # Album/playlist-like metadata
    album_meta = {
        'tracks': {
            'items': [
                {'track': {'name': 'Song One', 'artists': [{'name': 'Artist A'}]}},
                {'track': {'name': 'Two: Special/Chars*', 'artists': [{'name': 'Artist B'}]}},
            ]
        }
    }
    # Single track metadata
    single_meta = {
        'type': 'track',
        'name': 'Solo',
        'artists': [{'name': 'One Man'}],
    }

    # Write album meta
    content_dir_a = tmp_path / 'album'
    content_dir_a.mkdir()
    (content_dir_a / 'spotify_metadata.json').write_text(json.dumps(album_meta), encoding='utf-8')

    # Write single meta
    content_dir_s = tmp_path / 'single'
    content_dir_s.mkdir()
    (content_dir_s / 'spotify_metadata.json').write_text(json.dumps(single_meta), encoding='utf-8')

    svc = svc_mod.CDBurningService()

    tracks_a = svc._parse_spotify_metadata(str(content_dir_a))
    assert len(tracks_a) == 2
    assert tracks_a[0]['title'] == 'Song One' and tracks_a[0]['artist'] == 'Artist A'
    assert tracks_a[1]['title'] == 'Two: Special/Chars*' and tracks_a[1]['artist'] == 'Artist B'

    tracks_s = svc._parse_spotify_metadata(str(content_dir_s))
    assert len(tracks_s) == 1
    assert tracks_s[0]['title'] == 'Solo' and tracks_s[0]['artist'] == 'One Man'


class _DummyAudioSeg:
    def __init__(self, src):
        self._src = src

    @classmethod
    def from_mp3(cls, p):
        return cls(p)

    def set_frame_rate(self, r):
        return self

    def set_channels(self, c):
        return self

    def set_sample_width(self, w):
        return self

    def export(self, path, format='wav'):
        Path(path).write_bytes(b'WAVE')
        return path


@pytest.mark.unit
def test_convert_mp3_to_wav_filename_matching(monkeypatch, tmp_path):
    # Arrange content files
    content_dir = tmp_path / 'content'
    content_dir.mkdir()

    # Track with special chars in title; expect fallback pattern "Artist - <sanitized>.mp3"
    track1 = {'title': 'My: Song?*', 'artist': 'Foo'}
    # Sanitization mirrors service logic
    sanitized = re.sub(r'[\\/:*?"<>|]', '_', track1['title']).strip()
    sanitized = re.sub(r'_{2,}', '_', sanitized)
    (content_dir / f"{track1['artist']} - {sanitized}.mp3").write_bytes(b'MP3')

    # Track with exact title match
    track2 = {'title': 'Other', 'artist': 'Bar'}
    (content_dir / 'Other.mp3').write_bytes(b'MP3')

    # Monkeypatch AudioSegment
    monkeypatch.setattr(svc_mod, 'AudioSegment', _DummyAudioSeg, raising=True)

    # Prepare temp wav dir
    temp_wav_dir = tmp_path / 'wavs'
    temp_wav_dir.mkdir()

    sess = BurnSession(id='s1', title='t')
    svc = svc_mod.CDBurningService()
    wavs = svc._convert_mp3_to_wav(str(content_dir), [track1, track2], str(temp_wav_dir), session=sess)

    assert len(wavs) == 2
    # Check prefix numbering and sanitized naming
    assert os.path.basename(wavs[0]).startswith('01_') and os.path.basename(wavs[0]).endswith('.wav')
    assert os.path.basename(wavs[1]).startswith('02_') and os.path.basename(wavs[1]).endswith('.wav')


@pytest.mark.unit
def test_list_devices_with_status_imapi_unavailable(monkeypatch):
    monkeypatch.setattr(svc_mod.sys, 'platform', 'win32', raising=False)
    monkeypatch.setattr(svc_mod, 'IMAPI2AudioBurner', None, raising=False)
    svc = svc_mod.CDBurningService()
    with pytest.raises(svc_mod.IMAPIUnavailableError):
        svc.list_devices_with_status()


@pytest.mark.unit
def test_clear_selected_device_resets_state():
    svc = svc_mod.CDBurningService()
    svc._imapi_recorder = object()
    svc._imapi_recorder_id = 'DEV_A'
    assert svc.clear_selected_device() is True
    assert svc._imapi_recorder is None
    assert svc._imapi_recorder_id is None


class _FakeImapi:
    def __init__(self):
        self._rec = {}

    def list_recorders(self):
        return [
            {'unique_id': 'DEV_A', 'vendor_id': 'Acme', 'product_id': 'Writer', 'product_rev': '1', 'volume_paths': ('E:/',)},
            {'unique_id': 'DEV_B', 'vendor_id': 'Beta', 'product_id': 'Writer', 'product_rev': '1', 'volume_paths': ('F:/',)},
        ]

    def open_recorder(self, unique_id):
        obj = self._rec.get(unique_id)
        if obj is None:
            obj = object()
            self._rec[unique_id] = obj
        return obj, unique_id

    def check_audio_disc_ready(self, recorder):
        # Only recorder for DEV_A is considered ready
        return recorder is self._rec.get('DEV_A'), recorder is self._rec.get('DEV_A')


@pytest.mark.unit
def test_list_devices_with_status_and_selection(monkeypatch):
    # Force Windows path and make IMAPI available sentinel
    monkeypatch.setattr(svc_mod.sys, 'platform', 'win32', raising=False)
    monkeypatch.setattr(svc_mod, 'IMAPI2AudioBurner', object(), raising=False)

    svc = svc_mod.CDBurningService()
    svc._imapi = _FakeImapi()
    # Mark DEV_A as selected and active
    svc._imapi_recorder_id = 'DEV_A'
    svc._active_session_id = 'sess1'

    devices = svc.list_devices_with_status()
    assert isinstance(devices, list) and len(devices) == 2

    dev_a = next(d for d in devices if d['id'] == 'DEV_A')
    dev_b = next(d for d in devices if d['id'] == 'DEV_B')
    assert dev_a['present'] is True and dev_a['writable'] is True
    assert dev_b['present'] is False and dev_b['writable'] is False
    assert dev_a['selected'] is True and dev_a['active'] is True
    assert dev_b['selected'] is False


@pytest.mark.unit
def test_check_disc_status_updates_session(monkeypatch):
    svc = svc_mod.CDBurningService()
    sess = BurnSession(id='s2', title='t')

    # No recorder selected -> False and "No Burner Detected"
    ok = svc.check_disc_status(sess)
    assert ok is False
    d = sess.to_dict()
    assert d['burner_detected'] is False
    assert d['disc_present'] is False

    # Windows + fake IMAPI ready
    monkeypatch.setattr(svc_mod.sys, 'platform', 'win32', raising=False)
    monkeypatch.setattr(svc_mod, 'IMAPI2AudioBurner', object(), raising=False)
    f = _FakeImapi()
    svc._imapi = f
    rec, _ = f.open_recorder('DEV_A')
    svc._imapi_recorder = rec

    ok = svc.check_disc_status(sess)
    assert ok is True
    d = sess.to_dict()
    assert d['burner_detected'] is True
    assert d['disc_present'] is True
    assert d['disc_blank_or_erasable'] is True

