from enum import Enum
from pathlib import Path

import segno
from PIL import Image, ImageDraw, ImageFont, ImageOps

PX_PER_MM = 12  # Brother PT-P950NW @ 300 DPI
QUIET_ZONE_MM = 1.0  # quiet zone around QR (scanner-friendly)

DEFAULT_ROTATION = 0
FONT_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "fonts" / "DejaVuSans.ttf"
)


def get_font_check() -> dict:
    exists = FONT_PATH.exists()
    loadable = False
    error = None

    if exists:
        try:
            ImageFont.truetype(str(FONT_PATH), 12)
            loadable = True
        except OSError as exc:
            error = str(exc)
    else:
        error = f"font file not found: {FONT_PATH}"

    return {
        "font": "DejaVuSans.ttf",
        "path": str(FONT_PATH),
        "exists": exists,
        "loadable": loadable,
        "error": error,
    }


# Label canvas heights before the transport pads to the full print-head stripe.
EXPECTED_RASTER_H_PX = {
    6: 64,
    9: 84,
    12: 128,
    18: 192,
    24: 256,
    36: 384,
}

# Vertical placement inside the head raster.
TAPE_Y_OFFSET_PX = {
    6: 64,
    9: 44,
    12: 0,
    18: 0,
    24: 0,
    36: 0,
}


def _normalize_to_printer_raster(img: Image.Image, tape_size: float) -> Image.Image:
    tape_key = int(tape_size)
    target_h = EXPECTED_RASTER_H_PX.get(tape_key)

    # If unknown tape size, just return flattened image
    if not target_h:
        if img.mode == "RGBA":
            white_bg = Image.new("RGB", img.size, "white")
            white_bg.paste(img, mask=img.split()[3])
            return white_bg
        return img.convert("RGB")

    # Flatten to white (printer wants RGB/1-bit ultimately; no alpha)
    if img.mode == "RGBA":
        white_bg = Image.new("RGB", img.size, "white")
        white_bg.paste(img, mask=img.split()[3])
        img = white_bg
    else:
        img = img.convert("RGB")

    canvas = Image.new("RGB", (img.width, target_h), "white")

    # Crop if too tall (center-crop)
    if img.height > target_h:
        top = (img.height - target_h) // 2
        img = img.crop((0, top, img.width, top + target_h))

    # Paste with tape-specific y offset, clamped to bounds
    y_off = TAPE_Y_OFFSET_PX.get(tape_key, 0)
    y = (target_h - img.height) // 2 + y_off
    y = max(0, min(y, target_h - img.height))

    canvas.paste(img, (0, y))
    return canvas


LABEL_PADDING = {
    width: {"padding_tb": 0, "padding_lr": 0} for width in EXPECTED_RASTER_H_PX
}


class LabelType(str, Enum):
    TEXT = "TEXT"
    QR = "QR"
    TEXT_QR = "TEXT_QR"


class QrMode(str, Enum):
    AUTO = "auto"
    MICRO = "micro"
    REGULAR = "regular"


def _tape_height_px(tape_size: float) -> int:
    return int(tape_size * PX_PER_MM)


def _white_to_transparent(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size

    for y in range(h):
        for x in range(w):
            if px[x, y][:3] == (255, 255, 255):
                px[x, y] = (0, 0, 0, 0)

    return img


def _apply_padding_and_rotation(
    img: Image.Image,
    tape_size: float,
    rotation: int = DEFAULT_ROTATION,
) -> Image.Image:
    # Flatten label to white background
    if img.mode == "RGBA":
        white_bg = Image.new("RGB", img.size, "white")
        white_bg.paste(img, mask=img.split()[3])
        img = white_bg
    else:
        img = img.convert("RGB")

    cfg = LABEL_PADDING.get(
        tape_size,
        {"padding_tb": 0, "padding_lr": 0},
    )

    img = ImageOps.expand(
        img,
        border=(
            cfg["padding_lr"],
            cfg["padding_tb"],
            cfg["padding_lr"],
            cfg["padding_tb"],
        ),
        fill="white",
    )

    img = img.rotate(rotation, expand=True)
    img = _normalize_to_printer_raster(img, tape_size)
    return img


def _font_for_height(target_height: int) -> ImageFont.FreeTypeFont:
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"Required font not found: {FONT_PATH}")

    font_path = str(FONT_PATH)

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)

    for size in range(target_height, 5, -1):
        font = ImageFont.truetype(font_path, size)
        _, top, _, bottom = draw.textbbox((0, 0), "Ag", font=font)
        if (bottom - top) <= target_height:
            return font

    return ImageFont.truetype(font_path, 6)


