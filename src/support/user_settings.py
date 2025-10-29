#!/usr/bin/env python
"""User-specific settings helpers for API credentials."""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import current_app
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from src.database.db_manager import User, db
from src.support.app_settings import API_KEY_NAMES, apply_api_keys, describe_api_keys


def _coerce_user(user: Optional[Any]) -> Optional[User]:
    """Return a concrete :class:`User` instance if the object represents an authenticated user."""
    candidate = user
    try:
        if hasattr(candidate, "_get_current_object"):
            candidate = candidate._get_current_object()
    except Exception:
        return None
    if not isinstance(candidate, User):
        return None
    if not getattr(candidate, "is_authenticated", False):
        return None
    return candidate


def _ensure_user(user: Optional[Any] = None) -> Optional[User]:
    resolved = _coerce_user(user)
    if resolved is not None:
        return resolved
    return _coerce_user(current_user)


def get_user_api_keys(user: Optional[Any] = None) -> Dict[str, str]:
    """Return stored API keys for the given user (or current user when omitted)."""
    resolved = _ensure_user(user)
    if resolved is None:
        return {}
    prefs: Dict[str, Any] = dict(resolved.preferences or {})
    raw_store = prefs.get("api_keys")
    if not isinstance(raw_store, dict):
        return {}
    sanitized: Dict[str, str] = {}
    for field in API_KEY_NAMES:
        value = raw_store.get(field)
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                sanitized[field] = trimmed
    return sanitized


def describe_user_api_keys(user: Optional[Any] = None) -> Dict[str, Dict[str, Any]]:
    """Return a redacted description of stored API keys suitable for API responses."""
    api_keys = get_user_api_keys(user)
    return describe_api_keys(api_keys)


def persist_user_api_keys(updates: Dict[str, Any], user: Optional[Any] = None) -> Dict[str, str]:
    """Persist API key updates for the given user and return the sanitized store."""
    resolved = _ensure_user(user)
    if resolved is None:
        raise ValueError("Cannot persist API keys without an authenticated user")

    prefs: Dict[str, Any] = dict(resolved.preferences or {})
    current_store = prefs.get("api_keys")
    if not isinstance(current_store, dict):
        current_store = {}
    else:
        current_store = dict(current_store)

    for field in API_KEY_NAMES:
        if field not in updates:
            continue
        raw_value = updates[field]
        if raw_value is None:
            current_store.pop(field, None)
            continue
        value = str(raw_value).strip()
        if value:
            current_store[field] = value
        else:
            current_store.pop(field, None)

    if current_store:
        prefs["api_keys"] = current_store
    else:
        prefs.pop("api_keys", None)

    resolved.preferences = prefs
    try:
        db.session.add(resolved)
        db.session.commit()
    except SQLAlchemyError as exc:  # pragma: no cover - defensive transaction handling
        db.session.rollback()
        raise exc

    return get_user_api_keys(resolved)


def user_has_spotify_credentials(source: Optional[Any] = None) -> bool:
    """Return True when both Spotify client ID and secret are present for the user."""
    if isinstance(source, dict):
        keys = source
    else:
        keys = get_user_api_keys(source)
    return bool(keys.get("spotify_client_id") and keys.get("spotify_client_secret"))


def user_has_genius_credentials(source: Optional[Any] = None) -> bool:
    if isinstance(source, dict):
        keys = source
    else:
        keys = get_user_api_keys(source)
    return bool(keys.get("genius_access_token"))


def ensure_user_api_keys_applied(user: Optional[Any] = None, *, refresh_client: bool = False) -> Dict[str, str]:
    """Apply a user's API keys to the runtime configuration when necessary."""
    resolved = _ensure_user(user)
    app = current_app._get_current_object()
    keys = get_user_api_keys(resolved)
    state = app.extensions.setdefault("user_credentials_state", {})
    last_user_id = state.get("user_id")
    last_keys: Dict[str, str] = state.get("keys", {})

    if resolved is None:
        if last_user_id is not None or last_keys:
            apply_api_keys(app, {}, refresh_client=refresh_client)
            app.extensions["user_credentials_state"] = {"user_id": None, "keys": {}}
        return {}

    needs_refresh = refresh_client or last_user_id != resolved.id or last_keys != keys
    if needs_refresh:
        apply_api_keys(app, keys, refresh_client=refresh_client)
        app.extensions["user_credentials_state"] = {"user_id": resolved.id, "keys": dict(keys)}
    return keys


def ensure_user_api_keys_applied_for_user_id(user_id: Optional[int], *, refresh_client: bool = False) -> Dict[str, str]:
    """Load a user by id, apply their credentials, and return the sanitized key store."""
    if user_id is None:
        app = current_app._get_current_object()
        apply_api_keys(app, {}, refresh_client=refresh_client)
        app.extensions["user_credentials_state"] = {"user_id": None, "keys": {}}
        return {}

    user = db.session.get(User, user_id)
    if user is None:
        app = current_app._get_current_object()
        apply_api_keys(app, {}, refresh_client=refresh_client)
        app.extensions["user_credentials_state"] = {"user_id": None, "keys": {}}
        return {}

    return ensure_user_api_keys_applied(user=user, refresh_client=refresh_client)


__all__ = [
    "describe_user_api_keys",
    "ensure_user_api_keys_applied",
    "ensure_user_api_keys_applied_for_user_id",
    "get_user_api_keys",
    "persist_user_api_keys",
    "user_has_genius_credentials",
    "user_has_spotify_credentials",
]
