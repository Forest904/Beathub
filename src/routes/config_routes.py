import logging
from flask import Blueprint, jsonify
from config import Config

logger = logging.getLogger(__name__)

config_bp = Blueprint('config_bp', __name__, url_prefix='/api')


@config_bp.route('/config/frontend', methods=['GET'])
def get_frontend_config():
    """Expose a minimal set of configuration values to the frontend."""
    try:
        payload = {
            'cd_capacity_minutes': int(Config.CD_CAPACITY_MINUTES or 80),
        }
        return jsonify(payload), 200
    except Exception as e:
        logger.warning('Failed to load frontend config: %s', e, exc_info=True)
        return jsonify({'cd_capacity_minutes': 80}), 200

