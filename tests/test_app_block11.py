import logging
import os

import pytest


@pytest.mark.unit
def test_configure_logging_creates_file_and_is_idempotent(tmp_path, monkeypatch):
    import app as app_module
    import config as cfg

    # Ensure console logs disabled for this test
    monkeypatch.setattr(cfg.Config, "ENABLE_CONSOLE_LOGS", False, raising=True)

    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level
    try:
        log_dir = tmp_path / "logs"
        path1 = app_module.configure_logging(str(log_dir))
        assert os.path.exists(path1)

        # One file handler pointing to the returned file
        fhs = [h for h in logging.getLogger().handlers if isinstance(h, logging.FileHandler)]
        assert len(fhs) == 1
        assert os.path.abspath(fhs[0].baseFilename) == os.path.abspath(path1)

        # Second call should not duplicate handlers (still exactly one file handler)
        path2 = app_module.configure_logging(str(log_dir))
        fhs2 = [h for h in logging.getLogger().handlers if isinstance(h, logging.FileHandler)]
        assert len(fhs2) == 1
        assert os.path.exists(path2)
    finally:
        # Restore root logger state
        root.handlers = old_handlers
        root.setLevel(old_level)


@pytest.mark.unit
def test_configure_logging_respects_console_toggle(tmp_path, monkeypatch):
    import app as app_module
    import config as cfg

    # Enable console logs
    monkeypatch.setattr(cfg.Config, "ENABLE_CONSOLE_LOGS", True, raising=True)

    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level
    try:
        app_module.configure_logging(str(tmp_path / "logs"))
        sh = [h for h in logging.getLogger().handlers if isinstance(h, logging.StreamHandler)]
        # Expect at least one stream handler at WARNING level
        assert any(h.level == logging.WARNING for h in sh)
    finally:
        root.handlers = old_handlers
        root.setLevel(old_level)


@pytest.mark.unit
def test_create_app_registers_blueprints_and_extensions(monkeypatch):
    import app as app_module

    # Avoid initializing real SpotDL client
    monkeypatch.setattr(app_module, "build_default_client", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("skip")), raising=True)

    application = app_module.create_app()

    # Blueprints are registered
    for bp in ("download_bp", "artist_bp", "album_details_bp", "progress_bp", "cd_burning_bp"):
        assert bp in application.blueprints

    # Core extensions are present
    assert "spotify_downloader" in application.extensions
    assert "progress_broker" in application.extensions
    assert "cd_burning_service" in application.extensions
    # Job queue should also be initialized
    assert "download_jobs" in application.extensions

