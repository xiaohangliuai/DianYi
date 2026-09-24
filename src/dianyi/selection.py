"""Selection metadata and validation for automatic word lookup."""

from __future__ import annotations

import re
import string
from dataclasses import dataclass
from enum import Enum


ENGLISH_WORD = re.compile(r"^[A-Za-z]+(?:['\u2019-][A-Za-z]+)*$")
BOUNDARY_PUNCTUATION = string.punctuation.replace("'", "").replace("-", "") + "\u2018\u2019\u201c\u201d"


class RejectionReason(Enum):
    """Why a captured selection is unsafe for automatic word lookup."""

    EMPTY = "empty selection"
    PASSWORD = "password field"
    BLOCKED_APPLICATION = "blocked application"
    MULTIWORD = "multiple words"
    NON_ENGLISH = "not a single English word"
    TOO_LONG = "selection is too long"


@dataclass(frozen=True, slots=True)
class SelectionContext:
    """Selected text plus the source metadata needed for safe validation."""

    text: str
    observed_at_s: float
    application_name: str = ""
    wm_class: str = ""
    is_password: bool = False


@dataclass(frozen=True, slots=True)
class ValidatedWord:
    """A selection approved for automatic dictionary lookup."""

    text: str
    source: SelectionContext


@dataclass(frozen=True, slots=True)
class ValidatedSentence:
    """A selection approved for explicit sentence translation."""

    text: str
    source: SelectionContext


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Either an approved word or a documented rejection reason."""

    word: ValidatedWord | None = None
    rejection: RejectionReason | None = None

    def __post_init__(self) -> None:
        if (self.word is None) == (self.rejection is None):
            raise ValueError("exactly one of word or rejection must be set")

    @property
    def accepted(self) -> bool:
        """Return whether the selection passed validation."""
        return self.word is not None


@dataclass(frozen=True, slots=True)
class SentenceValidationResult:
    """Either an approved sentence or a documented rejection reason."""

    sentence: ValidatedSentence | None = None
    rejection: RejectionReason | None = None

    def __post_init__(self) -> None:
        if (self.sentence is None) == (self.rejection is None):
            raise ValueError("exactly one of sentence or rejection must be set")

    @property
    def accepted(self) -> bool:
        """Return whether the selection passed sentence validation."""
        return self.sentence is not None


def _is_blocked(context: SelectionContext, blocklist: frozenset[str]) -> bool:
    """Match source identifiers against a case-insensitive application blocklist."""
    blocked = {entry.casefold() for entry in blocklist}
    candidates = (context.application_name.casefold(), context.wm_class.casefold())
    return any(candidate and candidate in blocked for candidate in candidates)


def validate_automatic_word(
    context: SelectionContext,
    blocklist: frozenset[str] = frozenset(),
) -> ValidationResult:
    """Validate a fresh selection for automatic single-word lookup."""
    raw_text = context.text.strip()
    if not raw_text:
        return ValidationResult(rejection=RejectionReason.EMPTY)
    if context.is_password:
        return ValidationResult(rejection=RejectionReason.PASSWORD)
    if _is_blocked(context, blocklist):
        return ValidationResult(rejection=RejectionReason.BLOCKED_APPLICATION)

    word = raw_text.strip(BOUNDARY_PUNCTUATION)
    if not word:
        return ValidationResult(rejection=RejectionReason.EMPTY)
    if any(character.isspace() for character in word):
        return ValidationResult(rejection=RejectionReason.MULTIWORD)
    if ENGLISH_WORD.fullmatch(word) is None:
        return ValidationResult(rejection=RejectionReason.NON_ENGLISH)
    return ValidationResult(word=ValidatedWord(text=word, source=context))


def validate_sentence(
    context: SelectionContext,
    blocklist: frozenset[str] = frozenset(),
    *,
    maximum_characters: int = 5_000,
) -> SentenceValidationResult:
    """Validate text selected for an explicit sentence-translation request."""
    text = context.text.strip()
    if not text:
        return SentenceValidationResult(rejection=RejectionReason.EMPTY)
    if context.is_password:
        return SentenceValidationResult(rejection=RejectionReason.PASSWORD)
    if _is_blocked(context, blocklist):
        return SentenceValidationResult(
            rejection=RejectionReason.BLOCKED_APPLICATION
        )
    if len(text) > maximum_characters:
        return SentenceValidationResult(rejection=RejectionReason.TOO_LONG)

    letters = [character for character in text if character.isalpha()]
    if not letters or any(not character.isascii() for character in letters):
        return SentenceValidationResult(rejection=RejectionReason.NON_ENGLISH)
    return SentenceValidationResult(
        sentence=ValidatedSentence(text=text, source=context)
    )

