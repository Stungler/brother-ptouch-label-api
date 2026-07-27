import unittest
from unittest.mock import patch

from api.routes import print_endpoint
from api.schemas import PrinterRebootRequest, PrintRequest
from core.label_generator import LabelType


class RouteTest(unittest.TestCase):
    @patch("api.routes.print_labels")
    @patch("api.routes.generate_label")
    def test_legacy_print_forwards_requested_tape_width(
        self,
        mock_generate_label,
        mock_print_labels,
    ):
        mock_generate_label.return_value = ["rendered-label"]
        request = PrintRequest(
            text="TEST-6MM",
            label_type=LabelType.TEXT,
            tape_size=6,
            copies=1,
        )

        response = print_endpoint(request)

        mock_print_labels.assert_called_once_with(
            ["rendered-label"],
            tape_mm=6,
        )
        self.assertEqual(response["tape_size"], 6)

    def test_reboot_community_defaults_to_environment_configuration(self):
        request = PrinterRebootRequest()
        self.assertIsNone(request.community)


if __name__ == "__main__":
    unittest.main()
