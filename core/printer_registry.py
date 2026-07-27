from __future__ import annotations

import builtins
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from api.schemas import PrinterCreateRequest, PrinterRecord, PrinterUpdateRequest


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PrinterRegistry:
    """Thread-safe JSON-backed registry for configured printers."""

    def __init__(self, file_path: str):
        self._file_path = Path(file_path)
        self._lock = RLock()
        self._printers: dict[str, PrinterRecord] = {}

    def load(self) -> None:
        """Load registry from disk or initialize an empty persisted store."""
        with self._lock:
            if not self._file_path.exists():
                self._file_path.parent.mkdir(parents=True, exist_ok=True)
                self._persist_unlocked()
                return

            with self._file_path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)

            records = raw.get("printers", [])
            self._printers = {
                item["printer_id"]: PrinterRecord(**item) for item in records
            }

    def list(self) -> builtins.list[PrinterRecord]:
        """Return all printers sorted by printer_id."""
        with self._lock:
            return sorted(self._printers.values(), key=lambda item: item.printer_id)

    def get(self, printer_id: str) -> PrinterRecord | None:
        """Return one printer by id, or None if it does not exist."""
        with self._lock:
            return self._printers.get(printer_id)

    def create(self, payload: PrinterCreateRequest) -> PrinterRecord:
        """Create and persist a new printer entry."""
        with self._lock:
            if payload.printer_id == "auto":
                raise ValueError("Printer id 'auto' is reserved")

            if payload.printer_id in self._printers:
                raise ValueError(f"Printer '{payload.printer_id}' already exists")

            now = _utc_now_iso()
            printer = PrinterRecord(
                printer_id=payload.printer_id,
                name=payload.name,
                ip=payload.ip,
                model=payload.model,
                tape_size_mm=payload.tape_size_mm,
                enabled=True,
                created_at=now,
                updated_at=now,
            )

            self._printers[printer.printer_id] = printer
            self._persist_unlocked()
            return printer

    def update(self, printer_id: str, payload: PrinterUpdateRequest) -> PrinterRecord:
        """Update mutable fields of an existing printer and persist changes."""
        with self._lock:
            current = self._printers.get(printer_id)
            if current is None:
                raise KeyError(printer_id)

            data = current.model_dump()
            changes = payload.model_dump(exclude_unset=True)
            data.update(changes)
            data["updated_at"] = _utc_now_iso()

            updated = PrinterRecord(**data)
            self._printers[printer_id] = updated
            self._persist_unlocked()
            return updated

    def delete(self, printer_id: str) -> None:
        """Delete a printer from the registry and persist changes."""
        with self._lock:
            if printer_id not in self._printers:
                raise KeyError(printer_id)
            del self._printers[printer_id]
            self._persist_unlocked()

    def _persist_unlocked(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"printers": [item.model_dump() for item in self.list()]}
        with self._file_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)


_registry: PrinterRegistry | None = None


def init_printer_registry(file_path: str | None = None) -> PrinterRegistry:
    """Initialize global registry singleton from explicit path or environment."""
    global _registry

    path = file_path or os.getenv("PRINTER_REGISTRY_PATH", "data/printers.json")
    _registry = PrinterRegistry(path)
    _registry.load()
    return _registry


def get_printer_registry() -> PrinterRegistry:
    """Return initialized global registry singleton."""
    global _registry
    if _registry is None:
        _registry = init_printer_registry()
    return _registry
