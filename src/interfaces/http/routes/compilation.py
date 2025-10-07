import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request
from flask_login import login_required

from src.database.db_manager import db, DownloadedItem
from src.support.identity import resolve_user_id

logger = logging.getLogger(__name__)

compilation_bp = Blueprint('compilation_bp', __name__, url_prefix='/api')


def _get_downloader():
    from flask import current_app
    return current_app.extensions.get('download_orchestrator')


def _resolve_user_id() -> int:
    return resolve_user_id()


@compilation_bp.route('/compilations/download', methods=['POST'])
@login_required
def download_compilation_api():
    downloader = _get_downloader()
    if downloader is None:
        return jsonify({'status': 'error', 'message': 'Downloader unavailable'}), 503

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    tracks = data.get('tracks') or []
    cover_data_url = data.get('cover_data_url')  # optional base64 data URL from UI
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

    # Try to save cover image immediately so the history grid can show it
    def _save_data_url_image(data_url: str, out_dir: str) -> str | None:
        try:
            if not isinstance(data_url, str) or not data_url.startswith('data:image/') or ';base64,' not in data_url:
                return None
            head, b64 = data_url.split(',', 1)
            ext = 'jpg'
            if 'image/png' in head:
                ext = 'png'
            elif 'image/jpeg' in head or 'image/jpg' in head:
                ext = 'jpg'
            fname = f'cover.{ext}'
            target = os.path.join(out_dir, fname)
            import base64
            raw = base64.b64decode(b64)
            with open(target, 'wb') as f:
                f.write(raw)
            return target
        except Exception:
            logger.exception('Failed to save data URL cover image')
            return None

    def _write_default_svg(title_text: str, out_dir: str) -> str | None:
        try:
            svg_path = os.path.join(out_dir, 'cover.svg')
            # Simple centered SVG with wrapped text
            safe_title = (title_text or 'Compilation').strip()
            # naive wrap at ~24 chars
            lines = []
            line = ''
            for word in safe_title.split():
                if len(line) + len(word) + 1 <= 24:
                    line = (line + ' ' + word).strip()
                else:
                    if line:
                        lines.append(line)
                    line = word
            if line:
                lines.append(line)
            if len(lines) > 5:
                lines = lines[:5]
                lines[-1] += '…'
            dy = 0
            if lines:
                # vertical offset so group is centered
                total = (len(lines) - 1) * 1.3
                dy = -total / 2.0
            text_elems = '\n'.join([
                f"<text x='50%' y='50%' dy='{(i*1.3)+dy}em' text-anchor='middle' dominant-baseline='middle' font-family='Segoe UI, Arial, sans-serif' font-size='36' fill='#0b1727'>{line}</text>"
                for i, line in enumerate(lines)
            ])
            svg = f"""
<svg xmlns='http://www.w3.org/2000/svg' width='640' height='640' viewBox='0 0 640 640'>
  <defs>
    <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
      <stop offset='0%' stop-color='#a7c5eb'/>
      <stop offset='100%' stop-color='#74b9ff'/>
    </linearGradient>
  </defs>
  <rect width='100%' height='100%' fill='url(#bg)'/>
  {text_elems}
</svg>
""".strip()
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg)
            return svg_path
        except Exception:
            logger.exception('Failed to write default SVG cover')
            return None

    cover_path = None
    if isinstance(cover_data_url, str) and cover_data_url:
        cover_path = _save_data_url_image(cover_data_url, comp_dir)
    if not cover_path:
        cover_path = _write_default_svg(name, comp_dir)

    user_id = _resolve_user_id()

    # Persist or update DB record
    try:
        existing = DownloadedItem.query.filter_by(spotify_id=synthetic_spotify_id, user_id=user_id).first()
        ownership_changed = False
        if not existing:
            existing = DownloadedItem.query.filter_by(spotify_id=synthetic_spotify_id).first()
            if existing:
                ownership_changed = existing.user_id != user_id
                if ownership_changed:
                    existing.user_id = user_id
            else:
                item = DownloadedItem(
                    user_id=user_id,
                    spotify_id=synthetic_spotify_id,
                    title=name,
                    artist='Various Artists',
                    image_url=f"/api/items/by-spotify/{synthetic_spotify_id}/cover",
                    spotify_url=None,
                    local_path=comp_dir,
                    item_type='compilation',
                )
                db.session.add(item)
                db.session.commit()
                existing = item
        if existing:
            # Ensure path + cover URL are up to date
            new_url = f"/api/items/by-spotify/{synthetic_spotify_id}/cover"
            changed = ownership_changed
            if existing.user_id != user_id:
                existing.user_id = user_id
                changed = True
            if existing.local_path != comp_dir:
                existing.local_path = comp_dir
                changed = True
            if existing.image_url != new_url:
                existing.image_url = new_url
                changed = True
            if changed:
                db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning('Failed to persist compilation item in DB early: %s', e, exc_info=True)

    def _run_job():
        try:
            downloader.download_compilation(tracks, name, cover_data_url=cover_data_url, user_id=user_id)
        except Exception as e:
            logger.error('Compilation download failed: %s', e, exc_info=True)

    if async_mode:
        t = threading.Thread(target=_run_job, name=f'compilation-{ts}', daemon=True)
        t.start()
        return jsonify({'status': 'accepted', 'compilation_spotify_id': synthetic_spotify_id, 'output_directory': comp_dir}), 202

    result = downloader.download_compilation(tracks, name, cover_data_url=cover_data_url, user_id=user_id)
    http_status = 200 if isinstance(result, dict) and result.get('status') == 'success' else 500
    return jsonify(result), http_status