def _render_text(text: str, tape_size: float) -> Image.Image:
    target_height = _tape_height_px(tape_size)
    font = _font_for_height(target_height)

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)

    img = Image.new(
        "RGBA",
        (right - left, bottom - top),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(img)
    draw.text((-left, -top), text, fill=(0, 0, 0, 255), font=font)

    return img


def _render_qr(text: str, tape_size: float, mode: QrMode = QrMode.AUTO) -> Image.Image:
    total = _tape_height_px(tape_size)
    qz = int(QUIET_ZONE_MM * PX_PER_MM)
    inner = max(1, total - 2 * qz)

    def make_regular():
        return segno.make(text, micro=False)

    def make_micro():
        # micro QR has limited capacity; may raise depending on content
        return segno.make(text, micro=True)

    if mode == QrMode.REGULAR:
        code_obj = make_regular()
    elif mode == QrMode.MICRO:
        code_obj = make_micro()
    else:
        # AUTO: try micro on small tape, else regular
        if tape_size <= 6:
            try:
                code_obj = make_micro()
            # Segno may raise different data/encoding errors depending on input.
            except Exception:  # noqa: BLE001
                code_obj = make_regular()
        else:
            code_obj = make_regular()

    code = code_obj.to_pil(scale=10, border=0).convert("RGBA")
    code = code.resize((inner, inner), Image.NEAREST)
    code = _white_to_transparent(code)

    canvas = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    canvas.paste(code, (qz, qz), code)
    return canvas


def _compose_horizontal(
    left: Image.Image,
    right: Image.Image,
    spacing_mm: float,
) -> Image.Image:
    spacing_px = int(spacing_mm * PX_PER_MM)

    height = max(left.height, right.height)
    width = left.width + spacing_px + right.width

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    canvas.paste(left, (0, (height - left.height) // 2), left)
    canvas.paste(
        right,
        (left.width + spacing_px, (height - right.height) // 2),
        right,
    )

    return canvas


def _text_label(text: str, tape_size: float) -> Image.Image:
    return _apply_padding_and_rotation(
        _render_text(text, tape_size),
        tape_size,
    )


def _qr_only_label(
    text: str, tape_size: float, mode: QrMode = QrMode.AUTO
) -> Image.Image:
    return _apply_padding_and_rotation(
        _render_qr(text, tape_size, mode=mode),
        tape_size,
    )


def _text_qr_label(
    text: str, tape_size: float, mode: QrMode = QrMode.AUTO
) -> Image.Image:
    qr_img = _render_qr(text, tape_size, mode=mode)

    pad_px = int(QUIET_ZONE_MM * PX_PER_MM)
    target_text_height = qr_img.height - 2 * pad_px

    font = _font_for_height(target_text_height)

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)

    text_img = Image.new(
        "RGBA",
        (right - left, target_text_height),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(text_img)

    glyph_height = bottom - top
    y = (target_text_height - glyph_height) // 2 - top

    draw.text(
        (-left, y),
        text,
        fill=(0, 0, 0, 255),
        font=font,
    )

    canvas = _compose_horizontal(
        text_img,
        qr_img,
        spacing_mm=min(2, tape_size * 0.25),
    )

    return _apply_padding_and_rotation(
        canvas,
        tape_size,
    )


def generate_label(
    text: str,
    label_type: LabelType,
    tape_size: float,
    copies: int = 1,
    qr_mode: QrMode = QrMode.AUTO,
) -> list[Image.Image]:
    """Render one or more label images without sending them to a printer."""
    if not text:
        raise ValueError("Label text must not be empty")
    if copies < 1:
        raise ValueError("copies must be at least 1")

    match label_type:
        case LabelType.TEXT:
            img = _text_label(text, tape_size)
        case LabelType.QR:
            img = _qr_only_label(text, tape_size, mode=qr_mode)
        case LabelType.TEXT_QR:
            img = _text_qr_label(text, tape_size, mode=qr_mode)
        case _:
            raise ValueError(f"Invalid label type: {label_type}")

    return [img.copy() for _ in range(copies)]
