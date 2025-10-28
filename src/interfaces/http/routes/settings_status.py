#!/usr/bin/env python
"""Settings status endpoint returning SpotDL runtime readiness."""

from __future__ import annotations

from flask import Blueprint, jsonify, current_app
from flask_login import login_required

status_bp = Blueprint("settings_status_bp", __name__, url_prefix="/api/settings")


@status_bp.route("/status", methods=["GET"])
@login_required
def get_settings_status():
    spotdl_ready = bool(current_app.extensions.get("spotdl_ready", False))
    return jsonify({"spotdl_ready": spotdl_ready}), 200


__all__ = ["status_bp"]
