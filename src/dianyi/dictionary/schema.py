"""SQLite schema for the compact local ECDICT index."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_VERSION = 1

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS entries (
    word TEXT PRIMARY KEY COLLATE NOCASE,
    phonetic TEXT NOT NULL DEFAULT '',
    translation TEXT NOT NULL DEFAULT '',
    parts_of_speech TEXT NOT NULL DEFAULT '',
    frequency_rank INTEGER
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS inflections (
    form TEXT COLLATE NOCASE NOT NULL,
    headword TEXT COLLATE NOCASE NOT NULL,
    kind TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    PRIMARY KEY (form, headword, kind),
    FOREIGN KEY (headword) REFERENCES entries(word) ON DELETE CASCADE
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS inflections_by_form
ON inflections(form COLLATE NOCASE, priority, headword);

PRAGMA user_version = 1;
"""


def connect_database(
    path: str | Path,
    *,
    readonly: bool = False,
) -> sqlite3.Connection:
    """Open a dictionary database with safe, deterministic connection options."""
    database_path = Path(path).expanduser().resolve()
    if readonly:
        connection = sqlite3.connect(
            f"{database_path.as_uri()}?mode=ro",
            uri=True,
            timeout=1.0,
        )
    else:
        connection = sqlite3.connect(database_path, timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create or validate the current dictionary schema."""
    current_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if current_version not in (0, SCHEMA_VERSION):
        raise RuntimeError(
            f"unsupported dictionary schema version: {current_version}"
        )
    connection.executescript(SCHEMA_SQL)

