#!/usr/bin/env python
"""Settings status endpoint returning SpotDL runtime readiness."""

from __future__ import annotations

from flask import Blueprint, jsonify, current_app
from flask_login import login_required

from src.support.app_settings import describe_api_keys, get_api_keys

status_bp = Blueprint("settings_status_bp", __name__, url_prefix="/api/settings")


@status_bp.route("/status", methods=["GET"])
@login_required
def get_settings_status():
    spotdl_ready = bool(current_app.extensions.get("spotdl_ready", False))
    spotify_ready = bool(current_app.extensions.get("spotify_credentials_ready", False))
    genius_ready = bool(current_app.extensions.get("genius_credentials_ready", False))
    api_keys = describe_api_keys(get_api_keys(current_app))
    return jsonify({
        "spotdl_ready": spotdl_ready,
        "spotify_ready": spotify_ready,
        "genius_ready": genius_ready,
        "credentials_ready": spotify_ready,
        "api_keys": api_keys,
    }), 200


__all__ = ["status_bp"]
