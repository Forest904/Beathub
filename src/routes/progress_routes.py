import logging
from flask import Blueprint, Response

logger = logging.getLogger(__name__)

progress_bp = Blueprint('progress_bp', __name__, url_prefix='/api')


def _get_broker():
    from flask import current_app
    return current_app.extensions.get('progress_broker')


@progress_bp.route('/progress/stream')
def stream_progress():
    broker = _get_broker()
    if broker is None:
        return Response('progress unavailable', status=503)

    def _gen():
        try:
            for chunk in broker.subscribe():
                yield chunk
        except GeneratorExit:
            logger.info('SSE client disconnected')

    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
    }
    return Response(_gen(), headers=headers)

