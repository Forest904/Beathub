#!/usr/bin/env python
"""Runtime application settings helpers."""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, Optional

from flask import Flask, current_app

from config import Config, basedir

_SETTINGS_FILENAME = "app-settings.json"
_SETTINGS_LOCK = threading.RLock()
_BOOL_TRUE = {"1", "true", "t", "yes", "y", "on"}

_API_KEY_FIELDS = {
    "spotify_client_id": {
        "env": "SPOTIPY_CLIENT_ID",
        "config_attr": "SPOTIPY_CLIENT_ID",
    },
    "spotify_client_secret": {
        "env": "SPOTIPY_CLIENT_SECRET",
        "config_attr": "SPOTIPY_CLIENT_SECRET",
    },
    "genius_access_token": {
        "env": "GENIUS_ACCESS_TOKEN",
        "config_attr": "GENIUS_ACCESS_TOKEN",
    },
}

_CONFIG_BASELINE = {
    meta["config_attr"]: getattr(Config, meta["config_attr"], None)
    for meta in _API_KEY_FIELDS.values()
}

_ENV_BASELINE = {
    meta["env"]: os.environ.get(meta["env"])
    for meta in _API_KEY_FIELDS.values()
}


def _resolve_app(app: Optional[Flask] = None) -> Optional[Flask]:
    if app is not None:
        return app
    try:
        return current_app._get_current_object()
    except Exception:
        return None


def _settings_path(app: Optional[Flask] = None) -> str:
    target_app = _resolve_app(app)
    base_dir = target_app.instance_path if target_app is not None else os.path.join(basedir, "instance")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, _SETTINGS_FILENAME)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in _BOOL_TRUE
    return bool(value)


def get_default_download_settings() -> Dict[str, Any]:
    return {
        "base_output_dir": Config.BASE_OUTPUT_DIR,
        "threads": max(1, int(getattr(Config, "SPOTDL_THREADS", 1) or 1)),
        "preload": bool(getattr(Config, "SPOTDL_PRELOAD", False)),
        "simple_tui": bool(getattr(Config, "SPOTDL_SIMPLE_TUI", True)),
    }


