"""End-to-end demo: preprocess -> embed -> extract -> evaluate -> visualize.

Run:
    python main.py --input data/cover.png --message "hello world"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from steganography import lsb, utils, metrics


DEFAULT_MESSAGE = "The quick brown fox jumps over the lazy dog."


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LSB steganography end-to-end demo.")
    p.add_argument("-i", "--input", required=True, help="Cover image path.")
    p.add_argument("-m", "--message", default=DEFAULT_MESSAGE,
                   help="Message to hide.")
    p.add_argument("--resize", type=int, default=256,
                   help="Square resize dimension (default: 256).")
    p.add_argument("--outdir", default="results",
                   help="Directory for stego image and report (default: results).")
    p.add_argument("--show", action="store_true",
                   help="Display the visualization window.")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 1. preprocess
    cover = utils.preprocess(args.input, size=(args.resize, args.resize))
    print(f"cover: {cover.shape}  capacity: {lsb.max_message_bytes(cover)} bytes")

    # 2. embed
    stego = lsb.embed(cover, args.message)
    stego_path = outdir / "stego.png"
    utils.save_image(stego_path, stego)
    print(f"stego saved: {stego_path}")

    # 3. extract (round-trip check)
    recovered = lsb.extract(stego)
    ok = recovered == args.message
    print(f"recovered: {recovered!r}")
    print(f"round-trip ok: {ok}")

    # 4. metrics
    p = metrics.psnr(cover, stego)
    s = metrics.ssim(cover, stego)
    print(f"PSNR: {p:.2f} dB")
    print(f"SSIM: {s:.6f}")

    # 5. visualize
    report_path = outdir / "report.png"
    metrics.visualize(cover, stego, save_path=report_path, show=args.show)
    print(f"report saved: {report_path}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
