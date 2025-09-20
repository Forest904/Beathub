import os
import shutil
import logging
from flask import Blueprint, request, jsonify, send_file
import json
from src.database.db_manager import db, DownloadedItem
from src.lyrics_service import LyricsService
import re

logger = logging.getLogger(__name__)

download_bp = Blueprint('download_bp', __name__, url_prefix='/api')

# Helper function to get the SpotifyContentDownloader instance
def get_spotify_downloader():
    from flask import current_app
    return current_app.extensions['spotify_downloader']

@download_bp.route('/download', methods=['POST'])
def download_spotify_item_api():
    from flask import current_app
    spotify_downloader = get_spotify_downloader()
    jobs = current_app.extensions.get('download_jobs')

    data = request.get_json() or {}
    spotify_link = data.get('spotify_link')
    async_mode = bool(data.get('async', False))

    if not spotify_link:
        return jsonify({"status": "error", "message": "Spotify link is required."}), 400

    logger.info(f"Received download request for: {spotify_link} (async={async_mode})")

    # If job queue is available, use it for idempotent handling and parallelism
    if jobs is not None:
        job = jobs.submit(spotify_link)
        if async_mode:
            return jsonify({"status": "accepted", "job_id": job.id, "link": spotify_link}), 202
        # Synchronous path: wait for completion
        result = jobs.wait(job.id)
    else:
        # Direct call when no job queue is configured
        result = spotify_downloader.download_spotify_content(spotify_link)

    if not isinstance(result, dict):
        return jsonify({"status": "error", "message": "Unexpected orchestrator response."}), 500

    if result.get("status") == "success":
        # Extract relevant metadata from the result for DB storage
        item_type = result.get('item_type')
        spotify_id = result.get('spotify_id')
        title = result.get('item_name')
        artist = result.get('artist')
        image_url = result.get('cover_art_url')
        spotify_url = result.get('spotify_url')
        local_path = result.get('output_directory')

        logger.info(f"Attempting to save to DB: Type='{item_type}', ID='{spotify_id}', Title='{title}', Artist='{artist}'")

        # Validate essential fields before attempting DB save
        if not spotify_id or not title:
            logger.warning(f"Missing crucial data for DB save (Spotify ID or Title). Skipping DB storage for {spotify_link}.")
            return jsonify(result), 200

        # Determine if this item type should be stored in the DownloadedItem model
        if item_type in ["album", "track", "playlist"]:
            try:
                existing_item = DownloadedItem.query.filter_by(spotify_id=spotify_id).first()
                if not existing_item:
                    new_item = DownloadedItem(
                        spotify_id=spotify_id,
                        title=title,
                        artist=artist,
                        image_url=image_url,
                        spotify_url=spotify_url,
                        local_path=local_path,
                        item_type=item_type
                    )
                    db.session.add(new_item)
                    db.session.commit()
                    logger.info(f"Added {item_type} to DB: {new_item.title} (ID: {new_item.id})")
                else:
                    if existing_item.local_path != local_path:
                        existing_item.local_path = local_path
                        db.session.commit()
                        logger.info(f"Updated local_path for '{existing_item.title}' to '{local_path}'")
            except Exception as e:
                db.session.rollback()
                logger.error(f"DATABASE ERROR: Failed to save/update {item_type} '{title}' (ID: {spotify_id}) to DB: {e}", exc_info=True)
        else:
            logger.warning(f"Unhandled item_type '{item_type}' encountered. Skipping DB storage for this item.")

        return jsonify(result), 200

    # Error mapping to HTTP status
    message = result.get("message", "")
    error_code = result.get("error_code")
    status_code = 500 if error_code in ("provider_error", "internal_error") else 400
    return jsonify(result), status_code

@download_bp.route('/albums', methods=['GET'])
def get_downloaded_items():
    items = DownloadedItem.query.order_by(DownloadedItem.title).all()
    return jsonify([item.to_dict() for item in items]), 200

