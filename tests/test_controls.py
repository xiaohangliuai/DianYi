from __future__ import annotations

import unittest

from dianyi.controls import preferences_from_controls


class PreferencesControlTests(unittest.TestCase):
    def test_builds_validated_preferences_from_dialog_values(self) -> None:
        result = preferences_from_controls(
            "ctrl+shift+x",
            False,
            " Firefox \nfirefox\nKeePassXC\n",
            True,
        )

        self.assertEqual(result.shortcut, "Ctrl+Shift+X")
        self.assertFalse(result.automatic_word_lookup)
        self.assertEqual(result.blocked_applications, ("Firefox", "KeePassXC"))
        self.assertTrue(result.paused)

    def test_rejects_invalid_shortcut(self) -> None:
        with self.assertRaises(Exception):
            preferences_from_controls("T", True, "", False)


if __name__ == "__main__":
    unittest.main()
