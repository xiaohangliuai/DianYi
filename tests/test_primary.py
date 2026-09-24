from __future__ import annotations

import unittest

from dianyi.capture.primary import PrimarySelectionReader


class FakeClipboard:
    def __init__(self, text: str | None) -> None:
        self.text = text
        self.requests = 0

    def request_text(self, callback: object, user_data: object) -> None:
        self.requests += 1
        callback(self, self.text, user_data)  # type: ignore[operator]


class PrimarySelectionReaderTests(unittest.TestCase):
    def test_returns_current_primary_text_asynchronously(self) -> None:
        clipboard = FakeClipboard("selected sentence")
        results: list[str] = []

        PrimarySelectionReader(clipboard).read(results.append)

        self.assertEqual(clipboard.requests, 1)
        self.assertEqual(results, ["selected sentence"])

    def test_normalizes_missing_primary_selection_to_empty_text(self) -> None:
        results: list[str] = []

        PrimarySelectionReader(FakeClipboard(None)).read(results.append)

        self.assertEqual(results, [""])


if __name__ == "__main__":
    unittest.main()
