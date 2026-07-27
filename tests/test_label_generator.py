import unittest

from core.label_generator import LabelType, generate_label
from core.printing import get_supported_tape_sizes


class LabelGeneratorTest(unittest.TestCase):
    def test_all_configured_tape_widths_render(self):
        for tape_width_mm in get_supported_tape_sizes():
            with self.subTest(tape_width_mm=tape_width_mm):
                labels = generate_label(
                    text=f"TEST-{tape_width_mm:02d}MM",
                    label_type=LabelType.TEXT_QR,
                    tape_size=tape_width_mm,
                )

                self.assertEqual(len(labels), 1)
                self.assertEqual(labels[0].mode, "RGB")
                self.assertGreater(labels[0].width, 0)
                self.assertGreater(labels[0].height, 0)

    def test_each_layout_renders(self):
        for label_type in LabelType:
            with self.subTest(label_type=label_type):
                label = generate_label(
                    text="ASSET-0001",
                    label_type=label_type,
                    tape_size=18,
                )[0]
                self.assertGreater(label.width, 0)

    def test_copies_are_independent_images(self):
        labels = generate_label(
            text="COPY-TEST",
            label_type=LabelType.TEXT,
            tape_size=9,
            copies=2,
        )

        self.assertEqual(len(labels), 2)
        self.assertIsNot(labels[0], labels[1])

    def test_invalid_empty_text_and_copy_count_are_rejected(self):
        with self.assertRaises(ValueError):
            generate_label("", LabelType.TEXT, 18)
        with self.assertRaises(ValueError):
            generate_label("TEST", LabelType.TEXT, 18, copies=0)


if __name__ == "__main__":
    unittest.main()
