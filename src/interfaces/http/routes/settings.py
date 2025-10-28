#!/usr/bin/env python
"""Settings API endpoints."""

from __future__ import annotations

import logging
from typing import Dict

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from pydantic import BaseModel, Field, ValidationError, field_validator

from src.support.app_settings import (
    apply_download_settings,
    get_default_download_settings,
    get_download_settings,
    persist_download_settings,
)

logger = logging.getLogger(__name__)

settings_bp = Blueprint("settings_bp", __name__, url_prefix="/api/settings")


class DownloadSettingsPayload(BaseModel):
    base_output_dir: str = Field(min_length=1, max_length=512)
    threads: int = Field(ge=1, le=32)
    preload: bool

    @field_validator("base_output_dir")
    @classmethod
    def _strip_dir(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Base output directory cannot be empty")
        return cleaned


def _format_validation_errors(error: ValidationError) -> Dict[str, str]:
    problems: Dict[str, str] = {}
    for err in error.errors():
        loc = err.get("loc") or ("settings",)
        field = str(loc[0]) if isinstance(loc, (list, tuple)) and loc else "settings"
        problems[field] = err.get("msg", "Invalid value")
    return problems


@settings_bp.route("/download", methods=["GET"])
@login_required
def read_download_settings():
    settings = get_download_settings()
    defaults = get_default_download_settings()
    return jsonify({"settings": settings, "defaults": defaults}), 200


@settings_bp.route("/download", methods=["PUT"])
@login_required
def update_download_settings():
    payload = request.get_json(silent=True) or {}
    try:
        model = DownloadSettingsPayload.model_validate(payload)
    except ValidationError as exc:
        return jsonify({"errors": _format_validation_errors(exc)}), 400

    try:
        normalized = persist_download_settings(model.model_dump(), app=current_app)
        apply_download_settings(current_app, normalized, refresh_client=True)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Failed to persist download settings: %s", exc)
        return jsonify({"errors": {"settings": "Failed to update download settings."}}), 500

    defaults = get_default_download_settings()
    return jsonify({"settings": normalized, "defaults": defaults}), 200


__all__ = ["settings_bp"]
