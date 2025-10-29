#!/usr/bin/env python
"""Settings status endpoint returning SpotDL runtime readiness."""

from __future__ import annotations

from flask import Blueprint, jsonify, current_app
from flask_login import current_user, login_required

from src.support.user_settings import (
    describe_user_api_keys,
    ensure_user_api_keys_applied,
    user_has_genius_credentials,
    user_has_spotify_credentials,
)

status_bp = Blueprint("settings_status_bp", __name__, url_prefix="/api/settings")


@status_bp.route("/status", methods=["GET"])
@login_required
def get_settings_status():
    keys = ensure_user_api_keys_applied(current_user)
    spotify_ready = user_has_spotify_credentials(keys)
    genius_ready = user_has_genius_credentials(keys)
    spotdl_ready = bool(current_app.extensions.get("spotdl_ready", False) and spotify_ready)
    return jsonify({
        "spotdl_ready": spotdl_ready,
        "spotify_ready": spotify_ready,
        "genius_ready": genius_ready,
        "credentials_ready": spotify_ready,
        "api_keys": describe_user_api_keys(current_user),
    }), 200


__all__ = ["status_bp"]
