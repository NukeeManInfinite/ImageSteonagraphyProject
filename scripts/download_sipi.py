"""Download the classic USC-SIPI 'Miscellaneous' color test images into ./data/.

USC-SIPI is the canonical image-processing test set used in most
steganography / image-quality papers (Lena, Peppers, Mandrill, Airplane, ...).

The full dataset page is https://sipi.usc.edu/database/ — we pull only the
color images from the 'misc' volume, which are the ones useful for LSB
steganography (the method requires RGB channels).

Files are saved as .tiff in their native resolution. Re-run safely: the script
skips files that already exist.

Usage:
    python scripts/download_sipi.py
    python scripts/download_sipi.py --outdir data --convert-png
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://sipi.usc.edu/database/misc/"

# Color files in the USC-SIPI 'misc' volume. Numbers are USC-SIPI's own IDs.
# 4.1.xx = 256x256 color, 4.2.xx = 512x512 color.
COLOR_FILES = [
    "4.1.01.tiff",  # girl
    "4.1.02.tiff",  # couple
    "4.1.03.tiff",  # girl
    "4.1.04.tiff",  # girl
    "4.1.05.tiff",  # house
    "4.1.06.tiff",  # tree
    "4.1.07.tiff",  # jelly beans
    "4.1.08.tiff",  # jelly beans
    "4.2.03.tiff",  # mandrill (baboon)
    # 4.2.04.tiff (Lena) was removed by USC-SIPI in 2024 and is no longer served.
    "4.2.05.tiff",  # airplane (F-16)
    "4.2.06.tiff",  # sailboat on lake
    "4.2.07.tiff",  # peppers
    "house.tiff",   # house (alternate)
]


def _download_one(url: str, dest: Path, timeout: int = 30) -> bool:
    """Fetch `url` into `dest`. Returns True on success, False on failure."""
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip (exists): {dest.name}")
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        dest.write_bytes(data)
        print(f"  got ({len(data) // 1024} KB): {dest.name}")
        return True
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {dest.name}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"  network error for {dest.name}: {e.reason}", file=sys.stderr)
    except Exception as e:
        print(f"  unexpected error for {dest.name}: {e}", file=sys.stderr)
    # Clean partial files so reruns retry cleanly.
    if dest.exists():
        dest.unlink()
    return False


def _convert_to_png(tiff_path: Path) -> Path | None:
    """Convert a .tiff to .png using OpenCV. Returns the new path or None."""
    try:
        import cv2
    except ImportError:
        print("  cv2 not installed — skipping PNG conversion", file=sys.stderr)
        return None

    img = cv2.imread(str(tiff_path), cv2.IMREAD_COLOR)
    if img is None:
        print(f"  could not decode {tiff_path.name}", file=sys.stderr)
        return None
    png_path = tiff_path.with_suffix(".png")
    cv2.imwrite(str(png_path), img)
    return png_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--outdir", default="data",
                   help="Directory to save images into (default: data).")
    p.add_argument("--convert-png", action="store_true",
                   help="Also save .png copies alongside the .tiff originals "
                        "(more convenient for the rest of the pipeline).")
    args = p.parse_args(argv)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {len(COLOR_FILES)} USC-SIPI color images -> {outdir}/")

    ok = fail = 0
    for name in COLOR_FILES:
        success = _download_one(BASE_URL + name, outdir / name)
        if success:
            ok += 1
            if args.convert_png:
                _convert_to_png(outdir / name)
        else:
            fail += 1

    print(f"\ndone: {ok} downloaded, {fail} failed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
