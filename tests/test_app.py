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


if __name__ == "__main__":
    unittest.main()
