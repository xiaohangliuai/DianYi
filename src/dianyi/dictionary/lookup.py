"""Fast exact and inflection-aware lookup against the local dictionary."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from dianyi.dictionary.schema import connect_database


@dataclass(frozen=True, slots=True)
class DictionaryEntry:
    """Dictionary content ready for presentation."""

    selected_text: str
    headword: str
    phonetic: str
    parts_of_speech: tuple[str, ...]
    meanings: tuple[str, ...]

    @property
    def normalized(self) -> bool:
        """Return whether lookup resolved the selection to another headword."""
        return self.selected_text.casefold() != self.headword.casefold()


class DictionaryUnavailableError(RuntimeError):
    """Raised when the installed dictionary database cannot be opened."""


def default_database_path() -> Path:
    """Return the XDG-compliant location of the installed dictionary."""
    data_home = os.environ.get("XDG_DATA_HOME")
    root = Path(data_home).expanduser() if data_home else Path.home() / ".local/share"
    return root / "dianyi" / "dictionary.sqlite3"


def _parse_parts_of_speech(value: str) -> tuple[str, ...]:
    """Convert ECDICT's slash-separated weighted POS field into labels."""
    labels: list[str] = []
    for item in value.split("/"):
        label = item.partition(":")[0].strip()
        if label and label not in labels:
            labels.append(label)
    return tuple(labels)


def _parse_meanings(value: str) -> tuple[str, ...]:
    """Return non-empty Chinese meaning lines without changing their content."""
    return tuple(line.strip() for line in value.splitlines() if line.strip())


def _entry_from_row(selected_text: str, row: sqlite3.Row) -> DictionaryEntry:
    """Build a presentation model from one SQLite result row."""
    return DictionaryEntry(
        selected_text=selected_text,
        headword=row["word"],
        phonetic=row["phonetic"],
        parts_of_speech=_parse_parts_of_speech(row["parts_of_speech"]),
        meanings=_parse_meanings(row["translation"]),
    )


def _lookup_connection(
    connection: sqlite3.Connection,
    text: str,
) -> DictionaryEntry | None:
    """Look up one word using an existing read-only or test connection."""
    selected_text = text.strip().replace("\u2019", "'")
    if not selected_text:
        return None

    exact = connection.execute(
        """
        SELECT word, phonetic, translation, parts_of_speech
        FROM entries
        WHERE word = ? COLLATE NOCASE
        LIMIT 1
        """,
        (selected_text,),
    ).fetchone()
    if exact is not None:
        return _entry_from_row(selected_text, exact)

    inflected = connection.execute(
        """
        SELECT entry.word, entry.phonetic, entry.translation,
               entry.parts_of_speech
        FROM inflections AS inflection
        JOIN entries AS entry ON entry.word = inflection.headword
        WHERE inflection.form = ? COLLATE NOCASE
        ORDER BY inflection.priority,
                 COALESCE(entry.frequency_rank, 2147483647),
                 length(entry.word),
                 entry.word COLLATE NOCASE
        LIMIT 1
        """,
        (selected_text,),
    ).fetchone()
    if inflected is None:
        return None
    return _entry_from_row(selected_text, inflected)


def lookup_word(
    text: str,
    *,
    database_path: str | Path | None = None,
) -> DictionaryEntry | None:
    """Look up a word in the installed offline dictionary."""
    path = Path(database_path) if database_path is not None else default_database_path()
    try:
        with connect_database(path, readonly=True) as connection:
            return _lookup_connection(connection, text)
    except sqlite3.OperationalError as error:
        raise DictionaryUnavailableError(
            f"dictionary is unavailable at {path}"
        ) from error

