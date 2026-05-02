"""LSB steganography: embedding and extraction.

Format written into the image:
    [32-bit big-endian payload length in bits] [payload bits]

The length prefix lets extraction recover the exact message without
relying on sentinel strings (which can appear inside the payload).

Bits are written into the least significant bit of each channel value,
in row-major order across the flattened image (H x W x C).
"""

from __future__ import annotations

import numpy as np


LENGTH_HEADER_BITS = 32


# ---------------------------------------------------------------------------
# text <-> bits
# ---------------------------------------------------------------------------

def _text_to_bits(text: str) -> np.ndarray:
    """Encode text as UTF-8, then to a flat uint8 array of 0/1 bits (MSB first)."""
    data = text.encode("utf-8")
    if not data:
        return np.zeros(0, dtype=np.uint8)
    arr = np.frombuffer(data, dtype=np.uint8)
    # unpackbits is MSB-first, which matches our extraction order
    return np.unpackbits(arr)


def _int_to_bits(value: int, width: int) -> np.ndarray:
    """Encode a non-negative integer as a big-endian bit array of given width."""
    if value < 0 or value >= (1 << width):
        raise ValueError(f"Value {value} does not fit in {width} bits")
    # format into a binary string then to an array — simple and correct
    bits = np.array([(value >> (width - 1 - i)) & 1 for i in range(width)],
                    dtype=np.uint8)
    return bits


# ---------------------------------------------------------------------------
# capacity
# ---------------------------------------------------------------------------

def capacity_bits(image: np.ndarray) -> int:
    """Total number of LSB bits available in an image (H*W*C)."""
    if image.ndim != 3:
        raise ValueError("Expected a 3-channel image (H, W, C)")
    return int(image.size)


def max_message_bytes(image: np.ndarray) -> int:
    """How many UTF-8 bytes can fit, accounting for the 32-bit header."""
    return max(0, (capacity_bits(image) - LENGTH_HEADER_BITS) // 8)


# ---------------------------------------------------------------------------
# embed
# ---------------------------------------------------------------------------

def embed(image: np.ndarray, message: str) -> np.ndarray:
    """Return a new image with `message` embedded in the LSBs.

    The cover image is not modified in place.
    """
    if image.dtype != np.uint8:
        raise ValueError(f"Cover image must be uint8, got {image.dtype}")
    if image.ndim != 3:
        raise ValueError("Cover image must have shape (H, W, C)")

    payload_bits = _text_to_bits(message)
    payload_len = int(payload_bits.size)

    total_bits_needed = LENGTH_HEADER_BITS + payload_len
    if total_bits_needed > capacity_bits(image):
        raise ValueError(
            f"Message too large: needs {total_bits_needed} bits, "
            f"image holds {capacity_bits(image)}. "
            f"Max message size for this image: {max_message_bytes(image)} bytes."
        )

    header_bits = _int_to_bits(payload_len, LENGTH_HEADER_BITS)
    all_bits = np.concatenate([header_bits, payload_bits]).astype(np.uint8)

    stego = image.copy()
    flat = stego.reshape(-1)

    # Clear the LSB of the pixels we will touch, then OR in the bits.
    # Using bitwise ops keeps this branch-free and vectorized.
    n = all_bits.size
    flat[:n] = (flat[:n] & np.uint8(0xFE)) | all_bits

    return stego


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------

def _bits_to_int(bits: np.ndarray) -> int:
    """Decode a big-endian bit array to an int."""
    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    return value


def _bits_to_text(bits: np.ndarray) -> str:
    """Decode a flat bit array (MSB-first, multiple of 8) to a UTF-8 string."""
    if bits.size == 0:
        return ""
    if bits.size % 8 != 0:
        raise ValueError(
            f"Bit stream length {bits.size} is not a multiple of 8 — "
            "image may not contain LSB-embedded data or is corrupted."
        )
    byte_arr = np.packbits(bits.astype(np.uint8))
    try:
        return byte_arr.tobytes().decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(
            "Extracted bytes are not valid UTF-8 — the image probably "
            "does not contain a message embedded by this tool."
        ) from e


def extract(image: np.ndarray) -> str:
    """Recover the message previously embedded with `embed`.

    Reads the 32-bit length header first, then exactly that many
    payload bits, and decodes them as UTF-8.
    """
    if image.dtype != np.uint8:
        raise ValueError(f"Stego image must be uint8, got {image.dtype}")
    if image.ndim != 3:
        raise ValueError("Stego image must have shape (H, W, C)")

    flat = image.reshape(-1)
    cap = capacity_bits(image)

    if cap < LENGTH_HEADER_BITS:
        raise ValueError("Image is too small to contain a length header.")

    # Pull every LSB we might need; cheaper than repeated slicing.
    header_bits = flat[:LENGTH_HEADER_BITS] & np.uint8(1)
    payload_len = _bits_to_int(header_bits)

    if payload_len < 0 or payload_len > cap - LENGTH_HEADER_BITS:
        raise ValueError(
            f"Invalid payload length {payload_len} — the image likely "
            "does not contain a message embedded by this tool."
        )

    end = LENGTH_HEADER_BITS + payload_len
    payload_bits = flat[LENGTH_HEADER_BITS:end] & np.uint8(1)

    return _bits_to_text(payload_bits)
