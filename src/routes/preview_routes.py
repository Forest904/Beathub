import logging
import math
import time
from threading import Lock
from typing import Dict, Optional

import requests
from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from config import Config
from src.utils.cache import MISSING, TTLCache

logger = logging.getLogger(__name__)

preview_bp = Blueprint('preview_bp', __name__, url_prefix='/api')

_PREVIEW_CACHE = TTLCache(
    maxsize=Config.METADATA_CACHE_MAXSIZE,
    ttl=Config.METADATA_CACHE_TTL_SECONDS,
)
_PREVIEW_BYTE_LIMIT = 320_000  # ~10 seconds at 256 kbps
_STREAM_CHUNK_SIZE = 16 * 1024


class FixedWindowRateLimiter:
    """Simple fixed-window rate limiter keyed by client identifier."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        if max_requests <= 0:
            raise ValueError('max_requests must be positive')
        if window_seconds <= 0:
            raise ValueError('window_seconds must be positive')
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._entries: Dict[str, tuple[int, float]] = {}
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, float]:
        now = time.time()
        with self._lock:
            count, window_end = self._entries.get(key, (0, now + self._window_seconds))
            if now >= window_end:
                count = 0
                window_end = now + self._window_seconds
            count += 1
            self._entries[key] = (count, window_end)
            allowed = count <= self._max_requests
            retry_after = max(0.0, window_end - now)
        return allowed, retry_after

    def reset(self) -> None:
        with self._lock:
            self._entries.clear()


_RATE_LIMITER = FixedWindowRateLimiter(max_requests=30, window_seconds=60.0)


def _rate_limit_response(retry_after: float) -> Response:
    retry_header = str(int(math.ceil(retry_after)))
    if request.method == 'HEAD':
        resp = Response(status=429)
    else:
        resp = jsonify({'error': 'Too many preview requests'})
        resp.status_code = 429
    resp.headers['Retry-After'] = retry_header
    return resp


def _check_rate_limit() -> Optional[Response]:
    remote_addr = request.remote_addr or 'unknown'
    allowed, retry_after = _RATE_LIMITER.allow(remote_addr)
    if allowed:
        return None
    return _rate_limit_response(retry_after)


def _get_spotify_client():
    downloader = current_app.extensions.get('spotify_downloader')
    if not downloader:
        return None
    return downloader.get_spotipy_instance()


def _fetch_preview_url(track_id: str) -> Optional[str]:
    cache_key = ('preview_url', track_id)
    cached = _PREVIEW_CACHE.get(cache_key, MISSING)
    if cached is not MISSING:
        return cached

    sp = _get_spotify_client()
    if not sp:
        logger.error('Spotipy client not initialized; cannot retrieve preview for %s', track_id)
        _PREVIEW_CACHE.set(cache_key, None)
        return None
    try:
        track_info = sp.track(track_id)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception('Failed to fetch track metadata for %s: %s', track_id, exc)
        _PREVIEW_CACHE.set(cache_key, None)
        return None

    preview_url = track_info.get('preview_url') if isinstance(track_info, dict) else None
    if preview_url:
        _PREVIEW_CACHE.set(cache_key, preview_url)
        return preview_url

    logger.info('No preview available for track %s', track_id)
    _PREVIEW_CACHE.set(cache_key, None)
    return None


def _head_remote(url: str) -> Optional[requests.Response]:
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        if response.status_code >= 400:
            logger.warning('Preview HEAD request returned %s for %s', response.status_code, url)
            return None
        return response
    except requests.RequestException as exc:
        logger.exception('Failed HEAD request for preview %s: %s', url, exc)
        return None


@preview_bp.route('/preview/<string:track_id>', methods=['HEAD'])
def preview_head(track_id: str):
    rate_error = _check_rate_limit()
    if rate_error:
        return rate_error

    if not track_id:
        return Response(status=400)

    preview_url = _fetch_preview_url(track_id)
    if not preview_url:
        return Response(status=404)

    head_response = _head_remote(preview_url)
    if head_response is None:
        return Response(status=502)

    headers = {
        'Content-Type': head_response.headers.get('Content-Type', 'audio/mpeg'),
    }
    total_length = head_response.headers.get('Content-Length')
    if total_length:
        try:
            total = int(total_length)
        except ValueError:
            total = None
        if total is not None:
            headers['Content-Length'] = str(min(total, _PREVIEW_BYTE_LIMIT))
    headers['Accept-Ranges'] = 'bytes'
    return Response(status=200, headers=headers)


def _proxy_stream(preview_url: str):
    range_header = request.headers.get('Range')
    req_headers = {}
    if range_header:
        req_headers['Range'] = range_header

    try:
        remote = requests.get(preview_url, headers=req_headers, stream=True, timeout=(3.05, 10))
    except requests.RequestException as exc:
        logger.exception('Failed to stream preview from %s: %s', preview_url, exc)
        return None

    if remote.status_code >= 400:
        logger.warning('Preview stream returned %s for %s', remote.status_code, preview_url)
        remote.close()
        return None

    bytes_sent = 0
    truncated = False

    def generate():
        nonlocal bytes_sent, truncated
        try:
            for chunk in remote.iter_content(chunk_size=_STREAM_CHUNK_SIZE):
                if not chunk:
                    continue
                remaining = _PREVIEW_BYTE_LIMIT - bytes_sent
                if remaining <= 0:
                    truncated = True
                    break
                if len(chunk) > remaining:
                    yield chunk[:remaining]
                    bytes_sent += remaining
                    truncated = True
                    break
                bytes_sent += len(chunk)
                yield chunk
        finally:
            remote.close()

    headers = {
        'Content-Type': remote.headers.get('Content-Type', 'audio/mpeg'),
    }
    total_length = remote.headers.get('Content-Length')
    total = None
    if total_length:
        try:
            total = int(total_length)
        except ValueError:
            total = None
    if total is not None:
        headers['Content-Length'] = str(min(total, _PREVIEW_BYTE_LIMIT))
    headers['Accept-Ranges'] = 'bytes'

    status_code = remote.status_code
    if status_code == 200 and total is not None and total > _PREVIEW_BYTE_LIMIT and not range_header:
        status_code = 206
        headers['Content-Range'] = f'bytes 0-{_PREVIEW_BYTE_LIMIT - 1}/{total}'

    return Response(stream_with_context(generate()), status=status_code, headers=headers)


@preview_bp.route('/preview/<string:track_id>', methods=['GET'])
def preview_stream(track_id: str):
    rate_error = _check_rate_limit()
    if rate_error:
        return rate_error

    if not track_id:
        return jsonify({'error': 'Missing track identifier'}), 400

    preview_url = _fetch_preview_url(track_id)
    if not preview_url:
        return jsonify({'error': 'Preview unavailable'}), 404

    response = _proxy_stream(preview_url)
    if response is None:
        return jsonify({'error': 'Failed to proxy preview'}), 502
    return response


__all__ = ['preview_bp', '_PREVIEW_BYTE_LIMIT', 'FixedWindowRateLimiter']
