from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dianyi.preferences import (
    Preferences,
    PreferencesError,
    PreferencesStore,
    default_preferences_path,
    preferences_from_mapping,
)


class PreferencesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "config/settings.json"
        self.store = PreferencesStore(self.path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_returns_safe_defaults_when_file_is_absent(self) -> None:
        self.assertEqual(self.store.load(), Preferences())

    def test_round_trips_valid_preferences_atomically(self) -> None:
        expected = Preferences(
            shortcut="Ctrl+Shift+X",
            automatic_word_lookup=False,
            blocked_applications=("KeePassXC", "PrivateReader"),
            paused=True,
        )

        self.store.save(expected)

        self.assertEqual(self.store.load(), expected)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_normalizes_and_deduplicates_blocklist(self) -> None:
        result = preferences_from_mapping(
            {"blocked_applications": [" Firefox ", "firefox", "", "Secret"]}
        )

        self.assertEqual(result.blocked_applications, ("Firefox", "Secret"))

    def test_rejects_invalid_shortcut_and_types(self) -> None:
        with self.assertRaises(PreferencesError):
            preferences_from_mapping({"shortcut": "T"})
        with self.assertRaises(PreferencesError):
            preferences_from_mapping({"automatic_word_lookup": "yes"})
        with self.assertRaises(PreferencesError):
            preferences_from_mapping({"blocked_applications": "Firefox"})

    def test_rejects_malformed_file_instead_of_silently_overwriting_it(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{bad json", encoding="utf-8")

        with self.assertRaisesRegex(PreferencesError, "cannot read"):
            self.store.load()

        self.assertEqual(self.path.read_text(encoding="utf-8"), "{bad json")

    def test_saved_file_contains_no_selection_or_history_fields(self) -> None:
        self.store.save(Preferences())

        values = json.loads(self.path.read_text(encoding="utf-8"))

        self.assertEqual(
            set(values),
            {
                "shortcut",
                "automatic_word_lookup",
                "blocked_applications",
                "paused",
            },
        )

    def test_default_path_honors_xdg_config_home(self) -> None:
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/config"}):
            self.assertEqual(
                default_preferences_path(),
                Path("/tmp/config/dianyi/settings.json"),
            )


if __name__ == "__main__":
    unittest.main()