@download_bp.route('/albums/<int:item_id>', methods=['DELETE'])
def delete_downloaded_item(item_id):
    item = DownloadedItem.query.get(item_id)
    if not item:
        return jsonify({'success': False, 'message': 'Item not found'}), 404

    if item.local_path and os.path.exists(item.local_path):
        try:
            shutil.rmtree(item.local_path)
            logger.info(f"Successfully deleted local directory for {item.item_type}: {item.title} at {item.local_path}")
        except Exception as e:
            logger.error(f"Failed to delete local directory {item.local_path} for {item.title}: {e}", exc_info=True)
            return jsonify({'success': False, 'message': f'Failed to delete local files: {str(e)}'}), 500

    db.session.delete(item)
    db.session.commit()
    logger.info(f"Successfully deleted {item.item_type} '{item.title}' from DB.")
    return jsonify({'success': True, 'message': 'Item deleted successfully.'}), 200


@download_bp.route('/items/<int:item_id>/metadata', methods=['GET'])
def get_item_metadata_by_id(item_id: int):
    """Return the saved spotify_metadata.json for a downloaded item by DB id."""
    item = DownloadedItem.query.get(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    if not item.local_path:
        return jsonify({'error': 'Local path not available for this item'}), 404

    metadata_path = os.path.join(item.local_path, 'spotify_metadata.json')
    if not os.path.exists(metadata_path):
        return jsonify({'error': 'Metadata not found'}), 404
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data), 200
    except Exception as e:
        logger.error("Failed to read metadata for item %s: %s", item_id, e, exc_info=True)
        return jsonify({'error': 'Failed to read metadata'}), 500


@download_bp.route('/items/by-spotify/<string:spotify_id>/metadata', methods=['GET'])
def get_item_metadata_by_spotify(spotify_id: str):
    """Return the saved spotify_metadata.json for a downloaded item by Spotify id."""
    item = DownloadedItem.query.filter_by(spotify_id=spotify_id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    if not item.local_path:
        return jsonify({'error': 'Local path not available for this item'}), 404

    metadata_path = os.path.join(item.local_path, 'spotify_metadata.json')
    if not os.path.exists(metadata_path):
        return jsonify({'error': 'Metadata not found'}), 404
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data), 200
    except Exception as e:
        logger.error("Failed to read metadata for spotify %s: %s", spotify_id, e, exc_info=True)
        return jsonify({'error': 'Failed to read metadata'}), 500


