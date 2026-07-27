"""Brother raster command generation."""

from __future__ import annotations

import struct
from collections.abc import Iterable, Iterator
from typing import Final

from PIL import Image

from .network import detect_printer_model, send


def _round_up_to_full_byte(value: int) -> int:
    return ((value + 7) // 8) * 8


# Print-head stripe heights in Brother raster units. Values must be divisible
# by eight because each output byte represents eight vertical dots.
STRIPE_SIZE: Final[dict[tuple[str, str], int]] = {
    ("P950NW", "3.5mm"): _round_up_to_full_byte(307),
    ("P950NW", "6mm"): _round_up_to_full_byte(325),
    ("P950NW", "9mm"): _round_up_to_full_byte(345),
    ("P950NW", "12mm"): 368,
    ("P950NW", "18mm"): 408,
    ("P950NW", "24mm"): _round_up_to_full_byte(451),
    ("P950NW", "36mm"): 536,
    ("9800PCN", "18mm"): 312,
}

TAPE_SIZE_DEFAULT = "12mm"
TOP_MARGIN_DEFAULT = 8
BOTTOM_MARGIN_DEFAULT = 8

_INITIALIZE = b"\x1b@"
_ENTER_RASTER_MODE = b"\x1bia\x01"
_DISABLE_AUTO_CUT = b"\x1biM\x00"
_ZERO_MARGIN = b"\x1bid\x00\x00"
_RAW_COMPRESSION = b"M\x00"
_PRINT_WITH_FEED = b"\x1a"
_FORM_FEED = b"\x0c"
_EMPTY_RASTER_LINE = b"Z"


def _prepare_image(image: Image.Image) -> Image.Image:
    """Return an image whose pixels can be converted to monochrome safely."""
    if image.mode == "P":
        image = image.convert("RGBA")

    if image.mode in {"RGBA", "LA"}:
        rgba_image = image.convert("RGBA")
        background = Image.new("RGB", rgba_image.size, "white")
        background.paste(rgba_image, mask=rgba_image.getchannel("A"))
        return background

    if image.mode not in {"1", "L", "RGB"}:
        return image.convert("RGB")
    return image


def _raster_row(
    image: Image.Image,
    x_position: int,
    *,
    stripe_height: int,
    y_offset: int,
) -> bytes:
    pixels = image.load()
    row = bytearray()

    for stripe_index in range(stripe_height // 8):
        value = 0
        for bit_index in range(8):
            y_position = stripe_index * 8 + bit_index - y_offset
            if x_position < image.width and 0 <= y_position < image.height:
                color = pixels[x_position, y_position]
                brightness = color if isinstance(color, int) else sum(color) / 3
                if brightness <= 230:
                    value |= 1 << (7 - bit_index)
        row.append(value)

    return bytes(row)


def render(
    images: Iterable[Image.Image],
    ip: str | None = None,
    top_margin: int = TOP_MARGIN_DEFAULT,
    bottom_margin: int = BOTTOM_MARGIN_DEFAULT,
    printer_model: str | None = None,
    tape_size: str = TAPE_SIZE_DEFAULT,
) -> Iterator[bytes]:
    """Yield Brother raster commands for one or more label images.

    Form-feed commands are inserted between images. Supplying ``printer_model``
    avoids an HTTP model-detection request and is recommended for services that
    already know their configured hardware.
    """
    if top_margin < 0 or bottom_margin < 0:
        raise ValueError("Margins must not be negative")

    yield b"\x00" * 200

    if printer_model is None:
        if not ip:
            raise ValueError("ip is required when printer_model is not supplied")
        printer_model = detect_printer_model(ip)
        if printer_model is None:
            raise ValueError(f"Could not detect a supported printer at {ip}")

    media_key = (printer_model, tape_size)
    if media_key not in STRIPE_SIZE:
        raise ValueError(f"Unsupported tape size {tape_size} for {printer_model}")

    stripe_height = STRIPE_SIZE[media_key]
    if stripe_height % 8:
        raise ValueError(f"Stripe height must be divisible by 8; got {stripe_height}")

    yield _INITIALIZE
    yield _ENTER_RASTER_MODE
    yield _DISABLE_AUTO_CUT
    yield _ZERO_MARGIN

    for page_index, source_image in enumerate(images):
        if page_index:
            yield _FORM_FEED

        image = _prepare_image(source_image)
        cut_correction = 0

        if printer_model == "P950NW":
            raster_line_count = image.width + top_margin + bottom_margin
            yield (
                b"\x1biz\xc0\x00\x00\x00" + struct.pack("<I", raster_line_count) + b"\x01" + b"\x00"
            )
        elif printer_model == "9800PCN":
            yield b"\x1bic\x8e\x01\x12\x00\x00"
            yield b"\x1bid" + struct.pack("!B", 0) + b"\x00"
            cut_correction = 8
        else:  # Defensive guard for future mapping edits.
            raise ValueError(f"Unsupported printer model: {printer_model}")

        if top_margin < cut_correction:
            raise ValueError(
                f"Top margin {top_margin} is smaller than the "
                f"{cut_correction}-dot cut correction for {printer_model}"
            )

        yield _RAW_COMPRESSION
        yield _EMPTY_RASTER_LINE * (top_margin - cut_correction)

        y_offset = (stripe_height - image.height) // 2
        for x_position in range(image.width):
            row = _raster_row(
                image,
                x_position,
                stripe_height=stripe_height,
                y_offset=y_offset,
            )
            yield b"G" + struct.pack("<H", len(row))
            yield row

        yield _EMPTY_RASTER_LINE * (bottom_margin + cut_correction)

    yield _PRINT_WITH_FEED


def render_bytes(
    images: Iterable[Image.Image],
    ip: str | None = None,
    top_margin: int = TOP_MARGIN_DEFAULT,
    bottom_margin: int = BOTTOM_MARGIN_DEFAULT,
    tape_size: str = TAPE_SIZE_DEFAULT,
    printer_model: str | None = None,
) -> bytes:
    """Return all raster commands as one byte string."""
    return b"".join(
        render(
            images,
            ip=ip,
            top_margin=top_margin,
            bottom_margin=bottom_margin,
            tape_size=tape_size,
            printer_model=printer_model,
        )
    )


def cat(
    images: Iterable[Image.Image],
    ip: str | None = None,
    top_margin: int = TOP_MARGIN_DEFAULT,
    bottom_margin: int = BOTTOM_MARGIN_DEFAULT,
    tape_size: str = TAPE_SIZE_DEFAULT,
    printer_model: str | None = None,
) -> bytes:
    """Backward-compatible alias for :func:`render_bytes`."""
    return render_bytes(
        images,
        ip=ip,
        top_margin=top_margin,
        bottom_margin=bottom_margin,
        tape_size=tape_size,
        printer_model=printer_model,
    )


def print_images(
    images: Iterable[Image.Image],
    address: str,
    top_margin: int = TOP_MARGIN_DEFAULT,
    bottom_margin: int = BOTTOM_MARGIN_DEFAULT,
    tape_size: str = TAPE_SIZE_DEFAULT,
    printer_model: str | None = None,
) -> None:
    """Render images and send them to a network printer."""
    data = render_bytes(
        images,
        ip=address,
        top_margin=top_margin,
        bottom_margin=bottom_margin,
        tape_size=tape_size,
        printer_model=printer_model,
    )
    send(data, address)


def prynt(
    images: Iterable[Image.Image],
    ip: str,
    top_margin: int = TOP_MARGIN_DEFAULT,
    bottom_margin: int = BOTTOM_MARGIN_DEFAULT,
    tape_size: str = TAPE_SIZE_DEFAULT,
    printer_model: str | None = None,
) -> None:
    """Backward-compatible alias for :func:`print_images`."""
    print_images(
        images,
        ip,
        top_margin=top_margin,
        bottom_margin=bottom_margin,
        tape_size=tape_size,
        printer_model=printer_model,
    )
