from __future__ import annotations

import unittest

from dianyi.selection import (
    RejectionReason,
    SelectionContext,
    ValidationResult,
    validate_automatic_word,
    validate_sentence,
)


class SelectionValidationTests(unittest.TestCase):
    def validate(self, text: str, **kwargs: object) -> ValidationResult:
        return validate_automatic_word(
            SelectionContext(text=text, observed_at_s=1.0, **kwargs)
        )

    def test_accepts_a_plain_english_word(self) -> None:
        result = self.validate("running")

        self.assertTrue(result.accepted)
        assert result.word is not None
        self.assertEqual(result.word.text, "running")

    def test_trims_surrounding_punctuation(self) -> None:
        result = self.validate("\u201cHello!\u201d")

        assert result.word is not None
        self.assertEqual(result.word.text, "Hello")

    def test_accepts_hyphens_and_contractions(self) -> None:
        self.assertTrue(self.validate("state-of-the-art").accepted)
        self.assertTrue(self.validate("don't").accepted)
        self.assertTrue(self.validate("isn\u2019t").accepted)

    def test_rejects_empty_text(self) -> None:
        result = self.validate(" \n")

        self.assertEqual(result.rejection, RejectionReason.EMPTY)

    def test_rejects_a_phrase(self) -> None:
        result = self.validate("two words")

        self.assertEqual(result.rejection, RejectionReason.MULTIWORD)

    def test_rejects_non_english_text(self) -> None:
        self.assertEqual(
            self.validate("\u4f60\u597d").rejection,
            RejectionReason.NON_ENGLISH,
        )
        self.assertEqual(
            self.validate("caf\u00e9").rejection,
            RejectionReason.NON_ENGLISH,
        )

    def test_rejects_password_fields(self) -> None:
        result = self.validate("secret", is_password=True)

        self.assertEqual(result.rejection, RejectionReason.PASSWORD)

    def test_matches_blocked_application_name_case_insensitively(self) -> None:
        context = SelectionContext(
            text="word",
            observed_at_s=1.0,
            application_name="KeePassXC",
        )

        result = validate_automatic_word(context, frozenset({"keepassxc"}))

        self.assertEqual(result.rejection, RejectionReason.BLOCKED_APPLICATION)

    def test_matches_blocked_wm_class(self) -> None:
        context = SelectionContext(
            text="word",
            observed_at_s=1.0,
            wm_class="PrivateReader",
        )

        result = validate_automatic_word(context, frozenset({"privatereader"}))

        self.assertEqual(result.rejection, RejectionReason.BLOCKED_APPLICATION)

    def test_result_requires_one_outcome(self) -> None:
        with self.assertRaises(ValueError):
            ValidationResult()


class SentenceValidationTests(unittest.TestCase):
    def validate(self, text: str, **kwargs: object):
        return validate_sentence(
            SelectionContext(text=text, observed_at_s=1.0, **kwargs)
        )

    def test_accepts_english_sentence_with_typographic_punctuation(self) -> None:
        result = self.validate("\u201cThis is a sentence\u2014really!\u201d")

        self.assertTrue(result.accepted)
        assert result.sentence is not None
        self.assertEqual(result.sentence.text, "\u201cThis is a sentence\u2014really!\u201d")

    def test_accepts_single_word_for_explicit_translation(self) -> None:
        self.assertTrue(self.validate("hello").accepted)

    def test_rejects_empty_numeric_and_non_english_text(self) -> None:
        self.assertEqual(self.validate(" ").rejection, RejectionReason.EMPTY)
        self.assertEqual(self.validate("123").rejection, RejectionReason.NON_ENGLISH)
        self.assertEqual(self.validate("hello \u4e16\u754c").rejection, RejectionReason.NON_ENGLISH)

    def test_rejects_password_and_blocked_application(self) -> None:
        self.assertEqual(
            self.validate("secret", is_password=True).rejection,
            RejectionReason.PASSWORD,
        )
        context = SelectionContext(
            "sentence",
            observed_at_s=1.0,
            application_name="Blocked",
        )
        self.assertEqual(
            validate_sentence(context, frozenset({"blocked"})).rejection,
            RejectionReason.BLOCKED_APPLICATION,
        )

    def test_rejects_excessively_long_selection(self) -> None:
        result = validate_sentence(
            SelectionContext("a" * 11, observed_at_s=1.0),
            maximum_characters=10,
        )

        self.assertEqual(result.rejection, RejectionReason.TOO_LONG)


if __name__ == "__main__":
    unittest.main()
