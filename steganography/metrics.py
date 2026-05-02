"""Quality metrics and visualization for stego vs. cover images.

PSNR and SSIM are computed on uint8 images (data_range=255), which is the
conventional choice and matches how most steganography papers report numbers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import matplotlib.pyplot as plt
import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------

def psnr(original: np.ndarray, stego: np.ndarray) -> float:
    """Peak Signal-to-Noise Ratio in dB. Higher is better; >40 dB is typical for LSB."""
    _check_pair(original, stego)
    if np.array_equal(original, stego):
        return float("inf")
    return float(peak_signal_noise_ratio(original, stego, data_range=255))


def ssim(original: np.ndarray, stego: np.ndarray) -> float:
    """Structural Similarity Index, in [-1, 1]. 1.0 = identical."""
    _check_pair(original, stego)
    # channel_axis=-1 tells skimage to compute SSIM per channel and average.
    return float(
        structural_similarity(original, stego, channel_axis=-1, data_range=255)
    )


def difference_map(original: np.ndarray, stego: np.ndarray,
                   amplify: int = 32) -> np.ndarray:
    """Absolute per-pixel difference, amplified for visualization.

    LSB changes are at most +/-1 per channel, invisible without scaling.
    Returns a uint8 BGR image suitable for saving or display.
    """
    _check_pair(original, stego)
    diff = cv2.absdiff(original, stego).astype(np.int32) * amplify
    return np.clip(diff, 0, 255).astype(np.uint8)


def _check_pair(a: np.ndarray, b: np.ndarray) -> None:
    if a.shape != b.shape:
        raise ValueError(f"Shape mismatch: {a.shape} vs {b.shape}")
    if a.dtype != np.uint8 or b.dtype != np.uint8:
        raise ValueError("Both images must be uint8")


# ---------------------------------------------------------------------------
# visualization
# ---------------------------------------------------------------------------

def visualize(
    original: np.ndarray,
    stego: np.ndarray,
    save_path: Optional[str | Path] = None,
    show: bool = False,
    amplify: int = 32,
) -> None:
    """Show original / stego / amplified difference side-by-side.

    Images are expected as uint8 BGR (OpenCV convention); they are
    converted to RGB for matplotlib display.
    """
    _check_pair(original, stego)
    diff = difference_map(original, stego, amplify=amplify)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    titles = ["Original (cover)", "Stego", f"|diff|  x{amplify}"]
    imgs = [original, stego, diff]

    for ax, img, title in zip(axes, imgs, titles):
        ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        ax.set_title(title)
        ax.axis("off")

    fig.suptitle(
        f"PSNR = {psnr(original, stego):.2f} dB   |   "
        f"SSIM = {ssim(original, stego):.6f}"
    )
    fig.tight_layout()

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
