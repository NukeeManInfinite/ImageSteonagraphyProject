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

# Baked-in fallback list. Used when ALLOWED_ORIGINS is unset OR appended to
# whatever ALLOWED_ORIGINS provides. The deployed Vercel URL is included
# here so the API keeps working even if the Render env var is misconfigured.
BUILT_IN_ALLOWED_ORIGINS = [
    "https://image-steonagraphy-project.vercel.app",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def _parse_origins(raw: str) -> list[str]:
    """Split a comma-separated origins string. Strips whitespace and any
    trailing slash (a common copy-paste mistake that makes CORS silently
    fail because origins must match exactly).
    """
    out: list[str] = []
    for o in raw.split(","):
        o = o.strip().rstrip("/")
        if o:
            out.append(o)
    return out


def _resolve_allowed_origins() -> list[str]:
    """Combine env-var origins with the built-in fallback list, de-duped."""
    env_origins = _parse_origins(os.environ.get("ALLOWED_ORIGINS", ""))
    # Built-ins are always allowed too, so a missing or wrong env var can't
    # break a known-good frontend deploy.
    merged: list[str] = []
    for o in env_origins + BUILT_IN_ALLOWED_ORIGINS:
        if o not in merged:
            merged.append(o)
    return merged


def create_app() -> Flask:
    """Application factory."""
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

    origins = _resolve_allowed_origins()
    # Log on startup so the Render dashboard logs show exactly which origins
    # this server will accept. Easy to verify after each deploy.
    app.logger.info("CORS allowed origins: %s", origins)

    CORS(
        app,
        resources={
            r"/encode": {"origins": origins},
            r"/decode": {"origins": origins},
        },
        supports_credentials=False,
        methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

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
