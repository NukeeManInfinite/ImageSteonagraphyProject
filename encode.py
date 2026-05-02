"""CLI: embed a secret message into an image using LSB steganography.

Examples:
    python encode.py --input data/cover.png --output results/stego.png --message "secret"
    python encode.py -i data/cover.png -o results/stego.png -m "hi" --resize 256 --denoise
    python encode.py -i data/cover.png -o results/stego.png --message-file note.txt --report
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from steganography import lsb, utils, metrics


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Embed a secret message into an image (LSB).",
    )
    p.add_argument("-i", "--input", required=True, help="Path to the cover image.")
    p.add_argument("-o", "--output", required=True,
                   help="Path to write the stego image (use .png or .bmp).")

    msg = p.add_mutually_exclusive_group(required=True)
    msg.add_argument("-m", "--message", help="Secret message as a string.")
    msg.add_argument("--message-file",
                     help="Read the secret message from a UTF-8 text file.")

    p.add_argument("--resize", type=int, default=None,
                   help="Resize the cover to N x N before embedding "
                        "(omit to keep original dimensions).")
    p.add_argument("--denoise", action="store_true",
                   help="Apply a light bilateral filter before embedding.")
    p.add_argument("--report", action="store_true",
                   help="Print PSNR/SSIM and save a side-by-side visualization "
                        "next to the output image.")
    return p.parse_args(argv)


def _load_message(args: argparse.Namespace) -> str:
    if args.message is not None:
        return args.message
    path = Path(args.message_file)
    if not path.exists():
        raise FileNotFoundError(f"Message file not found: {path}")
    return path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    message = _load_message(args)
    if not message:
        print("error: message is empty", file=sys.stderr)
        return 2

    size = (args.resize, args.resize) if args.resize else None

    cover = utils.load_image(args.input)
    if size is not None:
        cover = utils.resize_image(cover, size)
    if args.denoise:
        cover = utils.denoise(cover)

    try:
        stego = lsb.embed(cover, message)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    utils.save_image(args.output, stego)
    print(f"embedded {len(message.encode('utf-8'))} bytes -> {args.output}")

    if args.report:
        p = metrics.psnr(cover, stego)
        s = metrics.ssim(cover, stego)
        print(f"PSNR: {p:.2f} dB")
        print(f"SSIM: {s:.6f}")

        viz_path = Path(args.output).with_name(Path(args.output).stem + "_report.png")
        metrics.visualize(cover, stego, save_path=viz_path)
        print(f"report: {viz_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
