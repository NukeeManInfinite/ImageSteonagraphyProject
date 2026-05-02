"""Service layer: bridge between the web layer and the steganography library.

Pure functions only — no Flask, no HTTP, no globals. The web layer hands
us raw bytes and gets raw bytes (or text) back.

Pipeline:

  encode:  image_bytes  ->  cv2.imdecode
                        ->  crypto.encrypt(message, password)
                        ->  lsb.embed(image, encrypted_token)
                        ->  cv2.imencode('.png', stego)
                        ->  return PNG bytes

  decode:  image_bytes  ->  cv2.imdecode
                        ->  lsb.extract(image)              -> token (str)
                        ->  crypto.decrypt(token, password) -> plaintext
                        ->  return plaintext
"""

from __future__ import annotations

import cv2
import numpy as np

from steganography import crypto, lsb
from steganography.crypto import WrongPasswordError  # re-export for callers


class ServiceError(Exception):
    """Base class for service-layer errors meant for the user."""


class InvalidImageError(ServiceError):
    """Uploaded bytes could not be decoded as a color image."""


class CapacityError(ServiceError):
    """The encrypted message does not fit in the cover image."""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _decode_image(image_bytes: bytes) -> np.ndarray:
    """Turn raw upload bytes into a uint8 BGR ndarray, or raise."""
    if not image_bytes:
        raise InvalidImageError("No image data was provided.")

    buf = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        raise InvalidImageError(
            "Could not decode the uploaded file as an image."
        )
    if img.ndim != 3 or img.shape[2] != 3:
        raise InvalidImageError(
            "Image must be a 3-channel color image (RGB)."
        )
    return img


def _encode_png(image: np.ndarray) -> bytes:
    """Encode a uint8 BGR image as PNG bytes (lossless — required for LSB)."""
    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise ServiceError("Failed to encode stego image as PNG.")
    return buf.tobytes()


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def encode_message(image_bytes: bytes, message: str, password: str) -> bytes:
    """Encrypt `message` with `password` and embed it into the image.

    Returns the resulting stego image as PNG bytes. Raises:
      - InvalidImageError  : input is not a valid color image
      - CapacityError      : encrypted payload doesn't fit in the cover
      - ValueError         : empty message / empty password
    """
    if not isinstance(message, str) or message == "":
        raise ValueError("Message must be a non-empty string.")
    if not isinstance(password, str) or password == "":
        raise ValueError("Password must be a non-empty string.")

    cover = _decode_image(image_bytes)

    token = crypto.encrypt(message, password)

    try:
        stego = lsb.embed(cover, token)
    except ValueError as e:
        # lsb.embed raises ValueError for capacity overflow.
        raise CapacityError(str(e)) from e

    return _encode_png(stego)


def decode_message(image_bytes: bytes, password: str) -> str:
    """Extract and decrypt a message from the given stego image bytes.

    Returns the recovered plaintext. Raises:
      - InvalidImageError   : input is not a valid color image
      - WrongPasswordError  : wrong password or tampered/no payload
      - ValueError          : empty password
    """
    if not isinstance(password, str) or password == "":
        raise ValueError("Password must be a non-empty string.")

    stego = _decode_image(image_bytes)

    try:
        token = lsb.extract(stego)
    except ValueError as e:
        # lsb.extract raises ValueError when there is no valid payload.
        # From the user's perspective this is the same failure mode as a
        # wrong password: "we couldn't recover anything readable".
        raise WrongPasswordError(
            "No readable message found — wrong password or this image "
            "doesn't contain a hidden payload."
        ) from e

    return crypto.decrypt(token, password)
