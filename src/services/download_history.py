from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union

from flask import has_app_context
from flask_login import current_user

from src.database.db_manager import db, DownloadedItem, get_system_user_id


logger = logging.getLogger(__name__)

_VALID_ITEM_TYPES = {"album", "track", "playlist", "compilation"}


def _resolve_user_id(explicit: Optional[Union[int, str]]) -> int:
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


def persist_download_item(result: Dict[str, Any], *, explicit_user_id: Optional[Union[int, str]] = None) -> None:
    """Persist DownloadedItem metadata for a completed download result."""
    if not isinstance(result, dict):
        return
    if result.get("status") != "success":
        return

    item_type = result.get("item_type")
    if item_type not in _VALID_ITEM_TYPES:
        return

    spotify_id = result.get("spotify_id")
    title = result.get("item_name")
    if not spotify_id or not title:
        return

    artist = result.get("artist")
    image_url = result.get("cover_art_url")
    spotify_url = result.get("spotify_url")
    local_path = result.get("output_directory")
    local_cover_path = result.get("local_cover_image_path")

    resolved_user_id = _resolve_user_id(
        explicit_user_id if explicit_user_id is not None else result.get("user_id")
    )

    try:
        existing_item = DownloadedItem.query.filter_by(
            spotify_id=spotify_id, user_id=resolved_user_id
        ).first()
        ownership_changed = False

        if not existing_item:
            orphan = DownloadedItem.query.filter_by(spotify_id=spotify_id).first()
            if orphan:
                ownership_changed = orphan.user_id != resolved_user_id
                if ownership_changed:
                    orphan.user_id = resolved_user_id
                existing_item = orphan

        if not existing_item:
            computed_image_url = (
                f"/api/items/by-spotify/{spotify_id}/cover"
                if local_cover_path
                else image_url
            )
            new_item = DownloadedItem(
                user_id=resolved_user_id,
                spotify_id=spotify_id,
                title=title,
                artist=artist,
                image_url=computed_image_url,
                spotify_url=spotify_url,
                local_path=local_path,
                item_type=item_type,
            )
            db.session.add(new_item)
            db.session.commit()
            logger.info(
                "Added %s to DB: %s (spotify_id=%s, user_id=%s)",
                item_type,
                title,
                spotify_id,
                resolved_user_id,
            )
        else:
            updated = ownership_changed
            if existing_item.user_id != resolved_user_id:
                existing_item.user_id = resolved_user_id
                updated = True
            if local_path and existing_item.local_path != local_path:
                existing_item.local_path = local_path
                updated = True
            if local_cover_path:
                computed_url = f"/api/items/by-spotify/{spotify_id}/cover"
                if existing_item.image_url != computed_url:
                    existing_item.image_url = computed_url
                    updated = True
            elif image_url and existing_item.image_url != image_url:
                existing_item.image_url = image_url
                updated = True
            if updated:
                db.session.commit()
                logger.info(
                    "Updated DownloadedItem '%s' metadata (spotify_id=%s, user_id=%s)",
                    existing_item.title,
                    spotify_id,
                    resolved_user_id,
                )
    except Exception as exc:
        db.session.rollback()
        logger.error(
            "Failed to persist %s '%s' (spotify_id=%s): %s",
            item_type,
            title,
            spotify_id,
            exc,
            exc_info=True,
        )


__all__ = ["persist_download_item"]
