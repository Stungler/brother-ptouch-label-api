from PIL import Image

from core.ptp950nw_config import PTP950NW
from printers.rasterprynt_ext import rasterprynt

SUPPORTED_PRINTERS = ("PT-P950NW",)

_legacy_printer_address: str | None = None


def initialize_printer(ip: str, model: str = "PT-P950NW") -> None:
    """Initialize legacy global target printer endpoint."""
    global _legacy_printer_address
    if model not in SUPPORTED_PRINTERS:
        raise NotImplementedError(f"Support for model '{model}' not implemented yet")
    _legacy_printer_address = ip


def get_supported_printers() -> list[str]:
    """Return supported printer model names."""
    return list(SUPPORTED_PRINTERS)


def get_supported_tape_sizes(model: str = "PT-P950NW") -> list[int]:
    """Return supported tape sizes for the requested printer model."""
    if model not in SUPPORTED_PRINTERS:
        raise NotImplementedError(f"Support for '{model}' is not implemented yet")
    return list(PTP950NW.supported_tape_sizes_mm)


def _normalize_to_stripe(
    img: Image.Image,
    tape_mm: float,
    vertical_alignment: str,
    y_offset_px: int = 0,
) -> Image.Image:
    """Fit label image into printer stripe height with alignment and vertical nudge."""
    tape_mm = float(tape_mm)
    stripe_height = PTP950NW.stripe_height(tape_mm)

    if img.mode != "RGB":
        img = img.convert("RGB")

    # Crop if too tall
    if img.height > stripe_height:
        img = img.crop((0, 0, img.width, stripe_height))

    # Pad if too short
    if img.height < stripe_height:
        available_space = stripe_height - img.height
        vertical_alignment = (vertical_alignment or "bottom").lower()

        if vertical_alignment == "top":
            top = 0
        elif vertical_alignment == "center":
            top = available_space // 2
        else:  # bottom
            top = available_space

        # A positive offset moves content toward the top of the tape.
        top -= int(y_offset_px)
        top = max(0, min(top, available_space))

        out = Image.new("RGB", (img.width, stripe_height), "white")
        out.paste(img, (0, top))
        return out

    return img


def print_labels(
    labels: list[Image.Image],
    tape_mm: float = 12,
    vertical_alignment: str = "bottom",
    y_offset_px: int | None = None,
    horizontal_padding_px: tuple[int, int] | None = None,
    top_margin: int = 8,
    bottom_margin: int = 8,
    *,
    v_align: str | None = None,
    pad_lr_px: tuple[int, int] | None = None,
) -> None:
    """Print labels to the legacy globally initialized printer target."""
    if v_align is not None:
        vertical_alignment = v_align
    if pad_lr_px is not None:
        horizontal_padding_px = pad_lr_px

    if _legacy_printer_address is None:
        raise RuntimeError(
            "Printer is not initialized. Call initialize_printer(ip) first."
        )
    print_labels_to_ip(
        labels=labels,
        printer_ip=_legacy_printer_address,
        tape_mm=tape_mm,
        vertical_alignment=vertical_alignment,
        y_offset_px=y_offset_px,
        horizontal_padding_px=horizontal_padding_px,
        top_margin=top_margin,
        bottom_margin=bottom_margin,
    )


def print_labels_to_ip(
    labels: list[Image.Image],
    printer_ip: str,
    tape_mm: float = 12,
    vertical_alignment: str = "bottom",
    y_offset_px: int | None = None,
    horizontal_padding_px: tuple[int, int] | None = None,
    top_margin: int = 8,
    bottom_margin: int = 8,
    *,
    v_align: str | None = None,
    pad_lr_px: tuple[int, int] | None = None,
) -> None:
    """Print labels directly to a specific printer IP address."""
    if not labels:
        raise ValueError("No labels to print")

    if v_align is not None:
        vertical_alignment = v_align
    if pad_lr_px is not None:
        horizontal_padding_px = pad_lr_px

    tape_mm_f = float(tape_mm)

    # Defaults per tape size
    if y_offset_px is None:
        y_offset_px = PTP950NW.y_offset_px(tape_mm_f)
    if horizontal_padding_px is None:
        horizontal_padding_px = PTP950NW.horizontal_padding(tape_mm_f)

    left_px, right_px = horizontal_padding_px

    normalized_labels: list[Image.Image] = []
    for img in labels:
        if left_px or right_px:
            if img.mode != "RGB":
                img = img.convert("RGB")
            canvas = Image.new(
                "RGB", (img.width + left_px + right_px, img.height), "white"
            )
            canvas.paste(img, (left_px, 0))
            img = canvas

        img = _normalize_to_stripe(
            img,
            tape_mm=tape_mm_f,
            vertical_alignment=vertical_alignment,
            y_offset_px=int(y_offset_px),
        )
        normalized_labels.append(img)

    rasterprynt.prynt(
        normalized_labels,
        printer_ip,
        top_margin=top_margin,
        bottom_margin=bottom_margin,
        tape_size=f"{tape_mm_f:g}mm",
        printer_model="P950NW",  # skip autodetect
    )


# Backward-compatible aliases for users of the original Python helper API.
init = initialize_printer
get_supported_TZe_sizes = get_supported_tape_sizes
