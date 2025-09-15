import sys
import types
import importlib
from pathlib import Path

import pytest


def _install_song_stub():
    """Install a stub for spotdl.types.song.Song before importing mapping module."""
    m_spotdl = types.ModuleType("spotdl")
    m_types = types.ModuleType("spotdl.types")
    m_song = types.ModuleType("spotdl.types.song")

    class Song:
        def __init__(self, json_dict):
            self._json = json_dict
            # Expose attributes used by songs_to_item_dto
            self.artist = json_dict.get("artists", ["Unknown"])[0]
            self.album_name = json_dict.get("album_name")
            self.name = json_dict.get("name")
            self.cover_url = json_dict.get("cover_url")

        @property
        def json(self):
            return self._json

    m_song.Song = Song
    sys.modules["spotdl"] = m_spotdl
    sys.modules["spotdl.types"] = m_types
    sys.modules["spotdl.types.song"] = m_song
    return Song


def _reload_mapping():
    # Ensure a fresh import picks up our stub
    if "src.models.spotdl_mapping" in sys.modules:
        del sys.modules["src.models.spotdl_mapping"]
    import src.models.spotdl_mapping as mapping
    importlib.reload(mapping)
    return mapping


def _make_json(
    song_id="sid1",
    name="Track 1",
    artists=None,
    album_name="Album A",
    duration=180,
    track_number=1,
    disc_number=1,
    disc_count=1,
    tracks_count=10,
    explicit=False,
    popularity=50,
    isrc="ISRC123",
    publisher="Label",
    year=2020,
    date="2020-01-01",
    genres=None,
    url="https://open.spotify.com/track/sid1",
    cover_url="http://example.com/c.jpg",
):
    if artists is None:
        artists = ["Artist X"]
    return {
        "song_id": song_id,
        "name": name,
        "artists": artists,
        "album_name": album_name,
        "album_id": "alb1",
        "album_artist": artists[0],
        "duration": duration,
        "track_number": track_number,
        "disc_number": disc_number,
        "disc_count": disc_count,
        "tracks_count": tracks_count,
        "explicit": explicit,
        "popularity": popularity,
        "isrc": isrc,
        "publisher": publisher,
        "year": year,
        "date": date,
        "genres": genres or ["pop"],
        "url": url,
        "cover_url": cover_url,
    }


@pytest.mark.unit
def test_song_to_track_dto_full_mapping(tmp_path):
    _install_song_stub()
    mapping = _reload_mapping()

    json_data = _make_json()
    Song = sys.modules["spotdl.types.song"].Song
    s = Song(json_data)

    local_path = tmp_path / "A.mp3"
    local_lyrics = tmp_path / "A.txt"
    t = mapping.song_to_track_dto(s, local_path=local_path, local_lyrics_path=local_lyrics)

    assert t.spotify_id == json_data["song_id"]
    assert t.title == json_data["name"]
    assert t.artists == json_data["artists"]
    assert t.album_name == json_data["album_name"]
    assert t.album_id == json_data["album_id"]
    assert t.album_artist == json_data["album_artist"]
    assert t.duration_ms == json_data["duration"] * 1000
    assert t.track_number == json_data["track_number"]
    assert t.disc_number == json_data["disc_number"]
    assert t.disc_count == json_data["disc_count"]
    assert t.tracks_count == json_data["tracks_count"]
    assert t.explicit == json_data["explicit"]
    assert t.popularity == json_data["popularity"]
    assert t.isrc == json_data["isrc"]
    assert t.publisher == json_data["publisher"]
    assert t.year == json_data["year"]
    assert t.date == json_data["date"]
    assert t.genres == json_data["genres"]
    assert t.spotify_url == json_data["url"]
    assert t.cover_url == json_data["cover_url"]
    assert t.local_path == str(local_path)
    assert t.local_lyrics_path == str(local_lyrics)


@pytest.mark.unit
def test_songs_to_item_dto_single_and_multi():
    _install_song_stub()
    mapping = _reload_mapping()

    Song = sys.modules["spotdl.types.song"].Song
    s1 = Song(_make_json(song_id="s1", name="N1", album_name="ALB"))
    s2 = Song(_make_json(song_id="s2", name="N2", album_name="ALB"))

    one = mapping.songs_to_item_dto([s1], spotify_link="link1")
    assert one.item_type == "track"
    # Title derived from album_name if present
    assert one.title == "ALB"
    assert one.artist == "Artist X"
    assert one.spotify_link == "link1"
    assert len(one.tracks) == 1

    many = mapping.songs_to_item_dto([s1, s2], spotify_link="link2")
    assert many.item_type == "album"
    assert many.title == "ALB"
    assert many.cover_url is not None
    assert len(many.tracks) == 2


@pytest.mark.unit
def test_songs_to_item_dto_cover_override():
    _install_song_stub()
    mapping = _reload_mapping()

    Song = sys.modules["spotdl.types.song"].Song
    s1 = Song(_make_json(cover_url="http://default/cover.jpg"))
    dto = mapping.songs_to_item_dto([s1], cover_url_override="http://override/cover.jpg")
    assert dto.cover_url == "http://override/cover.jpg"


@pytest.mark.unit
def test_songs_to_item_dto_empty_raises():
    _install_song_stub()
    mapping = _reload_mapping()
    with pytest.raises(ValueError):
        mapping.songs_to_item_dto([])


@pytest.mark.unit
def test_trackdto_to_db_kwargs_matches_fields(tmp_path):
    _install_song_stub()
    mapping = _reload_mapping()

    Song = sys.modules["spotdl.types.song"].Song
    s = Song(_make_json())
    t = mapping.song_to_track_dto(s, local_path=tmp_path / "A.mp3", local_lyrics_path=tmp_path / "A.txt")
    data = mapping.trackdto_to_db_kwargs(t)

    # Ensure mapping contains expected keys and values
    for key in (
        "spotify_id","title","artists","album_name","album_id","album_artist",
        "duration_ms","track_number","disc_number","disc_count","tracks_count",
        "explicit","popularity","isrc","publisher","year","date","genres",
        "spotify_url","cover_url","local_path","local_lyrics_path",
    ):
        assert key in data
        assert data[key] == getattr(t, key)

