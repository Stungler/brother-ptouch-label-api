import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api.routes import font_check, supported_sizes
from main import app


class AppSmokeTest(unittest.TestCase):
    def test_application_starts_and_exposes_core_endpoints(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "printers.json"

            async def exercise_lifespan():
                async with app.router.lifespan_context(app):
                    self.assertTrue(registry_path.exists())

            with patch.dict(
                os.environ,
                {"PRINTER_REGISTRY_PATH": str(registry_path)},
            ):
                asyncio.run(exercise_lifespan())

            self.assertEqual(
                supported_sizes()["sizes"],
                [6, 9, 12, 18, 24, 36],
            )

            self.assertEqual(font_check()["status"], "ok")

            openapi_schema = app.openapi()
            self.assertEqual(
                openapi_schema["info"]["title"],
                "labelprynt",
            )


if __name__ == "__main__":
    unittest.main()
