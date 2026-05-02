"""CLI: extract a hidden message from a stego image.

Examples:
    python decode.py --input results/stego.png
    python decode.py -i results/stego.png --output-file recovered.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from steganography import lsb, utils


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Extract a hidden message from an LSB stego image.",
    )
    p.add_argument("-i", "--input", required=True, help="Path to the stego image.")
    p.add_argument("--output-file", default=None,
                   help="If given, write the recovered message to this file "
                        "(UTF-8). Otherwise print it to stdout.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    stego = utils.load_image(args.input)

    try:
        message = lsb.extract(stego)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.output_file:
        Path(args.output_file).write_text(message, encoding="utf-8")
        print(f"recovered {len(message.encode('utf-8'))} bytes -> {args.output_file}")
    else:
        print(message)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
