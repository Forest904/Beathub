import importlib

import pytest


def _reload_mapping():
    import src.models.spotdl_mapping as mapping
    return importlib.reload(mapping)


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
def test_song_to_track_dto_full_mapping(tmp_path, spotdl_song_stub):
    mapping = _reload_mapping()

    json_data = _make_json()
    song = spotdl_song_stub(json_data)

    local_path = tmp_path / "A.mp3"
    local_lyrics = tmp_path / "A.txt"
    track = mapping.song_to_track_dto(song, local_path=local_path, local_lyrics_path=local_lyrics)

    assert track.spotify_id == json_data["song_id"]
    assert track.title == json_data["name"]
    assert track.artists == json_data["artists"]
    assert track.album_name == json_data["album_name"]
    assert track.album_id == json_data["album_id"]
    assert track.album_artist == json_data["album_artist"]
    assert track.duration_ms == json_data["duration"] * 1000
    assert track.track_number == json_data["track_number"]
    assert track.disc_number == json_data["disc_number"]
    assert track.disc_count == json_data["disc_count"]
    assert track.tracks_count == json_data["tracks_count"]
    assert track.explicit == json_data["explicit"]
    assert track.popularity == json_data["popularity"]
    assert track.isrc == json_data["isrc"]
    assert track.publisher == json_data["publisher"]
    assert track.year == json_data["year"]
    assert track.date == json_data["date"]
    assert track.genres == json_data["genres"]
    assert track.spotify_url == json_data["url"]
    assert track.cover_url == json_data["cover_url"]
    assert track.local_path == str(local_path)
    assert track.local_lyrics_path == str(local_lyrics)


@pytest.mark.unit
def test_songs_to_item_dto_single_and_multi(spotdl_song_stub):
    mapping = _reload_mapping()

    song_cls = spotdl_song_stub
    s1 = song_cls(_make_json(song_id="s1", name="N1", album_name="ALB"))
    s2 = song_cls(_make_json(song_id="s2", name="N2", album_name="ALB"))

    one = mapping.songs_to_item_dto([s1], spotify_link="link1")
    assert one.item_type == "track"
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
def test_songs_to_item_dto_cover_override(spotdl_song_stub):
    mapping = _reload_mapping()

    song = spotdl_song_stub(_make_json(cover_url="http://default/cover.jpg"))
    dto = mapping.songs_to_item_dto([song], cover_url_override="http://override/cover.jpg")
    assert dto.cover_url == "http://override/cover.jpg"


@pytest.mark.unit
def test_songs_to_item_dto_empty_raises(spotdl_song_stub):
    mapping = _reload_mapping()
    with pytest.raises(ValueError):
        mapping.songs_to_item_dto([])


@pytest.mark.unit
def test_trackdto_to_db_kwargs_matches_fields(tmp_path, spotdl_song_stub):
    mapping = _reload_mapping()

    song = spotdl_song_stub(_make_json())
    track = mapping.song_to_track_dto(song, local_path=tmp_path / "A.mp3", local_lyrics_path=tmp_path / "A.txt")
    data = mapping.trackdto_to_db_kwargs(track)

    for key in (
        "spotify_id",
        "title",
        "artists",
        "album_name",
        "album_id",
        "album_artist",
        "duration_ms",
        "track_number",
        "disc_number",
        "disc_count",
        "tracks_count",
        "explicit",
        "popularity",
        "isrc",
        "publisher",
        "year",
        "date",
        "genres",
        "spotify_url",
        "cover_url",
        "local_path",
        "local_lyrics_path",
    ):
        assert key in data
        assert data[key] == getattr(track, key)
