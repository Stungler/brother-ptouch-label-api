"""Brother P-touch raster encoding and network transport.

This package is derived from Philipp Hagemeister's MIT-licensed ``rasterprynt``
project and extended for additional PT-P950NW tape widths.
"""

from .network import clear_model_cache, detect_printer_model, send
from .protocol import (
    BOTTOM_MARGIN_DEFAULT,
    STRIPE_SIZE,
    TAPE_SIZE_DEFAULT,
    TOP_MARGIN_DEFAULT,
    cat,
    print_images,
    prynt,
    render,
    render_bytes,
)

__version__ = "1.2.0"

__all__ = [
    "BOTTOM_MARGIN_DEFAULT",
    "STRIPE_SIZE",
    "TAPE_SIZE_DEFAULT",
    "TOP_MARGIN_DEFAULT",
    "__version__",
    "cat",
    "clear_model_cache",
    "detect_printer_model",
    "print_images",
    "prynt",
    "render",
    "render_bytes",
    "send",
]