@download_bp.route('/items/<int:item_id>/lyrics', methods=['GET'])
def get_item_lyrics(item_id: int):
    """Retrieve lyrics for a given downloaded item (album/playlist/track) using fuzzy file matching.

    Query params:
      - title: track title (required)
      - artist: primary artist name (optional but recommended)

    Strategy:
      1) Find the matching audio file in the item's folder using the same fuzzy rules used for burn preview.
      2) Prefer a .txt lyrics file with the same basename as the audio file (exported by SpotDL pipeline).
      3) If no .txt found, read embedded lyrics from the audio file via LyricsService.
      4) If still not found, attempt fuzzy match among .txt basenames.
    """
    title = (request.args.get('title') or '').strip()
    artist = (request.args.get('artist') or '').strip()
    if not title:
        return jsonify({'error': 'Missing title parameter'}), 400

    item = DownloadedItem.query.get(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    base_dir = item.local_path
    if not base_dir or not os.path.isdir(base_dir):
        return jsonify({'error': 'Associated content directory not found or is invalid.'}), 404

    # Gather candidate files
    audio_exts = ('.mp3', '.flac', '.m4a', '.ogg', '.wav')
    text_exts = ('.txt',)
    all_files = []
    for root, _, files in os.walk(base_dir):
        for fn in files:
            low = fn.lower()
            if low.endswith(audio_exts) or low.endswith(text_exts):
                all_files.append(os.path.join(root, fn))

    # Normalization helper (mirrors cd_burning_service)
    def _norm(s: str) -> str:
        s = (s or '').lower()
        s = s.replace('\ufffdT', "'")  # best-effort for odd apostrophes
        s = re.sub(r"[\\/:*?\"<>|.,!()\[\]{}]", '', s)
        s = s.replace('_', '')
        s = re.sub(r"\s+", '', s)
        return s

    # Build expectations
    sanitized_title = re.sub(r'[\\/:*?"<>|]', '_', title).strip()
    sanitized_title = re.sub(r'_{2,}', '_', sanitized_title)

    # 1) Try exact filename match for audio
    found_audio = None
    mp3_name = f"{sanitized_title}.mp3"
    fallback_name = f"{artist} - {sanitized_title}.mp3" if artist else None
    for path in all_files:
        base = os.path.basename(path)
        if base.lower() == mp3_name.lower():
            found_audio = path
            break
    if not found_audio and artist:
        for path in all_files:
            base = os.path.basename(path)
            if base.lower() == (fallback_name or '').lower():
                found_audio = path
                break

    # 2) Fuzzy-normalized across all audio files
    if not found_audio:
        exp1 = _norm(sanitized_title)
        exp2 = _norm(f"{artist} - {sanitized_title}") if artist else None
        exp3 = _norm(title)
        exp4 = _norm(f"{artist} - {title}") if artist else None
        artist_norm = _norm(artist) if artist else ''
        for path in all_files:
            if not path.lower().endswith(audio_exts):
                continue
            base_no_ext = os.path.splitext(os.path.basename(path))[0]
            nb = _norm(base_no_ext)
            if nb in filter(None, (exp1, exp2, exp3, exp4)):
                found_audio = path
                break
            # Handle trailing feat*
            if exp1 and nb.startswith(exp1) and nb[len(exp1):].startswith(('feat', 'featuring', 'ft', 'with')):
                found_audio = path
                break
            if exp2 and nb.startswith(exp2) and nb[len(exp2):].startswith(('feat', 'featuring', 'ft', 'with')):
                found_audio = path
                break
            # Accept extra artists before the hyphen
            tail1 = '-' + exp1 if exp1 else None
            tail3 = '-' + exp3 if exp3 else None
            if tail1 and nb.endswith(tail1):
                left = nb[: -len(tail1)]
                if not artist_norm or left.startswith(artist_norm):
                    found_audio = path
                    break
            if tail3 and nb.endswith(tail3):
                left = nb[: -len(tail3)]
                if not artist_norm or left.startswith(artist_norm):
                    found_audio = path
                    break

    # Try matching a .txt with same base as the audio
    matched_txt = None
    if found_audio:
        base_no_ext = os.path.splitext(found_audio)[0]
        candidate = base_no_ext + '.txt'
        if os.path.exists(candidate):
            matched_txt = candidate

    # If no audio match, try fuzzy matching among .txt files directly
    if not matched_txt and not found_audio:
        exp1 = _norm(sanitized_title)
        exp2 = _norm(f"{artist} - {sanitized_title}") if artist else None
        exp3 = _norm(title)
        exp4 = _norm(f"{artist} - {title}") if artist else None
        artist_norm = _norm(artist) if artist else ''
        for path in all_files:
            if not path.lower().endswith('.txt'):
                continue
            base_no_ext = os.path.splitext(os.path.basename(path))[0]
            nb = _norm(base_no_ext)
            if nb in filter(None, (exp1, exp2, exp3, exp4)):
                matched_txt = path
                break
            if exp1 and nb.startswith(exp1) and nb[len(exp1):].startswith(('feat', 'featuring', 'ft', 'with')):
                matched_txt = path
                break
            if exp2 and nb.startswith(exp2) and nb[len(exp2):].startswith(('feat', 'featuring', 'ft', 'with')):
                matched_txt = path
                break
            tail1 = '-' + exp1 if exp1 else None
            tail3 = '-' + exp3 if exp3 else None
            if tail1 and nb.endswith(tail1):
                left = nb[: -len(tail1)]
                if not artist_norm or left.startswith(artist_norm):
                    matched_txt = path
                    break
            if tail3 and nb.endswith(tail3):
                left = nb[: -len(tail3)]
                if not artist_norm or left.startswith(artist_norm):
                    matched_txt = path
                    break

    # Read lyrics from .txt or extract from audio
    lyrics_text = None
    source = None
    if matched_txt and os.path.exists(matched_txt):
        try:
            with open(matched_txt, 'r', encoding='utf-8', errors='replace') as f:
                lyrics_text = f.read()
            source = 'text'
        except Exception:
            lyrics_text = None
            source = None
    if lyrics_text is None and found_audio and os.path.exists(found_audio):
        try:
            svc = LyricsService()
            lyrics_text = svc.extract_lyrics_from_audio(found_audio)
            if lyrics_text:
                source = 'embedded'
        except Exception:
            lyrics_text = None
            source = None

    if not lyrics_text:
        return jsonify({
            'success': False,
            'message': 'Lyrics not found for this track.',
            'matched_audio_path': found_audio,
            'matched_lyrics_path': matched_txt,
        }), 404

    return jsonify({
        'success': True,
        'lyrics': lyrics_text,
        'source': source,
        'matched_audio_path': found_audio,
        'matched_lyrics_path': matched_txt,
        'title': title,
        'artist': artist,
    }), 200


@download_bp.route('/items/<int:item_id>/audio', methods=['GET'])
def stream_item_audio(item_id: int):
    """Stream a matched audio file for a downloaded item using fuzzy matching.

    Query params:
      - title: track title (required)
      - artist: primary artist name (optional)
    """
    title = (request.args.get('title') or '').strip()
    artist = (request.args.get('artist') or '').strip()
    if not title:
        return jsonify({'error': 'Missing title parameter'}), 400

    item = DownloadedItem.query.get(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    base_dir = item.local_path
    if not base_dir or not os.path.isdir(base_dir):
        return jsonify({'error': 'Associated content directory not found or is invalid.'}), 404

    # Gather candidate audio files only
    audio_exts = ('.mp3', '.flac', '.m4a', '.ogg', '.wav')
    all_audio_files = []
    for root, _, files in os.walk(base_dir):
        for fn in files:
            low = fn.lower()
            if low.endswith(audio_exts):
                all_audio_files.append(os.path.join(root, fn))

    # Normalization helper (mirrors cd_burning_service)
    def _norm(s: str) -> str:
        s = (s or '').lower()
        s = s.replace('\ufffdT', "'")  # best-effort for odd apostrophes
        s = re.sub(r"[\\/:*?\"<>|.,!()\[\]{}]", '', s)
        s = s.replace('_', '')
        s = re.sub(r"\s+", '', s)
        return s

    # Build expectations
    sanitized_title = re.sub(r'[\\/:*?"<>|]', '_', title).strip()
    sanitized_title = re.sub(r'_{2,}', '_', sanitized_title)

    found_audio = None
    mp3_name = f"{sanitized_title}.mp3"
    fallback_name = f"{artist} - {sanitized_title}.mp3" if artist else None
    for path in all_audio_files:
        base = os.path.basename(path)
        if base.lower() == mp3_name.lower():
            found_audio = path
            break
    if not found_audio and artist:
        for path in all_audio_files:
            base = os.path.basename(path)
            if base.lower() == (fallback_name or '').lower():
                found_audio = path
                break

    # Fuzzy-normalized across all audio files
    if not found_audio:
        exp1 = _norm(sanitized_title)
        exp2 = _norm(f"{artist} - {sanitized_title}") if artist else None
        exp3 = _norm(title)
        exp4 = _norm(f"{artist} - {title}") if artist else None
        artist_norm = _norm(artist) if artist else ''
        for path in all_audio_files:
            base_no_ext = os.path.splitext(os.path.basename(path))[0]
            nb = _norm(base_no_ext)
            if nb in filter(None, (exp1, exp2, exp3, exp4)):
                found_audio = path
                break
            # Handle trailing feat*
            if exp1 and nb.startswith(exp1) and nb[len(exp1):].startswith(('feat', 'featuring', 'ft', 'with')):
                found_audio = path
                break
            if exp2 and nb.startswith(exp2) and nb[len(exp2):].startswith(('feat', 'featuring', 'ft', 'with')):
                found_audio = path
                break
            # Accept extra artists before the hyphen
            tail1 = '-' + exp1 if exp1 else None
            tail3 = '-' + exp3 if exp3 else None
            if tail1 and nb.endswith(tail1):
                left = nb[: -len(tail1)]
                if not artist_norm or left.startswith(artist_norm):
                    found_audio = path
                    break
            if tail3 and nb.endswith(tail3):
                left = nb[: -len(tail3)]
                if not artist_norm or left.startswith(artist_norm):
                    found_audio = path
                    break

    if not found_audio or not os.path.exists(found_audio):
        return jsonify({'error': 'Audio file not found for this track.'}), 404

    # Infer MIME type from extension
    ext = os.path.splitext(found_audio)[1].lower()
    mimetype = {
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
        '.flac': 'audio/flac',
        '.ogg': 'audio/ogg',
        '.wav': 'audio/wav',
    }.get(ext, 'application/octet-stream')

    try:
        return send_file(found_audio, mimetype=mimetype, as_attachment=False, conditional=True)
    except Exception:
        logger.exception("Failed to stream audio file: %s", found_audio)
        return jsonify({'error': 'Failed to stream audio file.'}), 500
