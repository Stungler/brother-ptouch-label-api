"""Print one or more image files with rasterprynt-ext."""

from __future__ import annotations

import argparse
from pathlib import Path

import rasterprynt
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("printer_address")
    parser.add_argument("images", type=Path, nargs="+")
    parser.add_argument("--tape-size", default="18mm")
    args = parser.parse_args()

    images: list[Image.Image] = []
    for path in args.images:
        with Image.open(path) as image:
            images.append(image.copy())

    rasterprynt.print_images(
        images,
        args.printer_address,
        tape_size=args.tape_size,
        printer_model="P950NW",
    )


if __name__ == "__main__":
    main()
