from __future__ import annotations

import unittest

from Xlib import X

from dianyi.capture.shortcut import parse_shortcut


class ShortcutParsingTests(unittest.TestCase):
    def test_parses_default_shortcut(self) -> None:
        result = parse_shortcut("Super+T")

        self.assertEqual(result.label, "Super+T")
        self.assertEqual(result.key_name, "t")
        self.assertEqual(result.modifiers, X.Mod4Mask)

    def test_parses_multiple_modifiers_case_insensitively(self) -> None:
        result = parse_shortcut("ctrl+SHIFT+x")

        self.assertEqual(result.key_name, "x")
        self.assertEqual(result.modifiers, X.ControlMask | X.ShiftMask)

    def test_rejects_missing_modifier(self) -> None:
        with self.assertRaisesRegex(ValueError, "modifier"):
            parse_shortcut("T")

    def test_rejects_unsupported_modifier(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported"):
            parse_shortcut("Hyper+T")

    def test_rejects_non_ascii_or_multi_character_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "ASCII"):
            parse_shortcut("Super+Enter")
        with self.assertRaisesRegex(ValueError, "ASCII"):
            parse_shortcut("Super+\u8bd1")

    def test_rejects_duplicate_modifier(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_shortcut("Super+Super+T")


if __name__ == "__main__":
    unittest.main()
