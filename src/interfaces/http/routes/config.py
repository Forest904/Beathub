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


@config_bp.route('/config/public-config', methods=['GET'])
def get_public_config():
    """Expose deployment feature flags for frontend gating."""
    try:
        rate_limiting_enabled = bool(
            Config.ENABLE_RATE_LIMITING
            and Config.RATE_LIMIT_REQUESTS > 0
            and Config.RATE_LIMIT_WINDOW_SECONDS > 0
        )
        payload = {
            'publicMode': bool(Config.PUBLIC_MODE),
            'allowStreamingExport': bool(Config.ALLOW_STREAMING_EXPORT),
            'enableCDBurner': bool(Config.ENABLE_CD_BURNER),
            'features': {
                'rateLimiting': {
                    'enabled': rate_limiting_enabled,
                    'requests': Config.RATE_LIMIT_REQUESTS,
                    'windowSeconds': Config.RATE_LIMIT_WINDOW_SECONDS,
                },
            },
        }
        return jsonify(payload), 200
    except Exception as exc:
        logger.warning('Failed to load public config: %s', exc, exc_info=True)
        return jsonify(
            {
                'publicMode': False,
                'allowStreamingExport': True,
                'enableCDBurner': True,
                'features': {
                    'rateLimiting': {
                        'enabled': False,
                        'requests': 0,
                        'windowSeconds': 0,
                    },
                },
            }
        ), 200

