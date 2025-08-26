import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.metadata_service import MetadataService


def test_extract_id_from_url_handles_trailing_slash_and_query():
    service = MetadataService(spotify_client=None)
    base_url = "https://open.spotify.com/album/"
    assert service._extract_id_from_url(base_url + "12345") == "12345"
    assert service._extract_id_from_url(base_url + "12345/") == "12345"
    assert service._extract_id_from_url(base_url + "12345/?si=abc") == "12345"


def test_get_item_type_case_insensitive():
    service = MetadataService(spotify_client=None)
    assert service._get_item_type("https://open.spotify.com/ALBUM/12345") == "album"
    assert service._get_item_type("https://open.spotify.com/Track/12345") == "track"
    assert service._get_item_type("https://open.spotify.com/PLAYLIST/12345") == "playlist"
