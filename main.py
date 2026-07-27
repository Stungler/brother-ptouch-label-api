from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router as printer_router
from core.print_queue import init_printer_queue_manager, stop_printer_queue_manager
from core.printer_registry import init_printer_registry


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize process-wide services and stop queue workers cleanly."""
    init_printer_registry()
    init_printer_queue_manager()
    yield
    stop_printer_queue_manager()


app = FastAPI(
    title="Brother P-touch Network Label API",
    description=(
        "Generate text and QR-code labels and print them directly to a supported "
        "Brother P-touch printer over the network."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(printer_router)
