from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from dianyi.dictionary.importer import (
    ECDICT_COMMIT,
    import_ecdict_csv,
    parse_exchange,
)
from dianyi.dictionary.lookup import lookup_word
from dianyi.dictionary.schema import connect_database


FIELDS = [
    "word",
    "phonetic",
    "definition",
    "translation",
    "pos",
    "collins",
    "oxford",
    "tag",
    "bnc",
    "frq",
    "exchange",
    "detail",
    "audio",
]


class DictionaryImporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.csv_path = root / "ecdict.csv"
        self.database_path = root / "dictionary.sqlite3"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_rows(self, rows: list[dict[str, str]]) -> None:
        with self.csv_path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def row(self, word: str, translation: str, **values: str) -> dict[str, str]:
        row = dict.fromkeys(FIELDS, "")
        row.update(word=word, translation=translation, **values)
        return row

    def test_imports_entries_and_reverse_inflections(self) -> None:
        self.write_rows(
            [
                self.row(
                    "run",
                    "vi. \u8dd1\nvt. \u7ecf\u8425, \u7ba1\u7406",
                    phonetic="r\u028cn",
                    pos="v:90/n:10",
                    frq="500",
                    exchange="p:ran/d:run/i:running/3:runs",
                ),
                self.row(
                    "child",
                    "n. \u5b69\u5b50",
                    exchange="s:children",
                ),
            ]
        )

        stats = import_ecdict_csv(self.csv_path, self.database_path)

        self.assertEqual(stats.entries, 2)
        self.assertEqual(stats.inflections, 4)
        running = lookup_word("running", database_path=self.database_path)
        children = lookup_word("children", database_path=self.database_path)
        assert running is not None and children is not None
        self.assertEqual(running.headword, "run")
        self.assertEqual(children.headword, "child")
        self.assertIn("\u7ecf\u8425, \u7ba1\u7406", running.meanings[1])

    def test_imports_zero_tag_as_lemma_relationship(self) -> None:
        self.write_rows(
            [
                self.row("perceive", "vt. \u5bdf\u89c9"),
                self.row("perceived", "adj. \u611f\u77e5\u5230\u7684", exchange="0:perceive/1:p"),
            ]
        )

        import_ecdict_csv(self.csv_path, self.database_path)

        with connect_database(self.database_path, readonly=True) as connection:
            relation = connection.execute(
                "SELECT headword FROM inflections WHERE form = 'perceived'"
            ).fetchone()
        assert relation is not None
        self.assertEqual(relation["headword"], "perceive")

    def test_filters_phrases_non_english_and_entries_without_chinese(self) -> None:
        self.write_rows(
            [
                self.row("valid", "adj. \u6709\u6548\u7684"),
                self.row("two words", "\u4e24\u4e2a\u8bcd"),
                self.row("caf\u00e9", "\u5496\u5561\u9986"),
                self.row("empty", ""),
            ]
        )

        stats = import_ecdict_csv(self.csv_path, self.database_path)

        self.assertEqual(stats.entries, 1)

    def test_records_pinned_source_metadata(self) -> None:
        self.write_rows([self.row("word", "n. \u5355\u8bcd")])

        import_ecdict_csv(self.csv_path, self.database_path)

        with connect_database(self.database_path, readonly=True) as connection:
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        self.assertEqual(metadata["source_commit"], ECDICT_COMMIT)

    def test_invalid_csv_does_not_replace_existing_database(self) -> None:
        self.database_path.write_bytes(b"existing")
        self.csv_path.write_text("word,translation\ntest,\u6d4b\u8bd5\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "missing columns"):
            import_ecdict_csv(self.csv_path, self.database_path)

        self.assertEqual(self.database_path.read_bytes(), b"existing")

    def test_parse_exchange_normalizes_legacy_codes_and_ignores_bad_items(self) -> None:
        result = parse_exchange(
            "bright",
            "b:brighter/z:brightest/bad/f:/r:bright",
        )

        self.assertEqual(
            [(item.form, item.kind) for item in result],
            [("brighter", "r"), ("brightest", "t")],
        )


if __name__ == "__main__":
    unittest.main()
