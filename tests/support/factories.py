"""Factory Boy factories for database models used in tests."""

import factory
from factory.alchemy import SQLAlchemyModelFactory

from src.database.db_manager import DownloadedItem, DownloadedTrack


class _BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "flush"


class DownloadedItemFactory(_BaseFactory):
    class Meta:
        model = DownloadedItem

    spotify_id = factory.Sequence(lambda n: f"item-{n}")
    title = factory.Sequence(lambda n: f"Title {n}")
    artist = factory.Sequence(lambda n: f"Artist {n}")
    image_url = factory.LazyAttribute(lambda obj: f"http://images/{obj.spotify_id}.jpg")
    spotify_url = factory.LazyAttribute(lambda obj: f"https://open.spotify.com/item/{obj.spotify_id}")
    local_path = factory.LazyAttribute(lambda obj: f"/downloads/{obj.spotify_id}")
    is_favorite = False
    item_type = "album"


class DownloadedTrackFactory(_BaseFactory):
    class Meta:
        model = DownloadedTrack

    spotify_id = factory.Sequence(lambda n: f"track-{n}")
    spotify_url = factory.LazyAttribute(lambda obj: f"https://open.spotify.com/track/{obj.spotify_id}")
    isrc = factory.Sequence(lambda n: f"ISRC{n:04d}")
    title = factory.Sequence(lambda n: f"Track {n}")
    artists = factory.LazyFunction(lambda: ["Artist"])
    album_name = "Album"
    album_id = factory.Sequence(lambda n: f"album-{n}")
    album_artist = "Artist"
    track_number = 1
    disc_number = 1
    disc_count = 1
    tracks_count = 1
    duration_ms = 180000
    explicit = False
    popularity = 10
    publisher = "Label"
    year = 2020
    date = "2020-01-01"
    genres = factory.LazyFunction(lambda: ["genre"])
    cover_url = factory.LazyAttribute(lambda obj: f"http://images/{obj.spotify_id}.jpg")
    local_path = factory.LazyAttribute(lambda obj: f"/downloads/{obj.spotify_id}.mp3")
    local_lyrics_path = factory.LazyAttribute(lambda obj: f"/downloads/{obj.spotify_id}.lrc")
    item = factory.SubFactory(DownloadedItemFactory)


_FACTORIES = [DownloadedItemFactory, DownloadedTrackFactory]


def set_session(session):
    for factory_cls in _FACTORIES:
        factory_cls._meta.sqlalchemy_session = session


def reset_session():
    for factory_cls in _FACTORIES:
        factory_cls._meta.sqlalchemy_session = None


__all__ = [
    "DownloadedItemFactory",
    "DownloadedTrackFactory",
    "set_session",
    "reset_session",
]
