"""Local dictionary storage and lookup."""

from dianyi.dictionary.lookup import DictionaryEntry, lookup_word
from dianyi.dictionary.schema import connect_database, initialize_database

__all__ = [
    "DictionaryEntry",
    "connect_database",
    "initialize_database",
    "lookup_word",
]
