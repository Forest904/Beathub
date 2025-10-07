#!/usr/bin/env python
"""Authentication API endpoints for registration and login."""

from __future__ import annotations

import re
from typing import Dict, Tuple

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_user, logout_user

from src.database.db_manager import User, db


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_credentials(payload: Dict[str, str]) -> Tuple[str, str, Dict[str, str]]:
    email = (payload.get("email") or "").strip().lower()
    password = (payload.get("password") or "").strip()
    errors: Dict[str, str] = {}
    if not email or not _EMAIL_RE.match(email):
        errors["email"] = "Please provide a valid email address."
    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters long."
    return email, password, errors


@auth_bp.route("/register", methods=["POST"])
def register_user():
    data = request.get_json() or {}
    email, password, errors = _validate_credentials(data)
    if errors:
        return jsonify({"errors": errors}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"errors": {"email": "An account with this email already exists."}}), 409

    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify({"user": user.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"errors": {"form": "Email and password are required."}}), 400

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({"errors": {"form": "Invalid email or password."}}), 401

    if not user.is_active:
        return jsonify({"errors": {"form": "Account is disabled."}}), 403

    login_user(user)
    return jsonify({"user": user.to_dict()}), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    if current_user.is_authenticated:
        logout_user()
    return jsonify({"success": True}), 200


@auth_bp.route("/session", methods=["GET"])
def session_info():
    if current_user.is_authenticated:
        return jsonify({"user": current_user.to_dict()}), 200
    return jsonify({"user": None}), 200


__all__ = ["auth_bp"]
