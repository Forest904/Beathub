#!/usr/bin/env python
"""Authentication utilities and Flask-Login integration."""

from __future__ import annotations

from flask import jsonify
from flask_login import LoginManager

login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_message = None


def init_auth(app):
    """Attach Flask-Login to the Flask app and register auth blueprints."""
    from src.database.db_manager import User, db, ensure_system_user
    from src.routes.auth_routes import auth_bp

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    @login_manager.unauthorized_handler
    def _unauthorized():
        return jsonify({"error": "authentication_required"}), 401

    # Ensure system user exists prior to serving requests
    with app.app_context():
        ensure_system_user()

    app.register_blueprint(auth_bp)

    return login_manager


__all__ = ["login_manager", "init_auth"]
