from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from dianyi.dictionary.schema import (
    SCHEMA_VERSION,
    connect_database,
    initialize_database,
)


class DictionarySchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "dictionary.db"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initializes_versioned_tables_and_index(self) -> None:
        with connect_database(self.database_path) as connection:
            initialize_database(connection)
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            indexes = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index'"
                )
            }
            version = connection.execute("PRAGMA user_version").fetchone()[0]

        self.assertEqual(tables, {"entries", "inflections"})
        self.assertIn("inflections_by_form", indexes)
        self.assertEqual(version, SCHEMA_VERSION)

    def test_initialization_is_idempotent(self) -> None:
        with connect_database(self.database_path) as connection:
            initialize_database(connection)
            initialize_database(connection)

    def test_rejects_unknown_newer_schema(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA user_version = 99")
            with self.assertRaisesRegex(RuntimeError, "unsupported"):
                initialize_database(connection)

    def test_enforces_inflection_foreign_keys(self) -> None:
        with connect_database(self.database_path) as connection:
            initialize_database(connection)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO inflections(form, headword, kind) "
                    "VALUES (?, ?, ?)",
                    ("running", "run", "i"),
                )

    def test_readonly_connection_cannot_modify_database(self) -> None:
        with connect_database(self.database_path) as connection:
            initialize_database(connection)

        with connect_database(self.database_path, readonly=True) as connection:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute(
                    "INSERT INTO entries(word) VALUES (?)",
                    ("test",),
                )


if __name__ == "__main__":
    unittest.main()
