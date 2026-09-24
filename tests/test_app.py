from __future__ import annotations

import contextlib
import io
import unittest
from unittest import mock

from dianyi import app


class AppTests(unittest.TestCase):
    def test_check_reports_success(self) -> None:
        output = io.StringIO()
        with mock.patch.object(app, "missing_system_modules", return_value=[]):
            with contextlib.redirect_stdout(output):
                result = app.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("available", output.getvalue())

    def test_check_reports_missing_modules(self) -> None:
        output = io.StringIO()
        with mock.patch.object(app, "missing_system_modules", return_value=["gi"]):
            with contextlib.redirect_stdout(output):
                result = app.main(["--check"])

        self.assertEqual(result, 1)
        self.assertIn("gi", output.getvalue())

    def test_capture_starts_service(self) -> None:
        with mock.patch.object(app, "missing_system_modules", return_value=[]):
            with mock.patch(
                "dianyi.service.run_capture_service",
                return_value=7,
            ) as run_capture:
                result = app.main(["--capture"])

        self.assertEqual(result, 7)
        run_capture.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
