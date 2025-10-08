"""Favorite toggling and listings."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from src.database.db_manager import Favorite, db


favorite_bp = Blueprint('favorite_bp', __name__, url_prefix='/api/favorites')

VALID_FAVORITE_TYPES = {'artist', 'album', 'track'}


def _serialize(favorite: Favorite) -> dict:
    return favorite.to_dict()


def _require_type_and_id(payload: dict) -> tuple[str, str] | tuple[None, None]:
    item_type = (payload.get('item_type') or '').strip().lower()
    item_id = (payload.get('item_id') or '').strip()
    if item_type not in VALID_FAVORITE_TYPES or not item_id:
        return None, None
    return item_type, item_id


@favorite_bp.route('', methods=['GET'])
@login_required
def list_favorites():
    page = max(1, request.args.get('page', type=int) or 1)
    per_page = request.args.get('per_page', type=int) or 20
    per_page = max(1, min(100, per_page))
    item_type = (request.args.get('type') or '').strip().lower()

    query = Favorite.query.filter_by(user_id=current_user.id)
    if item_type in VALID_FAVORITE_TYPES:
        query = query.filter(Favorite.item_type == item_type)

    pagination = query.order_by(Favorite.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    return (
        jsonify(
            {
                'items': [_serialize(fav) for fav in pagination.items],
                'pagination': {
                    'page': pagination.page,
                    'per_page': pagination.per_page,
                    'pages': pagination.pages,
                    'total': pagination.total,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev,
                },
            }
        ),
        200,
    )


@favorite_bp.route('/summary', methods=['GET'])
@login_required
def favorites_summary():
    summary = Favorite.summary_for_user(current_user.id)
    for favorite_type in VALID_FAVORITE_TYPES:
        summary.setdefault(favorite_type, 0)
    return jsonify({'summary': summary}), 200


@favorite_bp.route('/status', methods=['GET'])
@login_required
def favorite_status():
    item_type = (request.args.get('item_type') or '').strip().lower()
    item_id = (request.args.get('item_id') or '').strip()
    if item_type not in VALID_FAVORITE_TYPES or not item_id:
        return jsonify({'error': 'invalid_parameters'}), 400

    favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        item_type=item_type,
        item_id=item_id,
    ).first()

    return (
        jsonify(
            {
                'favorited': favorite is not None,
                'favorite': _serialize(favorite) if favorite else None,
            }
        ),
        200,
    )


@favorite_bp.route('/toggle', methods=['POST'])
@login_required
def toggle_favorite():
    payload = request.get_json() or {}
    item_type, item_id = _require_type_and_id(payload)
    if not item_type:
        return jsonify({'error': 'invalid_parameters'}), 400

    metadata = payload.get('metadata') or {}
    favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        item_type=item_type,
        item_id=item_id,
    ).first()

    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        summary = Favorite.summary_for_user(current_user.id)
        for favorite_type in VALID_FAVORITE_TYPES:
            summary.setdefault(favorite_type, 0)
        return (
            jsonify(
                {
                    'favorited': False,
                    'favorite': None,
                    'summary': summary,
                }
            ),
            200,
        )

    favorite = Favorite(
        user_id=current_user.id,
        item_type=item_type,
        item_id=item_id,
        item_name=(metadata.get('name') or metadata.get('title') or item_id)[:255],
        item_subtitle=(metadata.get('subtitle') or metadata.get('artist')),
        item_image_url=metadata.get('image_url') or metadata.get('cover_url'),
        item_url=metadata.get('url') or metadata.get('spotify_url'),
    )
    db.session.add(favorite)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        favorite = Favorite.query.filter_by(
            user_id=current_user.id,
            item_type=item_type,
            item_id=item_id,
        ).first()
        if favorite is None:
            return jsonify({'error': 'unable_to_toggle'}), 409

    summary = Favorite.summary_for_user(current_user.id)
    for favorite_type in VALID_FAVORITE_TYPES:
        summary.setdefault(favorite_type, 0)

    return (
        jsonify(
            {
                'favorited': True,
                'favorite': _serialize(favorite),
                'summary': summary,
            }
        ),
        200,
    )


@favorite_bp.route('/<int:favorite_id>', methods=['DELETE'])
@login_required
def remove_favorite(favorite_id: int):
    favorite = Favorite.query.filter_by(
        id=favorite_id,
        user_id=current_user.id,
    ).first()
    if favorite is None:
        return jsonify({'error': 'not_found'}), 404

    db.session.delete(favorite)
    db.session.commit()
    summary = Favorite.summary_for_user(current_user.id)
    for favorite_type in VALID_FAVORITE_TYPES:
        summary.setdefault(favorite_type, 0)

    return (
        jsonify(
            {
                'favorited': False,
                'favorite': None,
                'summary': summary,
            }
        ),
        200,
    )


__all__ = ['favorite_bp']
