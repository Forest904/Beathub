import json
import os
from unittest.mock import patch

import pytest


@pytest.mark.unit
def test_sanitize_filename_removes_forbidden_chars():
    from src.file_manager import FileManager

    fm = FileManager(base_output_dir="downloads-test")
    name = '  AC/DC: Greatest*Hits? "Edition" <2020> | Disc/1  '
    sanitized = fm.sanitize_filename(name)

    # No forbidden characters remain
    for ch in '\\/:*?"<>|':
        assert ch not in sanitized
    # Trim and collapse underscores
    assert sanitized == sanitized.strip()
    assert "__" not in sanitized


@pytest.mark.unit
def test_create_item_output_directory_creates_expected_path(tmp_path):
    from src.file_manager import FileManager

    fm = FileManager(base_output_dir=str(tmp_path))
    out = fm.create_item_output_directory("AC/DC", "Best: of? yes")

    assert out is not None
    assert os.path.isdir(out)
    # Directory name should contain sanitized artist and title
    base = os.path.basename(out)
    assert "AC_DC" in base
    assert "Best_ of_ yes" in base


@pytest.mark.unit
def test_save_metadata_json_success(tmp_path):
    from src.file_manager import FileManager

    fm = FileManager(base_output_dir=str(tmp_path))
    out_dir = tmp_path / "X"
    out_dir.mkdir()
    meta = {"a": 1, "b": [1, 2, 3]}
    path = fm.save_metadata_json(str(out_dir), meta)

    assert path is not None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == meta


@pytest.mark.unit
def test_save_metadata_json_ioerror(tmp_path, monkeypatch):
    from src.file_manager import FileManager

    fm = FileManager(base_output_dir=str(tmp_path))
    out_dir = tmp_path / "Y"
    out_dir.mkdir()

    target = os.path.join(str(out_dir), "spotify_metadata.json")

    real_open = open

    def bad_open(path, *args, **kwargs):
        if os.path.abspath(path) == os.path.abspath(target):
            raise IOError("disk full")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", bad_open, raising=True)
    res = fm.save_metadata_json(str(out_dir), {"z": 1})
    assert res is None

