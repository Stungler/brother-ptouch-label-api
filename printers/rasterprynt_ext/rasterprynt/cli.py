"""Command-line interface for raster printing."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from .network import detect_printer_model
from .protocol import (
    BOTTOM_MARGIN_DEFAULT,
    TAPE_SIZE_DEFAULT,
    TOP_MARGIN_DEFAULT,
    print_images,
    render_bytes,
)


def _load_images(paths: list[Path]) -> list[Image.Image]:
    images: list[Image.Image] = []
    for path in paths:
        with Image.open(path) as image:
            images.append(image.copy())
    return images


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rasterprynt",
        description="Print raster images on a supported Brother P-touch printer.",
    )
    parser.add_argument("address", help="Printer IP address or hostname")
    parser.add_argument("images", metavar="IMAGE", nargs="*", type=Path)
    parser.add_argument(
        "--to-file",
        type=Path,
        metavar="FILE",
        help="Write command bytes to a file instead of printing",
    )
    parser.add_argument(
        "--detect-device",
        action="store_true",
        help="Detect the printer model and exit",
    )
    parser.add_argument(
        "--printer-model",
        choices=("P950NW", "9800PCN"),
        help="Skip HTTP model detection by specifying the model",
    )
    parser.add_argument(
        "--top-margin",
        default=TOP_MARGIN_DEFAULT,
        type=int,
        metavar="DOTS",
        help="Blank raster lines before each image (default: %(default)s)",
    )
    parser.add_argument(
        "--bottom-margin",
        default=BOTTOM_MARGIN_DEFAULT,
        type=int,
        metavar="DOTS",
        help="Blank raster lines after each image (default: %(default)s)",
    )
    parser.add_argument(
        "--tape-size",
        default=TAPE_SIZE_DEFAULT,
        metavar="WIDTH",
        help="Tape width such as 6mm, 12mm, or 18mm (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.detect_device:
        if args.images:
            parser.error("Images cannot be supplied with --detect-device")
        model = detect_printer_model(args.address)
        print(model or "unknown")
        return 0 if model else 1

    if not args.images:
        parser.error("At least one image is required")

    images = _load_images(args.images)
    common_options = {
        "top_margin": args.top_margin,
        "bottom_margin": args.bottom_margin,
        "tape_size": args.tape_size,
        "printer_model": args.printer_model,
    }

    if args.to_file:
        data = render_bytes(images, ip=args.address, **common_options)
        args.to_file.write_bytes(data)
        return 0

    print_images(images, args.address, **common_options)
    return 0
