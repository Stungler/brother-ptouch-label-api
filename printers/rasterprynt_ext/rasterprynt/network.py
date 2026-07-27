"""Printer discovery and raw TCP transport helpers."""

from __future__ import annotations

import logging
import socket
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

LOGGER = logging.getLogger(__name__)

RAW_PRINT_PORT = 9100
MODEL_CACHE_SECONDS = 3600
MODEL_HTTP_TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True, slots=True)
class _ModelCacheEntry:
    cached_at: float
    model: str


_MODEL_CACHE: dict[str, _ModelCacheEntry] = {}


def clear_model_cache() -> None:
    """Clear cached printer model detections."""
    _MODEL_CACHE.clear()


def detect_printer_model(
    address: str,
    *,
    cache_seconds: int = MODEL_CACHE_SECONDS,
    timeout_seconds: float = MODEL_HTTP_TIMEOUT_SECONDS,
) -> str | None:
    """Detect a supported printer model through its embedded HTTP interface.

    Results are cached by address. ``None`` is returned when the printer is
    unreachable or its model cannot be identified.
    """
    now = time.monotonic()
    cached = _MODEL_CACHE.get(address)
    if cached and cached.cached_at + max(0, cache_seconds) > now:
        return cached.model

    try:
        model = _detect_printer_model_uncached(
            address,
            timeout_seconds=timeout_seconds,
        )
    except URLError as exc:
        LOGGER.warning("Failed to detect printer at %s: %s", address, exc)
        return None

    if model:
        _MODEL_CACHE[address] = _ModelCacheEntry(cached_at=now, model=model)
    return model


def _detect_printer_model_uncached(
    address: str,
    *,
    timeout_seconds: float,
) -> str | None:
    url = f"http://{address}/admin/default.html"
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            html = response.read()
    except HTTPError as exc:
        if exc.code != 401:
            raise
        html = exc.read()

    normalized_html = html.lower()
    if b"brother pt-9800pcn" in normalized_html:
        return "9800PCN"
    if b"brother pt-p950nw" in normalized_html:
        return "P950NW"
    return None


def send(
    data: bytes,
    address: str,
    *,
    port: int = RAW_PRINT_PORT,
    timeout_seconds: float | None = None,
) -> None:
    """Send pre-rendered command bytes to a printer's raw TCP socket."""
    with socket.create_connection(
        (address, port),
        timeout=timeout_seconds,
    ) as connection:
        connection.sendall(data)
