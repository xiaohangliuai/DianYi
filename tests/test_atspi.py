from __future__ import annotations

import unittest
from dataclasses import dataclass

from dianyi.capture.atspi import selection_from_accessible


@dataclass
class FakeRange:
    start_offset: int
    end_offset: int


class FakeText:
    def __init__(self, text: str, selections: list[FakeRange]) -> None:
        self.text = text
        self.selections = selections

    def get_n_selections(self) -> int:
        return len(self.selections)

    def get_selection(self, index: int) -> FakeRange:
        return self.selections[index]

    def get_text(self, start: int, end: int) -> str:
        return self.text[start:end]


class FakeTextInterface:
    """Model PyGObject's interface-qualified AT-SPI call style."""

    @staticmethod
    def get_n_selections(text: FakeText) -> int:
        return len(text.selections)

    @staticmethod
    def get_selection(text: FakeText, index: int) -> FakeRange:
        return text.selections[index]

    @staticmethod
    def get_text(text: FakeText, start: int, end: int) -> str:
        return text.text[start:end]


class FakeApplication:
    def get_name(self) -> str:
        return "Test Browser"


class FakeAccessible:
    def __init__(self, text: FakeText, role: object = "text") -> None:
        self.text = text
        self.role = role

    def get_text_iface(self) -> FakeText:
        return self.text

    def get_application(self) -> FakeApplication:
        return FakeApplication()

    def get_role(self) -> object:
        return self.role

    def get_role_name(self) -> str:
        return "password text" if self.role == "password" else "text"


class AtspiSelectionTests(unittest.TestCase):
    def test_extracts_the_single_selected_range(self) -> None:
        source = FakeAccessible(FakeText("hello world", [FakeRange(0, 5)]))

        result = selection_from_accessible(source, 4.2)

        self.assertEqual(result.text, "hello")
        self.assertEqual(result.observed_at_s, 4.2)
        self.assertEqual(result.application_name, "Test Browser")

    def test_supports_interface_qualified_text_calls(self) -> None:
        source = FakeAccessible(FakeText("hello world", [FakeRange(6, 11)]))

        result = selection_from_accessible(
            source,
            4.2,
            text_interface=FakeTextInterface,
        )

        self.assertEqual(result.text, "world")

    def test_marks_password_roles(self) -> None:
        source = FakeAccessible(
            FakeText("secret", [FakeRange(0, 6)]),
            role="password",
        )

        result = selection_from_accessible(
            source,
            4.2,
            password_role="password",
        )

        self.assertTrue(result.is_password)

    def test_does_not_merge_multiple_selections(self) -> None:
        source = FakeAccessible(
            FakeText("one two", [FakeRange(0, 3), FakeRange(4, 7)])
        )

        result = selection_from_accessible(source, 4.2)

        self.assertEqual(result.text, "")


if __name__ == "__main__":
    unittest.main()
