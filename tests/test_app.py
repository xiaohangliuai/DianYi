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

    def test_dictionary_install_runs_installer(self) -> None:
        fake_result = mock.Mock()
        fake_result.stats.entries = 10
        fake_result.stats.inflections = 5
        fake_result.database_path = "/tmp/dictionary.db"
        output = io.StringIO()
        with mock.patch.object(app, "missing_system_modules", return_value=[]):
            with mock.patch(
                "dianyi.dictionary.install.install_dictionary",
                return_value=fake_result,
            ) as install:
                with contextlib.redirect_stdout(output):
                    result = app.main(["--install-dictionary"])

        self.assertEqual(result, 0)
        self.assertIn("10 dictionary entries", output.getvalue())
        install.assert_called_once_with()

    def test_model_install_runs_installer(self) -> None:
        fake_result = mock.Mock(version="1.9", already_installed=False)
        output = io.StringIO()
        with mock.patch.object(app, "missing_system_modules", return_value=[]):
            with mock.patch(
                "dianyi.model_install.install_translation_model",
                return_value=fake_result,
            ) as install:
                with contextlib.redirect_stdout(output):
                    result = app.main(["--install-model"])

        self.assertEqual(result, 0)
        self.assertIn("Installed Argos en-to-zh model 1.9", output.getvalue())
        install.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
