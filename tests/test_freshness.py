from __future__ import annotations

import unittest

from dianyi.capture.freshness import FreshSelectionBuffer
from dianyi.capture.gesture import DoubleClick
from dianyi.selection import SelectionContext


GESTURE = DoubleClick(started_at_s=10.0, completed_at_s=10.2, x=5, y=8)


class FreshSelectionBufferTests(unittest.TestCase):
    def test_consumes_selection_created_during_gesture(self) -> None:
        buffer = FreshSelectionBuffer()
        selection = SelectionContext("word", observed_at_s=10.1)
        buffer.record(selection)

        self.assertIs(buffer.consume_for(GESTURE, now_s=10.25), selection)

    def test_rejects_selection_from_before_gesture(self) -> None:
        buffer = FreshSelectionBuffer()
        buffer.record(SelectionContext("stale", observed_at_s=9.9))

        self.assertIsNone(buffer.consume_for(GESTURE, now_s=10.25))

    def test_rejects_selection_that_is_too_old(self) -> None:
        buffer = FreshSelectionBuffer(maximum_age_s=0.1)
        buffer.record(SelectionContext("word", observed_at_s=10.1))

        self.assertIsNone(buffer.consume_for(GESTURE, now_s=10.25))

    def test_selection_can_only_be_consumed_once(self) -> None:
        buffer = FreshSelectionBuffer()
        buffer.record(SelectionContext("word", observed_at_s=10.1))

        self.assertIsNotNone(buffer.consume_for(GESTURE, now_s=10.25))
        self.assertIsNone(buffer.consume_for(GESTURE, now_s=10.26))

    def test_new_event_replaces_old_text(self) -> None:
        buffer = FreshSelectionBuffer()
        buffer.record(SelectionContext("old", observed_at_s=10.05))
        buffer.record(SelectionContext("new", observed_at_s=10.1))

        result = buffer.consume_for(GESTURE, now_s=10.25)

        assert result is not None
        self.assertEqual(result.text, "new")

    def test_rejects_invalid_maximum_age(self) -> None:
        with self.assertRaises(ValueError):
            FreshSelectionBuffer(maximum_age_s=0)


if __name__ == "__main__":
    unittest.main()
