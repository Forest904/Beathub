"""Playlist CRUD routes with ownership enforcement."""

from __future__ import annotations

from typing import Iterable

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.database.db_manager import (
    db,
    DownloadedTrack,
    Playlist,
    PlaylistTrack,
)


playlist_bp = Blueprint('playlist_bp', __name__, url_prefix='/api/playlists')


def _serialize_playlist(playlist: Playlist, *, include_tracks: bool = True) -> dict:
    return playlist.to_dict(include_tracks=include_tracks)


def _owned_playlist(playlist_id: int) -> Playlist | None:
    if not getattr(current_user, 'is_authenticated', False):
        return None
    return (
        Playlist.query.options(
            selectinload(Playlist.entries).selectinload(PlaylistTrack.track)
        )
        .filter_by(id=playlist_id, user_id=current_user.id)
        .first()
    )


def _normalize_artists(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [piece.strip() for piece in str(value).split(',') if piece.strip()]


def _ensure_track(track_payload: dict, user_id: int) -> DownloadedTrack:
    spotify_id = (track_payload.get('spotify_id') or track_payload.get('id') or '').strip()
    if not spotify_id:
        raise ValueError('Track spotify_id is required')

    title = track_payload.get('title') or track_payload.get('name')
    if not title:
        raise ValueError('Track title is required')

    artists = _normalize_artists(
        track_payload.get('artists')
        or track_payload.get('artist_names')
        or track_payload.get('artist')
    )

    track = DownloadedTrack.query.filter_by(
        spotify_id=spotify_id,
        user_id=user_id,
    ).first()

    if track is None:
        track = DownloadedTrack(
            spotify_id=spotify_id,
            spotify_url=track_payload.get('spotify_url') or track_payload.get('url'),
            isrc=track_payload.get('isrc'),
            title=title,
            artists=artists,
            album_name=track_payload.get('album_name') or track_payload.get('album'),
            album_id=track_payload.get('album_id'),
            album_artist=track_payload.get('album_artist'),
            track_number=track_payload.get('track_number'),
            disc_number=track_payload.get('disc_number'),
            disc_count=track_payload.get('disc_count'),
            tracks_count=track_payload.get('tracks_count'),
            duration_ms=track_payload.get('duration_ms'),
            explicit=bool(track_payload.get('explicit', False)),
            popularity=track_payload.get('popularity'),
            publisher=track_payload.get('publisher'),
            year=track_payload.get('year'),
            date=track_payload.get('date'),
            genres=track_payload.get('genres'),
            cover_url=track_payload.get('cover_url'),
            local_path=track_payload.get('local_path'),
            local_lyrics_path=track_payload.get('local_lyrics_path'),
            user_id=user_id,
        )
        db.session.add(track)
    else:
        if artists and track.artists != artists:
            track.artists = artists
        if track.title != title:
            track.title = title
        if track.cover_url != track_payload.get('cover_url') and track_payload.get('cover_url'):
            track.cover_url = track_payload.get('cover_url')
        if track.spotify_url != track_payload.get('spotify_url') and track_payload.get('spotify_url'):
            track.spotify_url = track_payload.get('spotify_url')

    return track


def _apply_tracks(playlist: Playlist, tracks: Iterable[dict]) -> None:
    existing_spotify_ids = {
        (entry.track.spotify_id if entry.track else None)
        for entry in playlist.entries
    }
    next_position = max((entry.position for entry in playlist.entries), default=-1) + 1
    for offset, payload in enumerate(tracks):
        track = _ensure_track(payload, playlist.user_id)
        if track.spotify_id in existing_spotify_ids:
            continue
        snapshot = track.to_dict()
        snapshot['id'] = track.id
        entry = PlaylistTrack(
            playlist=playlist,
            track=track,
            position=next_position + offset,
            track_snapshot=snapshot,
        )
        db.session.add(entry)
        existing_spotify_ids.add(track.spotify_id)


@playlist_bp.route('', methods=['GET'])
@login_required
def list_playlists():
    page = max(1, request.args.get('page', type=int) or 1)
    per_page = request.args.get('per_page', type=int) or 10
    per_page = max(1, min(per_page, 50))

    query = Playlist.query.filter_by(user_id=current_user.id).order_by(Playlist.updated_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return (
        jsonify(
            {
                'items': [
                    _serialize_playlist(playlist, include_tracks=False)
                    for playlist in pagination.items
                ],
                'pagination': {
                    'page': pagination.page,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev,
                },
            }
        ),
        200,
    )


@playlist_bp.route('', methods=['POST'])
@login_required
def create_playlist():
    payload = request.get_json() or {}
    name = (payload.get('name') or '').strip()
    description = (payload.get('description') or '').strip() or None

    if not name:
        return jsonify({'error': 'name_required'}), 400

    playlist = Playlist(name=name, description=description, user_id=current_user.id)
    db.session.add(playlist)

    tracks_payload = payload.get('tracks') or []
    try:
        _apply_tracks(playlist, tracks_payload)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'error': 'invalid_track', 'message': str(exc)}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'duplicate_track'}), 409

    return jsonify({'playlist': _serialize_playlist(playlist)}), 201


