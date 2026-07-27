import hashlib
import unittest
from unittest.mock import patch

import rasterprynt
from PIL import Image

GOLDEN_OUTPUTS = {
    ("P950NW", "3.5mm"): (
        509,
        "be2d43f6f6a493944b09ec383e04e6a688f8d8d4c25f4e751303b79feb1fbbad",
    ),
    ("P950NW", "6mm"): (
        521,
        "72747e15cd1b2d2f4b7d4a16ead12bddafe7fce8345704c8004b07b034d8b14e",
    ),
    ("P950NW", "9mm"): (
        539,
        "d48a2d62bb9db2736afdd12d1ad639ac2d994d65c0f62ce7627b553b64b9c216",
    ),
    ("P950NW", "12mm"): (
        551,
        "15a976a68baa07fb6f98a5f6b90a5e7d808f263e3ca7bb9c1c513082a56fdf0f",
    ),
    ("P950NW", "18mm"): (
        581,
        "9b594c4402ed609deeb1d41f5bb3540b9549b39a28a98daf13d0937eaabb9be5",
    ),
    ("P950NW", "24mm"): (
        617,
        "302570e1e5be540cbb6695438721f79f34d65cabfc403778413c92033b1f1f84",
    ),
    ("P950NW", "36mm"): (
        677,
        "9d3c85b00951d7e0ac119884b78695f5651318d7d8287d32c94deb4f50a7a855",
    ),
    ("9800PCN", "18mm"): (
        525,
        "2af7045556bc76f93a242d58540ac4570884faaccabbe2211cbc9854bc5378d4",
    ),
}


def create_fixture_images() -> list[Image.Image]:
    first = Image.new("RGB", (4, 3), "white")
    first.putpixel((0, 0), (0, 0, 0))
    first.putpixel((3, 2), (0, 0, 0))

    second = Image.new("RGB", (2, 5), "white")
    second.putpixel((1, 1), (0, 0, 0))
    return [first, second]


class ProtocolTest(unittest.TestCase):
    def test_refactor_preserves_golden_command_bytes(self):
        for (model, tape_size), (expected_length, expected_hash) in GOLDEN_OUTPUTS.items():
            with self.subTest(model=model, tape_size=tape_size):
                top_margin = 10 if model == "9800PCN" else 2
                data = rasterprynt.render_bytes(
                    create_fixture_images(),
                    top_margin=top_margin,
                    bottom_margin=3,
                    tape_size=tape_size,
                    printer_model=model,
                )

                self.assertEqual(len(data), expected_length)
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected_hash)

    def test_legacy_cat_name_matches_render_bytes(self):
        options = {
            "tape_size": "18mm",
            "printer_model": "P950NW",
        }
        self.assertEqual(
            rasterprynt.cat(create_fixture_images(), **options),
            rasterprynt.render_bytes(create_fixture_images(), **options),
        )

    @patch("rasterprynt.protocol.send")
    def test_legacy_prynt_name_sends_rendered_bytes(self, mock_send):
        rasterprynt.prynt(
            create_fixture_images(),
            "192.0.2.10",
            tape_size="18mm",
            printer_model="P950NW",
        )

        data, address = mock_send.call_args.args
        self.assertIsInstance(data, bytes)
        self.assertEqual(address, "192.0.2.10")

    def test_unsupported_media_and_invalid_margins_are_rejected(self):
        with self.assertRaises(ValueError):
            rasterprynt.render_bytes(
                create_fixture_images(),
                tape_size="99mm",
                printer_model="P950NW",
            )
        with self.assertRaises(ValueError):
            rasterprynt.render_bytes(
                create_fixture_images(),
                top_margin=-1,
                printer_model="P950NW",
            )


if __name__ == "__main__":
    unittest.main()
