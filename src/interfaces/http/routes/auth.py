#!/usr/bin/env python
"""Authentication API endpoints for registration and login."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, Tuple

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

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



def _validate_profile_payload(payload: Dict[str, object]) -> Tuple[Dict[str, object], Dict[str, str]]:
    updated_fields: Dict[str, object] = {}
    errors: Dict[str, str] = {}

    username = payload.get("username")
    if username is not None:
        if not isinstance(username, str):
            errors["username"] = "Username must be a string."
        else:
            username = username.strip()
            if len(username) > 120:
                errors["username"] = "Username must be 120 characters or fewer."
            else:
                updated_fields["username"] = username or None

    display_name = payload.get("display_name")
    if display_name is not None:
        if not isinstance(display_name, str):
            errors["display_name"] = "Display name must be a string."
        else:
            display_name = display_name.strip()
            if len(display_name) > 120:
                errors["display_name"] = "Display name must be 120 characters or fewer."
            else:
                updated_fields["display_name"] = display_name or None

    avatar_url = payload.get("avatar_url")
    if avatar_url is not None:
        if not isinstance(avatar_url, str):
            errors["avatar_url"] = "Avatar URL must be a string."
        else:
            avatar_url = avatar_url.strip()
            if avatar_url and len(avatar_url) > 512:
                errors["avatar_url"] = "Avatar URL must be 512 characters or fewer."
            else:
                updated_fields["avatar_url"] = avatar_url or None

    preferences = payload.get("preferences")
    if preferences is not None:
        if not isinstance(preferences, dict):
            errors["preferences"] = "Preferences must be an object."
        else:
            updated_fields["preferences"] = preferences

    return updated_fields, errors


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
    username = email.split("@")[0]
    user.username = username or None
    user.display_name = username or None
    user.preferences = user.preferences or {}
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

    user.last_login_at = datetime.utcnow()
    login_user(user)
    db.session.commit()
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


@auth_bp.route("/profile", methods=["PATCH"])
@login_required
def update_profile():
    data = request.get_json() or {}
    updates, errors = _validate_profile_payload(data)

    if errors:
        return jsonify({"errors": errors}), 400

    for key, value in updates.items():
        setattr(current_user, key, value)

    db.session.commit()
    return jsonify({"user": current_user.to_dict()}), 200


@auth_bp.route("/change-email", methods=["POST"])
@login_required
def change_email():
    data = request.get_json() or {}
    new_email = (data.get("new_email") or "").strip().lower()
    current_password = (data.get("current_password") or "").strip()

    errors: Dict[str, str] = {}
    if not new_email or not _EMAIL_RE.match(new_email):
        errors["new_email"] = "Please provide a valid email address."
    if not current_password:
        errors["current_password"] = "Your current password is required to change email."

    if errors:
        return jsonify({"errors": errors}), 400

    if not current_user.check_password(current_password):
        return jsonify({"errors": {"current_password": "Current password is incorrect."}}), 403

    if new_email == current_user.email:
        return jsonify({"errors": {"new_email": "This email is already associated with your account."}}), 400

    existing = User.query.filter(User.email == new_email).first()
    if existing:
        return jsonify({"errors": {"new_email": "Another account is already using this email."}}), 409

    current_user.email = new_email
    if not current_user.username:
        current_user.username = new_email.split("@")[0] or new_email

    db.session.commit()
    return jsonify({"user": current_user.to_dict()}), 200


@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json() or {}
    current_password = (data.get("current_password") or "").strip()
    new_password = (data.get("new_password") or "").strip()
    confirm_password = (data.get("confirm_password") or "").strip()

    errors: Dict[str, str] = {}
    if not current_password:
        errors["current_password"] = "Current password is required."
    if len(new_password) < 8:
        errors["new_password"] = "New password must be at least 8 characters long."
    if new_password and new_password != confirm_password:
        errors["confirm_password"] = "Passwords do not match."

    if errors:
        return jsonify({"errors": errors}), 400

    if not current_user.check_password(current_password):
        return jsonify({"errors": {"current_password": "Current password is incorrect."}}), 403

    if current_user.check_password(new_password):
        return jsonify({"errors": {"new_password": "New password must be different from the current password."}}), 400

    current_user.set_password(new_password)
    db.session.commit()
    return jsonify({"success": True}), 200


__all__ = ["auth_bp"]
