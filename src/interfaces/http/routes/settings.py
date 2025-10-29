#!/usr/bin/env python
"""Settings API endpoints."""

from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from src.support.app_settings import (
    apply_api_keys,
    apply_download_settings,
    describe_api_keys,
    get_api_keys,
    get_default_download_settings,
    get_download_settings,
    persist_api_keys,
    persist_download_settings,
)

logger = logging.getLogger(__name__)

settings_bp = Blueprint("settings_bp", __name__, url_prefix="/api/settings")


class DownloadSettingsPayload(BaseModel):
    base_output_dir: str = Field(min_length=1, max_length=512)
    threads: int = Field(ge=1, le=32)
    preload: bool
    simple_tui: bool | None = None

    @field_validator("base_output_dir")
    @classmethod
    def _strip_dir(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Base output directory cannot be empty")
        return cleaned


class ApiKeysPayload(BaseModel):
    spotify_client_id: str | None = Field(default=None, max_length=256)
    spotify_client_secret: str | None = Field(default=None, max_length=256)
    genius_access_token: str | None = Field(default=None, max_length=512)

    @field_validator("spotify_client_id", "spotify_client_secret", "genius_access_token", mode="before")
    @classmethod
    def _normalize(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else ""
        return str(value).strip()


class SettingsUpdatePayload(BaseModel):
    download: DownloadSettingsPayload
    api_keys: ApiKeysPayload | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_flat_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "download" in data:
            return data
        download_fields = {}
        for key in ("base_output_dir", "threads", "preload", "simple_tui"):
            if key in data:
                download_fields[key] = data[key]
        result: Dict[str, Any] = {"download": download_fields}
        if "api_keys" in data:
            result["api_keys"] = data["api_keys"]
        return result


def _format_validation_errors(error: ValidationError) -> Dict[str, str]:
    problems: Dict[str, str] = {}
    for err in error.errors():
        loc = err.get("loc") or ("settings",)
        if isinstance(loc, (list, tuple)):
            field = ".".join(str(part) for part in loc if str(part)) or "settings"
        else:
            field = str(loc) if loc else "settings"
        problems[field] = err.get("msg", "Invalid value")
    return problems


@settings_bp.route("/download", methods=["GET"])
@login_required
def read_download_settings():
    settings = get_download_settings(current_app)
    defaults = get_default_download_settings()
    api_keys_raw = get_api_keys(current_app)
    api_keys = describe_api_keys(api_keys_raw)
    spotdl_ready = bool(current_app.extensions.get("spotdl_ready", False))
    spotify_ready = bool(current_app.extensions.get("spotify_credentials_ready", False))
    genius_ready = bool(current_app.extensions.get("genius_credentials_ready", False))
    return (
        jsonify({
            "settings": settings,
            "defaults": defaults,
            "api_keys": api_keys,
            "spotdl_ready": spotdl_ready,
            "spotify_ready": spotify_ready,
            "genius_ready": genius_ready,
            "credentials_ready": spotify_ready,
        }),
        200,
    )


@settings_bp.route("/download", methods=["PUT"])
@login_required
def update_download_settings():
    payload = request.get_json(silent=True) or {}
    try:
        model = SettingsUpdatePayload.model_validate(payload)
    except ValidationError as exc:
        return jsonify({"errors": _format_validation_errors(exc)}), 400

    try:
        normalized_download = persist_download_settings(model.download.model_dump(), app=current_app)
        if model.api_keys is not None:
            api_key_updates = model.api_keys.model_dump(exclude_unset=True)
            stored_api_keys = persist_api_keys(api_key_updates, app=current_app)
        else:
            stored_api_keys = get_api_keys(current_app)
        apply_api_keys(current_app, stored_api_keys, refresh_client=model.api_keys is not None)
        spotify_ready = bool(current_app.extensions.get("spotify_credentials_ready", False))
        apply_download_settings(current_app, normalized_download, refresh_client=spotify_ready)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Failed to persist settings: %s", exc)
        return jsonify({"errors": {"settings": "Failed to update application settings."}}), 500

    defaults = get_default_download_settings()
    api_keys = describe_api_keys(stored_api_keys)
    spotdl_ready = bool(current_app.extensions.get("spotdl_ready", False))
    spotify_ready = bool(current_app.extensions.get("spotify_credentials_ready", False))
    genius_ready = bool(current_app.extensions.get("genius_credentials_ready", False))
    return (
        jsonify({
            "settings": normalized_download,
            "defaults": defaults,
            "api_keys": api_keys,
            "spotdl_ready": spotdl_ready,
            "spotify_ready": spotify_ready,
            "genius_ready": genius_ready,
            "credentials_ready": spotify_ready,
        }),
        200,
    )


__all__ = ["settings_bp"]
