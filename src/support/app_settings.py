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

    if "simple_tui" in raw:
        normalized["simple_tui"] = _coerce_bool(raw.get("simple_tui"))

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
                target_app.logger.debug("Failed to ensure base output dir %s exists", base_output_dir, exc_info=True)

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
            from src.infrastructure.spotdl import SpotdlClient, build_default_client

            target_app.extensions["spotdl_ready"] = False
            old_client = target_app.extensions.get("spotdl_client")
            try:
                if isinstance(old_client, SpotdlClient):
                    old_client.shutdown()
            except Exception:
                if target_app.logger:
                    target_app.logger.debug("Failed to shutdown existing SpotDL client", exc_info=True)
            try:
                new_client = build_default_client(app_logger=target_app.logger)
            except Exception as exc:  # pragma: no cover - defensive logging
                target_app.logger.warning("Failed to rebuild SpotDL client after settings update: %s", exc, exc_info=True)
                target_app.extensions["spotdl_ready"] = False
            else:
                target_app.extensions["spotdl_client"] = new_client
                target_app.extensions["spotdl_ready"] = True
                orchestrator = target_app.extensions.get("download_orchestrator")
                if orchestrator is not None:
                    orchestrator._spotdl_client = new_client

    return normalized


__all__ = [
    "apply_download_settings",
    "get_default_download_settings",
    "get_download_settings",
    "load_runtime_settings",
    "persist_download_settings",
]
