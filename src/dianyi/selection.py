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
