from PIL import Image, ImageDraw

from printers.rasterprynt_ext import rasterprynt

PX_PER_MM = 12


def tape_height_px(tape_mm: int) -> int:
    """Convert a physical tape width to the renderer's approximate pixel height."""
    return int(tape_mm * PX_PER_MM)


def create_alignment_test_image(tape_mm: int, width_px: int = 600) -> Image.Image:
    """Create a ruled image for measuring vertical tape alignment."""
    height = tape_height_px(tape_mm)
    image = Image.new("RGB", (width_px, height), "white")
    draw = ImageDraw.Draw(image)

    for y in range(0, height, 4):
        draw.line([(0, y), (width_px - 1, y)], fill="black")

    for y in range(0, height, 12):
        draw.line([(0, y), (width_px - 1, y)], fill="black", width=2)
        draw.text((5, y + 1), f"y={y}", fill="black")

    draw.text((width_px - 80, 2), "TOP", fill="black")
    draw.text((width_px - 110, height - 18), "BOTTOM", fill="black")

    return image


def describe_raster_alignment(
    image: Image.Image,
    tape_mm: float,
    printer_model: str = "P950NW",
) -> None:
    """Print the image and transport stripe dimensions for calibration."""
    tape_key = f"{tape_mm:g}mm"
    stripe = rasterprynt.STRIPE_SIZE[(printer_model, tape_key)]
    print("tape:", tape_key, "printer_model:", printer_model)
    print("image.size (W,H):", image.size)
    print("stripe_size:", stripe)
    print("stripe - image.height:", stripe - image.height)
    print("expected y_offset (centered):", (stripe - image.height) // 2)