@playlist_bp.route('/<int:playlist_id>', methods=['GET'])
@login_required
def get_playlist(playlist_id: int):
    playlist = _owned_playlist(playlist_id)
    if playlist is None:
        return jsonify({'error': 'not_found'}), 404
    return jsonify({'playlist': _serialize_playlist(playlist)}), 200


@playlist_bp.route('/<int:playlist_id>', methods=['PUT'])
@login_required
def update_playlist(playlist_id: int):
    playlist = _owned_playlist(playlist_id)
    if playlist is None:
        return jsonify({'error': 'not_found'}), 404

    payload = request.get_json() or {}
    if 'name' in payload:
        name = (payload.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name_required'}), 400
        playlist.name = name
    if 'description' in payload:
        playlist.description = (payload.get('description') or '').strip() or None

    if 'tracks' in payload:
        # Replace all tracks when explicit list provided
        playlist.entries.clear()
        db.session.flush()
        try:
            _apply_tracks(playlist, payload.get('tracks') or [])
        except ValueError as exc:
            db.session.rollback()
            return jsonify({'error': 'invalid_track', 'message': str(exc)}), 400
        except IntegrityError:
            db.session.rollback()
            return jsonify({'error': 'duplicate_track'}), 409

    db.session.commit()
    return jsonify({'playlist': _serialize_playlist(playlist)}), 200


@playlist_bp.route('/<int:playlist_id>', methods=['DELETE'])
@login_required
def delete_playlist(playlist_id: int):
    playlist = _owned_playlist(playlist_id)
    if playlist is None:
        return jsonify({'error': 'not_found'}), 404

    db.session.delete(playlist)
    db.session.commit()
    return jsonify({'status': 'deleted'}), 200


@playlist_bp.route('/<int:playlist_id>/tracks', methods=['POST'])
@login_required
def add_tracks(playlist_id: int):
    playlist = _owned_playlist(playlist_id)
    if playlist is None:
        return jsonify({'error': 'not_found'}), 404

    payload = request.get_json() or {}
    tracks_payload = payload.get('tracks')
    if isinstance(tracks_payload, dict):
        tracks_payload = [tracks_payload]
    if not isinstance(tracks_payload, list):
        return jsonify({'error': 'invalid_payload'}), 400

    try:
        _apply_tracks(playlist, tracks_payload)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'error': 'invalid_track', 'message': str(exc)}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'duplicate_track'}), 409

    return jsonify({'playlist': _serialize_playlist(playlist)}), 200


@playlist_bp.route('/<int:playlist_id>/tracks/<int:entry_id>', methods=['DELETE'])
@login_required
def remove_track(playlist_id: int, entry_id: int):
    playlist = _owned_playlist(playlist_id)
    if playlist is None:
        return jsonify({'error': 'not_found'}), 404

    entry = next((item for item in playlist.entries if item.id == entry_id), None)
    if entry is None:
        return jsonify({'error': 'track_not_found'}), 404

    db.session.delete(entry)
    remaining = [e for e in playlist.entries if e.id != entry_id]
    for index, item in enumerate(remaining):
        item.position = index
    db.session.commit()
    return jsonify({'playlist': _serialize_playlist(playlist)}), 200


@playlist_bp.route('/<int:playlist_id>/tracks/reorder', methods=['PUT'])
@login_required
def reorder_tracks(playlist_id: int):
    playlist = _owned_playlist(playlist_id)
    if playlist is None:
        return jsonify({'error': 'not_found'}), 404

    payload = request.get_json() or {}
    order = payload.get('order') or []
    if not isinstance(order, list) or not order:
        return jsonify({'error': 'invalid_payload'}), 400

    entry_map = {entry.id: entry for entry in playlist.entries}
    missing_ids = [entry_id for entry_id in order if entry_id not in entry_map]
    if missing_ids:
        return jsonify({'error': 'unknown_entries', 'entries': missing_ids}), 400

    for position, entry_id in enumerate(order):
        entry_map[entry_id].position = position

    # Keep unspecified entries at the end preserving order
    unspecified = [entry for entry in playlist.entries if entry.id not in order]
    base = len(order)
    for offset, entry in enumerate(sorted(unspecified, key=lambda e: e.position)):
        entry.position = base + offset

    db.session.commit()
    return jsonify({'playlist': _serialize_playlist(playlist)}), 200


__all__ = ['playlist_bp']
