import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from src.database.db_manager import db, DownloadedItem

logger = logging.getLogger(__name__)

compilation_bp = Blueprint('compilation_bp', __name__, url_prefix='/api')


def _get_downloader():
    from flask import current_app
    return current_app.extensions.get('spotify_downloader')


@compilation_bp.route('/compilations/download', methods=['POST'])
def download_compilation_api():
    downloader = _get_downloader()
    if downloader is None:
        return jsonify({'status': 'error', 'message': 'Downloader unavailable'}), 503

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    tracks = data.get('tracks') or []
    async_mode = bool(data.get('async', True))

    if not name:
        return jsonify({'status': 'error', 'message': 'Missing compilation name'}), 400
    if not isinstance(tracks, list) or len(tracks) == 0:
        return jsonify({'status': 'error', 'message': 'Provide a non-empty list of tracks'}), 400
    if len(tracks) > 200:
        return jsonify({'status': 'error', 'message': 'Too many tracks (max 200)'}), 400

    # Pre-create output dir and DB record so the item shows up in history immediately
    safe_name = downloader.file_manager.sanitize_filename(name)
    ts = datetime.now().strftime('%Y%m%d-%H%M')
    comp_dir = os.path.join(downloader.base_output_dir, 'Compilations', f"{safe_name}-{ts}")
    os.makedirs(comp_dir, exist_ok=True)
    synthetic_spotify_id = f'comp-{ts}-{safe_name}'

    try:
        existing = DownloadedItem.query.filter_by(spotify_id=synthetic_spotify_id).first()
        if not existing:
            item = DownloadedItem(
                spotify_id=synthetic_spotify_id,
                title=name,
                artist='Various Artists',
                image_url=None,
                spotify_url=None,
                local_path=comp_dir,
                item_type='compilation',
            )
            db.session.add(item)
            db.session.commit()
        else:
            if existing.local_path != comp_dir:
                existing.local_path = comp_dir
                db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning('Failed to persist compilation item in DB early: %s', e, exc_info=True)

    def _run_job():
        try:
            downloader.download_compilation(tracks, name)
        except Exception as e:
            logger.error('Compilation download failed: %s', e, exc_info=True)

    if async_mode:
        t = threading.Thread(target=_run_job, name=f'compilation-{ts}', daemon=True)
        t.start()
        return jsonify({'status': 'accepted', 'compilation_spotify_id': synthetic_spotify_id, 'output_directory': comp_dir}), 202

    result = downloader.download_compilation(tracks, name)
    http_status = 200 if isinstance(result, dict) and result.get('status') == 'success' else 500
    return jsonify(result), http_status

