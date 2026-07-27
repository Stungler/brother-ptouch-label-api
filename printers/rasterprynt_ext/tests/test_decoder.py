import unittest

from PIL import Image
from rasterprynt.decoder import (
    decode_rows,
    decompress_packbits,
    detect_capture_format,
    rows_to_pbm,
)
from rasterprynt.protocol import render_bytes


class DecoderTest(unittest.TestCase):
    def test_packbits_example_from_brother_documentation(self):
        compressed = b"\xed\x00\xff\x22\x05\x23\xba\xbf\xa2\x22\x2b"
        expected = (
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x22\x22\x23\xba\xbf\xa2\x22\x2b"
        )
        self.assertEqual(b"".join(decompress_packbits(compressed)), expected)

    def test_decoder_reads_encoder_output(self):
        image = Image.new("RGB", (4, 3), "white")
        image.putpixel((0, 0), (0, 0, 0))
        commands = render_bytes(
            [image],
            top_margin=1,
            bottom_margin=1,
            tape_size="18mm",
            printer_model="P950NW",
        )

        rows = decode_rows(commands)
        pbm = rows_to_pbm(rows)

        self.assertEqual(len(rows), 6)
        self.assertEqual(len(rows[0]), 408)
        self.assertTrue(pbm.startswith(b"P1\n408 6\n"))

    def test_truncated_packbits_input_is_rejected(self):
        with self.assertRaises(ValueError):
            b"".join(decompress_packbits(b"\x02\x01"))
        with self.assertRaises(ValueError):
            b"".join(decompress_packbits(b"\xff"))

    def test_capture_format_detection(self):
        self.assertEqual(detect_capture_format(b"\xa1\xb2\xc3\xd4data"), "pcap")
        self.assertEqual(detect_capture_format(b"\x00\x00commands"), "bin")


if __name__ == "__main__":
    unittest.main()
