from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dianyi.dictionary.lookup import (
    DictionaryUnavailableError,
    default_database_path,
    lookup_word,
)
from dianyi.dictionary.schema import connect_database, initialize_database


class DictionaryLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "dictionary.db"
        with connect_database(self.database_path) as connection:
            initialize_database(connection)
            connection.executemany(
                """
                INSERT INTO entries(
                    word, phonetic, translation, parts_of_speech, frequency_rank
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    ("run", "r\u028cn", "vi. \u8dd1\nvt. \u7ba1\u7406", "v:90/n:10", 500),
                    ("running", "", "n. \u8dd1\u6b65", "n:100", 1_500),
                    ("child", "t\u0283a\u026ald", "n. \u5b69\u5b50", "n", 200),
                    ("saw", "s\u0254\u02d0", "n. \u952f", "n", 2_000),
                    ("see", "si\u02d0", "vt. \u770b\u89c1", "v", 100),
                ],
            )
            connection.executemany(
                """
                INSERT INTO inflections(form, headword, kind, priority)
                VALUES (?, ?, ?, ?)
                """,
                [
                    ("running", "run", "i", 20),
                    ("children", "child", "s", 10),
                    ("saw", "see", "p", 10),
                ],
            )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_exact_match_wins_over_inflection(self) -> None:
        result = lookup_word("Running", database_path=self.database_path)

        assert result is not None
        self.assertEqual(result.headword, "running")
        self.assertFalse(result.normalized)
        self.assertEqual(result.meanings, ("n. \u8dd1\u6b65",))

    def test_resolves_irregular_plural_through_reverse_index(self) -> None:
        result = lookup_word("children", database_path=self.database_path)

        assert result is not None
        self.assertEqual(result.headword, "child")
        self.assertTrue(result.normalized)
        self.assertEqual(result.phonetic, "t\u0283a\u026ald")

    def test_parses_parts_of_speech_and_multiline_meanings(self) -> None:
        result = lookup_word("run", database_path=self.database_path)

        assert result is not None
        self.assertEqual(result.parts_of_speech, ("v", "n"))
        self.assertEqual(result.meanings, ("vi. \u8dd1", "vt. \u7ba1\u7406"))

    def test_exact_homograph_wins_over_irregular_form(self) -> None:
        result = lookup_word("saw", database_path=self.database_path)

        assert result is not None
        self.assertEqual(result.headword, "saw")

    def test_normalizes_curly_apostrophe_for_lookup(self) -> None:
        with connect_database(self.database_path) as connection:
            connection.execute(
                "INSERT INTO entries(word, translation) VALUES (?, ?)",
                ("don't", "\u4e0d\u8981"),
            )

        result = lookup_word("don\u2019t", database_path=self.database_path)

        assert result is not None
        self.assertEqual(result.headword, "don't")

    def test_returns_none_for_unknown_or_empty_text(self) -> None:
        self.assertIsNone(lookup_word("unknown", database_path=self.database_path))
        self.assertIsNone(lookup_word("  ", database_path=self.database_path))

    def test_reports_missing_database_clearly(self) -> None:
        missing = Path(self.temporary_directory.name) / "missing.db"

        with self.assertRaisesRegex(DictionaryUnavailableError, str(missing)):
            lookup_word("word", database_path=missing)

    def test_default_path_honors_xdg_data_home(self) -> None:
        with mock.patch.dict(os.environ, {"XDG_DATA_HOME": "/tmp/data"}):
            self.assertEqual(
                default_database_path(),
                Path("/tmp/data/dianyi/dictionary.sqlite3"),
            )


if __name__ == "__main__":
    unittest.main()
