"""Convert the pinned ECDICT CSV format into DianYi's local index."""

from __future__ import annotations

import csv
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from dianyi.dictionary.schema import connect_database, initialize_database
from dianyi.selection import ENGLISH_WORD


ECDICT_RELEASE = "1.0.28"
ECDICT_COMMIT = "8defb761f7c7ad1818ca94290a1844d7b33d6b23"
ECDICT_CSV_URL = (
    "https://raw.githubusercontent.com/skywind3000/ECDICT/"
    f"{ECDICT_COMMIT}/ecdict.csv"
)
REQUIRED_COLUMNS = frozenset(
    {"word", "phonetic", "translation", "pos", "bnc", "frq", "exchange"}
)
INFLECTION_PRIORITIES = {
    "0": 0,
    "s": 10,
    "p": 20,
    "d": 20,
    "i": 30,
    "3": 40,
    "r": 50,
    "t": 50,
    "f": 10,
    "b": 50,
    "z": 50,
}
LEGACY_KINDS = {"f": "s", "b": "r", "z": "t"}


@dataclass(frozen=True, slots=True)
class Inflection:
    form: str
    headword: str
    kind: str
    priority: int


@dataclass(frozen=True, slots=True)
class ImportStats:
    entries: int
    inflections: int


def _clean_word(value: str) -> str:
    """Normalize apostrophes and whitespace used in lookup keys."""
    return value.strip().replace("\u2019", "'")


def _frequency_rank(row: dict[str, str]) -> int | None:
    """Choose the best positive rank available in an ECDICT row."""
    ranks: list[int] = []
    for field in ("frq", "bnc"):
        try:
            rank = int(row.get(field, ""))
        except (TypeError, ValueError):
            continue
        if rank > 0:
            ranks.append(rank)
    return min(ranks) if ranks else None


def parse_exchange(word: str, exchange: str) -> tuple[Inflection, ...]:
    """Parse ECDICT exchange codes into reverse lookup relationships."""
    current_word = _clean_word(word)
    inflections: list[Inflection] = []
    for item in exchange.split("/"):
        raw_kind, separator, raw_value = item.partition(":")
        kind = raw_kind.strip()
        value = _clean_word(raw_value)
        if not separator or kind not in INFLECTION_PRIORITIES or not value:
            continue

        normalized_kind = LEGACY_KINDS.get(kind, kind)
        if kind == "0":
            form, headword = current_word, value
        else:
            form, headword = value, current_word
        if (
            form.casefold() == headword.casefold()
            or ENGLISH_WORD.fullmatch(form) is None
            or ENGLISH_WORD.fullmatch(headword) is None
        ):
            continue
        inflections.append(
            Inflection(
                form=form,
                headword=headword,
                kind=normalized_kind,
                priority=INFLECTION_PRIORITIES[kind],
            )
        )
    return tuple(inflections)


def _validate_header(reader: csv.DictReader[str]) -> None:
    """Reject incompatible source files before changing the destination."""
    columns = frozenset(reader.fieldnames or ())
    missing = sorted(REQUIRED_COLUMNS - columns)
    if missing:
        raise ValueError("ECDICT CSV is missing columns: " + ", ".join(missing))


def _import_rows(connection: sqlite3.Connection, source: TextIO) -> ImportStats:
    """Stream ECDICT rows into an initialized SQLite connection."""
    reader = csv.DictReader(source)
    _validate_header(reader)
    connection.execute(
        "CREATE TEMP TABLE exchange_staging "
        "(word TEXT PRIMARY KEY COLLATE NOCASE, exchange TEXT NOT NULL) WITHOUT ROWID"
    )

    with connection:
        for row in reader:
            word = _clean_word(row.get("word", ""))
            translation = (row.get("translation") or "").strip()
            if ENGLISH_WORD.fullmatch(word) is None or not translation:
                continue
            connection.execute(
                """
                INSERT OR IGNORE INTO entries(
                    word, phonetic, translation, parts_of_speech, frequency_rank
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    word,
                    (row.get("phonetic") or "").strip(),
                    translation,
                    (row.get("pos") or "").strip(),
                    _frequency_rank(row),
                ),
            )
            exchange = (row.get("exchange") or "").strip()
            if exchange:
                connection.execute(
                    "INSERT OR IGNORE INTO exchange_staging(word, exchange) "
                    "VALUES (?, ?)",
                    (word, exchange),
                )

        staged = connection.execute(
            "SELECT word, exchange FROM exchange_staging"
        )
        for row in staged:
            for inflection in parse_exchange(row["word"], row["exchange"]):
                connection.execute(
                    """
                    INSERT OR IGNORE INTO inflections(
                        form, headword, kind, priority
                    )
                    SELECT ?, ?, ?, ?
                    WHERE EXISTS (
                        SELECT 1 FROM entries
                        WHERE word = ? COLLATE NOCASE
                    )
                    """,
                    (
                        inflection.form,
                        inflection.headword,
                        inflection.kind,
                        inflection.priority,
                        inflection.headword,
                    ),
                )

        connection.executemany(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
            (
                ("source", "ECDICT"),
                ("source_release", ECDICT_RELEASE),
                ("source_commit", ECDICT_COMMIT),
            ),
        )
        entries = connection.execute("SELECT count(*) FROM entries").fetchone()[0]
        inflections = connection.execute(
            "SELECT count(*) FROM inflections"
        ).fetchone()[0]
    connection.execute("PRAGMA optimize")
    return ImportStats(entries=entries, inflections=inflections)


def import_ecdict_csv(
    csv_path: str | Path,
    database_path: str | Path,
) -> ImportStats:
    """Build a complete dictionary beside its target, then replace atomically."""
    source_path = Path(csv_path).expanduser().resolve()
    target_path = Path(database_path).expanduser().resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = tempfile.NamedTemporaryFile(
        prefix=f".{target_path.name}.",
        suffix=".tmp",
        dir=target_path.parent,
        delete=False,
    )
    temporary_path = Path(temporary_file.name)
    temporary_file.close()
    try:
        with connect_database(temporary_path) as connection:
            initialize_database(connection)
            with source_path.open("r", encoding="utf-8-sig", newline="") as source:
                stats = _import_rows(connection, source)
        os.replace(temporary_path, target_path)
        return stats
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise

