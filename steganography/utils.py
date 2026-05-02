"""Image preprocessing and I/O helpers.

All functions keep images as uint8 BGR ndarrays (OpenCV's native format),
because LSB steganography operates on integer pixel values. Normalization
to float [0, 1] is provided separately for metric/visualization use only —
it must NOT be applied before embedding.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import cv2
import numpy as np


DEFAULT_SIZE: Tuple[int, int] = (256, 256)


def load_image(path: str | Path) -> np.ndarray:
    """Load an image as a uint8 BGR array.

    Raises FileNotFoundError if the path is unreadable or not a valid image.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Could not decode image: {path}")
    return img


def save_image(path: str | Path, img: np.ndarray) -> None:
    """Save a uint8 BGR image losslessly.

    For stego images we enforce PNG (lossless). JPEG would destroy the LSBs.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix.lower() in {".jpg", ".jpeg"}:
        raise ValueError(
            f"Refusing to save stego image as {path.suffix} — "
            "lossy formats destroy LSB data. Use .png or .bmp."
        )

    if img.dtype != np.uint8:
        raise ValueError(f"Expected uint8 image, got {img.dtype}")

    ok = cv2.imwrite(str(path), img)
    if not ok:
        raise IOError(f"Failed to write image: {path}")


def resize_image(img: np.ndarray, size: Tuple[int, int] = DEFAULT_SIZE) -> np.ndarray:
    """Resize to (width, height). Uses area interpolation for downscaling."""
    h, w = img.shape[:2]
    target_w, target_h = size
    interp = cv2.INTER_AREA if (target_w < w or target_h < h) else cv2.INTER_CUBIC
    return cv2.resize(img, (target_w, target_h), interpolation=interp)


def denoise(img: np.ndarray, strength: int = 3) -> np.ndarray:
    """Optional light denoising via bilateral filter.

    Bilateral preserves edges better than Gaussian, which matters because
    edge pixels are where LSB changes are least perceptible.
    """
    return cv2.bilateralFilter(img, d=strength, sigmaColor=50, sigmaSpace=50)


def normalize(img: np.ndarray) -> np.ndarray:
    """Scale uint8 image to float32 in [0, 1].

    For visualization / metrics only — never feed this back into embedding.
    """
    return img.astype(np.float32) / 255.0


def preprocess(
    path: str | Path,
    size: Tuple[int, int] = DEFAULT_SIZE,
    apply_denoise: bool = False,
) -> np.ndarray:
    """Full preprocessing pipeline for the cover image.

    Returns a uint8 BGR image ready for LSB embedding.
    """
    img = load_image(path)
    img = resize_image(img, size)
    if apply_denoise:
        img = denoise(img)
    return img
