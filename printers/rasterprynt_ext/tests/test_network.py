import unittest
from unittest.mock import patch
from urllib.error import URLError

from rasterprynt import network


class NetworkTest(unittest.TestCase):
    def setUp(self):
        network.clear_model_cache()
        self.addCleanup(network.clear_model_cache)

    @patch("rasterprynt.network.time.monotonic", side_effect=(1000.0, 1001.0))
    @patch("rasterprynt.network._detect_printer_model_uncached")
    def test_detect_printer_model_uses_unexpired_cache(
        self,
        mock_detect,
        _mock_time,
    ):
        mock_detect.return_value = "P950NW"

        first = network.detect_printer_model("192.0.2.10")
        second = network.detect_printer_model("192.0.2.10")

        self.assertEqual(first, "P950NW")
        self.assertEqual(second, "P950NW")
        mock_detect.assert_called_once()

    @patch(
        "rasterprynt.network._detect_printer_model_uncached",
        side_effect=URLError("unreachable"),
    )
    def test_detection_failure_returns_none(self, _mock_detect):
        with self.assertLogs("rasterprynt.network", level="WARNING"):
            self.assertIsNone(network.detect_printer_model("192.0.2.10"))


if __name__ == "__main__":
    unittest.main()
