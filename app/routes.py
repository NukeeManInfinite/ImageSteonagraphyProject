"""HTTP routes.

Routes stay deliberately thin: parse the request, hand bytes/strings to the
service layer, shape the result into an HTTP response. Anything that can
fail with a user-meaningful error raises one of the typed exceptions in
`app.service`, which the error handlers in `app/__init__.py` turn into
JSON 400 responses.
"""

from __future__ import annotations

from io import BytesIO

from flask import Blueprint, abort, jsonify, make_response, render_template, request, send_file

from app.service import decode_message, encode_message


bp = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# /
# ---------------------------------------------------------------------------

@bp.get("/")
def index():
    """Serve the single-page UI. The template itself ships in Step 4."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# /encode
# ---------------------------------------------------------------------------

@bp.post("/encode")
def encode():
    """Embed an encrypted message into an uploaded image.

    Form fields:
      image    -- file (PNG/BMP/etc.; will be re-encoded as PNG)
      message  -- secret text
      password -- password used to derive the encryption key

    Returns:
      200 image/png  -- stego image as a download
      400 json       -- validation / capacity / image errors
    """
    image_bytes, message, password = _parse_encode_form()

    stego_png = encode_message(image_bytes, message, password)

    return send_file(
        BytesIO(stego_png),
        mimetype="image/png",
        as_attachment=True,
        download_name="stego.png",
    )


# ---------------------------------------------------------------------------
# /decode
# ---------------------------------------------------------------------------

@bp.post("/decode")
def decode():
    """Extract and decrypt a message from an uploaded stego image.

    Form fields:
      image    -- the stego image
      password -- password used at encode time

    Returns:
      200 json {"message": "..."}  -- recovered plaintext
      400 json {"error":  "..."}   -- wrong password / no payload / bad image
    """
    image_bytes, password = _parse_decode_form()

    plaintext = decode_message(image_bytes, password)

    return jsonify(message=plaintext)


# ---------------------------------------------------------------------------
# request parsing helpers (kept here so the routes themselves stay tiny)
# ---------------------------------------------------------------------------

def _parse_encode_form() -> tuple[bytes, str, str]:
    image_bytes = _read_image_field()
    message = (request.form.get("message") or "").strip()
    password = request.form.get("password") or ""

    if not message:
        _bad_request("Field 'message' is required.")
    if not password:
        _bad_request("Field 'password' is required.")
    return image_bytes, message, password


def _parse_decode_form() -> tuple[bytes, str]:
    image_bytes = _read_image_field()
    password = request.form.get("password") or ""
    if not password:
        _bad_request("Field 'password' is required.")
    return image_bytes, password


def _read_image_field() -> bytes:
    """Read the 'image' file upload into memory, or 400 if missing."""
    file = request.files.get("image")
    if file is None or file.filename == "":
        _bad_request("Field 'image' (file upload) is required.")
    return file.read()


def _bad_request(msg: str):
    """Abort the current request with a JSON 400 — same shape as other errors."""
    abort(make_response(jsonify(error=msg), 400))
