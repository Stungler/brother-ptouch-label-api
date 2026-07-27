import json
import tempfile
import unittest
from pathlib import Path

from api.schemas import PrinterCreateRequest, PrinterUpdateRequest
from core.printer_registry import PrinterRegistry


class PrinterRegistryTest(unittest.TestCase):
    def test_create_update_reload_and_delete(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "printers.json"
            registry = PrinterRegistry(str(registry_path))
            registry.load()

            created = registry.create(
                PrinterCreateRequest(
                    printer_id="labels-18mm",
                    name="Test printer",
                    ip="192.0.2.10",
                    tape_size_mm=18,
                )
            )
            self.assertTrue(created.enabled)

            updated = registry.update(
                "labels-18mm",
                PrinterUpdateRequest(name="Updated printer"),
            )
            self.assertEqual(updated.name, "Updated printer")

            reloaded = PrinterRegistry(str(registry_path))
            reloaded.load()
            self.assertEqual(reloaded.get("labels-18mm").name, "Updated printer")

            reloaded.delete("labels-18mm")
            self.assertEqual(reloaded.list(), [])
            self.assertEqual(
                json.loads(registry_path.read_text(encoding="utf-8")),
                {"printers": []},
            )

    def test_auto_is_reserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = PrinterRegistry(str(Path(temp_dir) / "printers.json"))
            registry.load()
            with self.assertRaises(ValueError):
                registry.create(
                    PrinterCreateRequest(
                        printer_id="auto",
                        name="Reserved",
                        ip="192.0.2.10",
                        tape_size_mm=18,
                    )
                )


if __name__ == "__main__":
    unittest.main()
