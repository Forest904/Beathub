from __future__ import annotations

import logging
from typing import Optional, Union

from flask import has_app_context
from flask_login import current_user

from src.database.db_manager import get_system_user_id

logger = logging.getLogger(__name__)


def resolve_user_id(explicit: Optional[Union[int, str]] = None) -> int:
    """Resolve the acting user id for persistence and job ownership.

    Preference order:
    1. Explicit value when provided (coerced to int).
    2. Authenticated Flask-Login user in the current app context.
    3. System user id fallback (non-interactive tasks).
    """
    if explicit is not None:
        try:
            return int(explicit)
        except (TypeError, ValueError):
            logger.debug("Unable to coerce explicit user id %r to int; falling back", explicit)
    if has_app_context():
        try:
            if getattr(current_user, "is_authenticated", False):
                return int(current_user.get_id())
        except Exception:
            logger.debug("Failed to resolve current_user id; falling back", exc_info=True)
    return get_system_user_id()


__all__ = ["resolve_user_id"]
