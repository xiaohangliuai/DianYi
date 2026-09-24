from __future__ import annotations

import unittest

from dianyi.desktop_settings import DesktopInputSettings, read_input_settings


class FakeSettings:
    def __init__(self, values: dict[str, int]) -> None:
        self.values = values

    def get_int(self, key: str) -> int:
        return self.values[key]


class DesktopSettingsTests(unittest.TestCase):
    def test_reads_gnome_mouse_thresholds(self) -> None:
        settings = FakeSettings({"double-click": 400, "drag-threshold": 8})

        result = read_input_settings(settings)

        self.assertEqual(result, DesktopInputSettings(400, 8))

    def test_rejects_invalid_double_click_time(self) -> None:
        settings = FakeSettings({"double-click": 0, "drag-threshold": 8})

        with self.assertRaisesRegex(ValueError, "double-click"):
            read_input_settings(settings)

    def test_rejects_invalid_drag_threshold(self) -> None:
        settings = FakeSettings({"double-click": 400, "drag-threshold": -1})

        with self.assertRaisesRegex(ValueError, "drag threshold"):
            read_input_settings(settings)


if __name__ == "__main__":
    unittest.main()
