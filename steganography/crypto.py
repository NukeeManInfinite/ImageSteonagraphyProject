"""Password-based message encryption using Fernet.

A thin, beginner-friendly wrapper that:

  - derives a key from the user's password via PBKDF2-HMAC-SHA256
    (200 000 iterations, 16-byte random salt),
  - encrypts/decrypts with Fernet (AES-128-CBC + HMAC-SHA256, authenticated),
  - returns a single urlsafe-base64 string that already contains the salt,
  - raises a clear `WrongPasswordError` when decryption fails.

The output format inside the base64 envelope is just:

    [16-byte salt][Fernet token bytes]

Embedding the salt with the ciphertext means the user only needs to remember
the password — no separate key file to keep alongside the stego image.
"""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# Tunables — kept as module constants so they're easy to find.
SALT_SIZE = 16          # bytes
KDF_ITERATIONS = 200_000
KEY_LENGTH = 32          # Fernet needs a 32-byte key (then base64-encoded)


class WrongPasswordError(ValueError):
    """Raised when decryption fails — wrong password or corrupted data."""


# ---------------------------------------------------------------------------
# internal helpers
# ---------------------------------------------------------------------------

def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a password and salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    raw_key = kdf.derive(password.encode("utf-8"))
    # Fernet expects a urlsafe-base64-encoded 32-byte key.
    return base64.urlsafe_b64encode(raw_key)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def encrypt(plaintext: str, password: str) -> str:
    """Encrypt `plaintext` with `password`. Returns a urlsafe-base64 string.

    The returned string carries the salt internally — pass it straight into
    `decrypt` along with the same password to recover the original text.
    """
    if not isinstance(plaintext, str):
        raise TypeError("plaintext must be a str")
    if not isinstance(password, str) or password == "":
        raise ValueError("password must be a non-empty string")

    salt = os.urandom(SALT_SIZE)
    key = _derive_key(password, salt)
    token = Fernet(key).encrypt(plaintext.encode("utf-8"))

    blob = salt + token
    return base64.urlsafe_b64encode(blob).decode("ascii")


def decrypt(token: str, password: str) -> str:
    """Decrypt a string previously produced by `encrypt`.

    Raises `WrongPasswordError` if the password is wrong, the token has
    been tampered with, or the input is otherwise unreadable.
    """
    if not isinstance(token, str):
        raise TypeError("token must be a str")
    if not isinstance(password, str) or password == "":
        raise ValueError("password must be a non-empty string")

    try:
        blob = base64.urlsafe_b64decode(token.encode("ascii"))
    except (ValueError, base64.binascii.Error) as e:
        raise WrongPasswordError("Token is not valid base64.") from e

    if len(blob) <= SALT_SIZE:
        raise WrongPasswordError("Token is too short to contain a salt.")

    salt, ciphertext = blob[:SALT_SIZE], blob[SALT_SIZE:]
    key = _derive_key(password, salt)

    try:
        plaintext_bytes = Fernet(key).decrypt(ciphertext)
    except InvalidToken as e:
        raise WrongPasswordError(
            "Decryption failed — wrong password or corrupted data."
        ) from e

    return plaintext_bytes.decode("utf-8")