def _normalize_download_settings(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    defaults = get_default_download_settings()
    normalized = dict(defaults)
    if not isinstance(raw, dict):
        return normalized

    base_output_dir = str(raw.get("base_output_dir") or "").strip()
    if base_output_dir:
        normalized["base_output_dir"] = base_output_dir

    try:
        threads = int(raw.get("threads"))
        normalized["threads"] = max(1, min(threads, 32))
    except Exception:
        pass

    if "preload" in raw:
        normalized["preload"] = _coerce_bool(raw.get("preload"))

    normalized["simple_tui"] = False

    return normalized


def load_runtime_settings(app: Optional[Flask] = None) -> Dict[str, Any]:
    path = _settings_path(app)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_runtime_settings(data: Dict[str, Any], app: Optional[Flask] = None) -> None:
    path = _settings_path(app)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


def _load_api_key_store(app: Optional[Flask] = None) -> Dict[str, str]:
    current = load_runtime_settings(app).get("api_keys")
    if not isinstance(current, dict):
        return {}
    sanitized: Dict[str, str] = {}
    for field in _API_KEY_FIELDS:
        value = current.get(field)
        if isinstance(value, str):
            sanitized[field] = value
    return sanitized


def get_api_keys(app: Optional[Flask] = None) -> Dict[str, str]:
    with _SETTINGS_LOCK:
        return _load_api_key_store(app)


def describe_api_keys(api_keys: Optional[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
    description: Dict[str, Dict[str, Any]] = {}
    source = api_keys or {}
    for field in _API_KEY_FIELDS:
        value = source.get(field)
        entry: Dict[str, Any] = {"stored": bool(value), "source": "user" if field in source else "env"}
        if entry["stored"] and isinstance(value, str):
            preview = value[-4:] if len(value) >= 4 else value
            entry["preview"] = f"****{preview}"
        if field in source and not entry["stored"]:
            entry["cleared"] = True
        description[field] = entry
    return description


def persist_api_keys(updates: Optional[Dict[str, Any]], app: Optional[Flask] = None) -> Dict[str, str]:
    if not isinstance(updates, dict):
        return get_api_keys(app)

    with _SETTINGS_LOCK:
        data = load_runtime_settings(app)
        current = data.get("api_keys")
        if not isinstance(current, dict):
            current = {}
        stored: Dict[str, str] = dict(current)

        for field in _API_KEY_FIELDS:
            if field not in updates:
                continue
            raw_value = updates[field]
            if raw_value is None:
                stored.pop(field, None)
                continue
            value = str(raw_value).strip()
            stored[field] = value

        if stored:
            data["api_keys"] = stored
        else:
            data.pop("api_keys", None)
        save_runtime_settings(data, app)
        return dict(stored)


def apply_api_keys(
    app: Optional[Flask],
    api_keys: Optional[Dict[str, str]],
    *,
    refresh_client: bool = False,
) -> Dict[str, str]:
    raw_keys: Dict[str, str] = {}
    if isinstance(api_keys, dict):
        for field in _API_KEY_FIELDS:
            if field in api_keys:
                raw_val = api_keys[field]
                if isinstance(raw_val, str):
                    raw_keys[field] = raw_val

    normalized: Dict[str, Optional[str]] = {}
    for field in _API_KEY_FIELDS:
        if field in raw_keys:
            trimmed = raw_keys[field].strip()
            normalized[field] = trimmed if trimmed else ""
        else:
            normalized[field] = None

    target_app = _resolve_app(app)

    final_values: Dict[str, Optional[str]] = {}
    for field, meta in _API_KEY_FIELDS.items():
        env_name = meta["env"]
        attr = meta["config_attr"]
        value = normalized.get(field)
        if value is None:
            baseline_env = _ENV_BASELINE.get(env_name)
            if baseline_env is None:
                os.environ.pop(env_name, None)
            else:
                os.environ[env_name] = baseline_env
            final_value: Optional[str] = _CONFIG_BASELINE.get(attr)
        elif value == "":
            os.environ.pop(env_name, None)
            final_value = None
        else:
            os.environ[env_name] = value
            final_value = value
        final_values[attr] = final_value
        setattr(Config, attr, final_value)
        if target_app is not None:
            target_app.config[attr] = final_value

    spotify_client_id = final_values.get("SPOTIPY_CLIENT_ID")
    spotify_client_secret = final_values.get("SPOTIPY_CLIENT_SECRET")
    genius_access_token = final_values.get("GENIUS_ACCESS_TOKEN")

    if target_app is not None:
        orchestrator = target_app.extensions.get("download_orchestrator")
        if orchestrator is not None:
            try:
                from src.domain.catalog.metadata_service import MetadataService

                orchestrator._spotify_client_id = spotify_client_id
                orchestrator._spotify_client_secret = spotify_client_secret
                orchestrator.metadata_service = MetadataService(
                    spotify_client_id=spotify_client_id,
                    spotify_client_secret=spotify_client_secret,
                )
            except Exception:
                if target_app.logger:
                    target_app.logger.debug(
                        "Failed to refresh MetadataService with new Spotify credentials",
                        exc_info=True,
                    )
            try:
                from src.domain.catalog.lyrics_service import LyricsService

                orchestrator._genius_access_token = genius_access_token
                orchestrator.lyrics_service = LyricsService(genius_access_token=genius_access_token)
            except Exception:
                if target_app.logger:
                    target_app.logger.debug(
                        "Failed to refresh LyricsService with new Genius token",
                        exc_info=True,
                    )

    spotify_ready = bool(spotify_client_id and spotify_client_secret)
    genius_ready = bool(genius_access_token)
    if target_app is not None:
        target_app.extensions["spotify_credentials_ready"] = spotify_ready
        target_app.extensions["genius_credentials_ready"] = genius_ready
        if refresh_client:
            if spotify_ready:
                _refresh_spotdl_client(target_app, reason="API key update")
            else:
                _shutdown_spotdl_client(target_app)
        else:
            if not spotify_ready:
                target_app.extensions["spotdl_ready"] = False

    return normalized


def _shutdown_spotdl_client(target_app: Optional[Flask]) -> None:
    if target_app is None or not hasattr(target_app, "extensions"):
        return
    try:
        from src.infrastructure.spotdl import SpotdlClient  # type: ignore
    except Exception:
        SpotdlClient = None  # type: ignore
    old_client = target_app.extensions.get("spotdl_client")
    if SpotdlClient is not None and isinstance(old_client, SpotdlClient):
        try:
            old_client.shutdown()
        except Exception:
            if target_app.logger:
                target_app.logger.debug("Failed to shutdown existing SpotDL client", exc_info=True)
    target_app.extensions.pop("spotdl_client", None)
    target_app.extensions["spotdl_ready"] = False


def _refresh_spotdl_client(target_app: Optional[Flask], *, reason: str) -> bool:
    if target_app is None:
        return False

    _shutdown_spotdl_client(target_app)

    simple_tui_disabled = False
    spotify_reset = False
    last_error: Optional[Exception] = None

    for _ in range(3):
        try:
            from src.infrastructure.spotdl import build_default_client

            new_client = build_default_client(app_logger=target_app.logger)
        except Exception as exc:
            last_error = exc
            message = str(exc)
            if "LiveError: Only one live display may be active at once" in message and not simple_tui_disabled:
                if target_app.logger:
                    target_app.logger.warning(
                        "SpotDL client rebuild hit Rich LiveError; disabling simple TUI and retrying"
                    )
                os.environ["SPOTDL_SIMPLE_TUI"] = "0"
                Config.SPOTDL_SIMPLE_TUI = False
                if hasattr(target_app, "config"):
                    target_app.config["SPOTDL_SIMPLE_TUI"] = False
                simple_tui_disabled = True
                continue
            if "SpotifyError: A spotify client has already been initialized" in message and not spotify_reset:
                try:
                    from spotdl.utils.spotify import SpotifyClient  # type: ignore

                    SpotifyClient._instance = None  # type: ignore[attr-defined]
                except Exception:
                    pass
                if target_app.logger:
                    target_app.logger.warning(
                        "SpotDL client rebuild hit Spotify client singleton; resetting and retrying"
                    )
                spotify_reset = True
                continue
            if target_app.logger:
                target_app.logger.warning(
                    "Failed to rebuild SpotDL client after %s: %s",
                    reason,
                    exc,
                    exc_info=True,
                )
            target_app.extensions["spotdl_ready"] = False
            return False
        else:
            target_app.extensions["spotdl_client"] = new_client
            target_app.extensions["spotdl_ready"] = True
            orchestrator = target_app.extensions.get("download_orchestrator")
            if orchestrator is not None:
                orchestrator._spotdl_client = new_client
            return True

    if target_app.logger and last_error is not None:
        target_app.logger.warning(
            "Failed to rebuild SpotDL client after %s: %s",
            reason,
            last_error,
            exc_info=True,
        )
    target_app.extensions["spotdl_ready"] = False
    return False



def get_download_settings(app: Optional[Flask] = None) -> Dict[str, Any]:
    with _SETTINGS_LOCK:
        stored = load_runtime_settings(app).get("download")
    return _normalize_download_settings(stored)


def persist_download_settings(settings: Dict[str, Any], app: Optional[Flask] = None) -> Dict[str, Any]:
    normalized = _normalize_download_settings(settings)
    with _SETTINGS_LOCK:
        data = load_runtime_settings(app)
        data["download"] = normalized
        save_runtime_settings(data, app)
    return normalized


def apply_download_settings(app: Optional[Flask], settings: Dict[str, Any], *, refresh_client: bool = False) -> Dict[str, Any]:
    normalized = _normalize_download_settings(settings)
    target_app = _resolve_app(app)

    base_output_dir = normalized["base_output_dir"]
    threads = normalized["threads"]
    preload = normalized["preload"]
    simple_tui = normalized.get("simple_tui", True)

    os.environ["BASE_OUTPUT_DIR"] = base_output_dir
    os.environ["SPOTDL_THREADS"] = str(threads)
    os.environ["SPOTDL_PRELOAD"] = "1" if preload else "0"
    os.environ["SPOTDL_SIMPLE_TUI"] = "1" if simple_tui else "0"

    Config.BASE_OUTPUT_DIR = base_output_dir
    Config.SPOTDL_THREADS = threads
    Config.SPOTDL_PRELOAD = preload
    Config.SPOTDL_SIMPLE_TUI = simple_tui

    if target_app is not None:
        target_app.config["BASE_OUTPUT_DIR"] = base_output_dir
        target_app.config["SPOTDL_THREADS"] = threads
        target_app.config["SPOTDL_PRELOAD"] = preload
        target_app.config["SPOTDL_SIMPLE_TUI"] = simple_tui

        try:
            os.makedirs(base_output_dir, exist_ok=True)
        except Exception:
            if target_app.logger:
                target_app.logger.debug(
                    "Failed to ensure base output dir %s exists",
                    base_output_dir,
                    exc_info=True,
                )

        orchestrator = target_app.extensions.get("download_orchestrator")
        if orchestrator is not None:
            try:
                orchestrator.base_output_dir = base_output_dir
            except Exception:
                pass
            fm = getattr(orchestrator, "file_manager", None)
            if fm is not None and hasattr(fm, "base_output_dir"):
                fm.base_output_dir = base_output_dir
            dl_helpers = getattr(orchestrator, "audio_cover_download_service", None)
            if dl_helpers is not None and hasattr(dl_helpers, "base_output_dir"):
                dl_helpers.base_output_dir = base_output_dir

        cd_service = target_app.extensions.get("cd_burning_service")
        if cd_service is not None and hasattr(cd_service, "base_output_dir"):
            cd_service.base_output_dir = base_output_dir

        if refresh_client:
            if target_app.extensions.get("spotify_credentials_ready", False):
                _refresh_spotdl_client(target_app, reason="download settings update")
            else:
                _shutdown_spotdl_client(target_app)

    return normalized


__all__ = [
    "apply_download_settings",
    "apply_api_keys",
    "describe_api_keys",
    "get_default_download_settings",
    "get_download_settings",
    "get_api_keys",
    "load_runtime_settings",
    "persist_api_keys",
    "persist_download_settings",
]

