"""Flask app factory.

Builds and configures the application. All HTTP-level concerns live in this
package; the actual steganography + crypto work is delegated to
`app.service`, which in turn uses the existing `steganography` library.

Local dev:
    flask --app app run

Production (e.g. Render):
    gunicorn --bind 0.0.0.0:$PORT "app:create_app()"
"""

from __future__ import annotations

import os

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

from app.service import (
    CapacityError,
    InvalidImageError,
    WrongPasswordError,
)

# 8 MB upload cap — enough for typical PNG covers, small enough to keep
# memory use bounded for an MVP.
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

# Default origins cover local dev. In production, set ALLOWED_ORIGINS to a
# comma-separated list that includes your Vercel URL, e.g.
#   ALLOWED_ORIGINS="https://my-stego.vercel.app,http://localhost:5000"
DEFAULT_ALLOWED_ORIGINS = "http://localhost:5000,http://127.0.0.1:5000"


def create_app() -> Flask:
    """Application factory."""
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

    # CORS: only enable on the API endpoints that the Vercel frontend calls.
    # The home page (`/`) is same-origin during local dev and unused in prod.
    origins = [
        o.strip()
        for o in os.environ.get("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS).split(",")
        if o.strip()
    ]
    CORS(app, resources={r"/encode": {"origins": origins},
                         r"/decode": {"origins": origins}})

    # Routes live in their own module to keep this file focused on wiring.
    from app.routes import bp
    app.register_blueprint(bp)

    _register_error_handlers(app)
    return app


def _register_error_handlers(app: Flask) -> None:
    """Map service-layer exceptions to JSON HTTP 400 responses."""

    @app.errorhandler(InvalidImageError)
    def _invalid_image(e: InvalidImageError):
        return jsonify(error=str(e)), 400

    @app.errorhandler(CapacityError)
    def _capacity(e: CapacityError):
        return jsonify(error=str(e)), 400

    @app.errorhandler(WrongPasswordError)
    def _wrong_password(e: WrongPasswordError):
        return jsonify(error=str(e)), 400

    @app.errorhandler(RequestEntityTooLarge)
    def _too_large(_e: RequestEntityTooLarge):
        return (
            jsonify(error=f"Upload exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."),
            413,
        )
