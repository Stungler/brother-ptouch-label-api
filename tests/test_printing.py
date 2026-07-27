import unittest
from unittest.mock import patch

from PIL import Image

from core.printing import (
    PTP950NW,
    get_supported_tape_sizes,
    print_labels_to_ip,
)


class PrintingTest(unittest.TestCase):
    def test_supported_tape_sizes_come_from_configuration(self):
        self.assertEqual(
            get_supported_tape_sizes(),
            list(PTP950NW.supported_tape_sizes_mm),
        )

    @patch("core.printing.rasterprynt.prynt")
    def test_print_normalizes_image_and_forwards_tape_width(self, mock_prynt):
        image = Image.new("RGB", (40, 20), "white")

        print_labels_to_ip(
            labels=[image],
            printer_ip="192.0.2.10",
            tape_mm=18,
        )

        args, kwargs = mock_prynt.call_args
        self.assertEqual(args[1], "192.0.2.10")
        self.assertEqual(args[0][0].height, PTP950NW.stripe_height(18))
        self.assertEqual(kwargs["tape_size"], "18mm")
        self.assertEqual(kwargs["printer_model"], "P950NW")

    @patch("core.printing.rasterprynt.prynt")
    def test_legacy_keyword_names_remain_supported(self, mock_prynt):
        image = Image.new("RGB", (20, 20), "white")

        print_labels_to_ip(
            [image],
            "192.0.2.10",
            tape_mm=6,
            v_align="center",
            pad_lr_px=(0, 0),
        )

        mock_prynt.assert_called_once()


if __name__ == "__main__":
    unittest.main()
