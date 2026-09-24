from __future__ import annotations

import unittest

from dianyi.capture.coordinator import CaptureCoordinator
from dianyi.capture.gesture import (
    DoubleClickDetector,
    PointerAction,
    PointerEvent,
)
from dianyi.selection import SelectionContext


def pointer(action: PointerAction, milliseconds: int) -> PointerEvent:
    return PointerEvent(
        action=action,
        button=1,
        x=10,
        y=20,
        timestamp_ms=milliseconds,
        monotonic_s=milliseconds / 1_000,
    )


class CaptureCoordinatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scheduled: list[tuple[int, object]] = []
        self.words: list[tuple[str, int, int]] = []
        self.dismissals = 0
        self.now = 1.25
        self.coordinator = CaptureCoordinator(
            DoubleClickDetector(400, 8),
            lambda word, x, y: self.words.append((word, x, y)),
            lambda delay, callback: self.scheduled.append((delay, callback)),
            on_dismiss=self.dismiss,
            clock=lambda: self.now,
        )

    def dismiss(self) -> None:
        self.dismissals += 1

    def double_click(self) -> None:
        for action, milliseconds in (
            (PointerAction.PRESS, 1_000),
            (PointerAction.RELEASE, 1_020),
            (PointerAction.PRESS, 1_150),
            (PointerAction.RELEASE, 1_170),
        ):
            self.coordinator.handle_pointer_event(pointer(action, milliseconds))

    def run_scheduled(self) -> None:
        _delay, callback = self.scheduled.pop(0)
        callback()  # type: ignore[operator]

    def test_publishes_fresh_single_word_after_settle_delay(self) -> None:
        self.double_click()
        self.coordinator.record_selection(SelectionContext("word", 1.1))

        self.assertEqual(self.scheduled[0][0], 80)
        self.run_scheduled()

        self.assertEqual(self.words, [("word", 10, 20)])

    def test_dismisses_existing_result_on_each_left_press(self) -> None:
        self.double_click()

        self.assertEqual(self.dismissals, 2)

    def test_dismisses_on_other_pointer_buttons(self) -> None:
        event = pointer(PointerAction.PRESS, 1_000)
        event = PointerEvent(
            action=event.action,
            button=3,
            x=event.x,
            y=event.y,
            timestamp_ms=event.timestamp_ms,
            monotonic_s=event.monotonic_s,
        )

        self.coordinator.handle_pointer_event(event)

        self.assertEqual(self.dismissals, 1)

    def test_does_not_publish_stale_selection(self) -> None:
        self.coordinator.record_selection(SelectionContext("stale", 0.5))
        self.double_click()

        self.run_scheduled()

        self.assertEqual(self.words, [])

    def test_does_not_publish_a_phrase_for_automatic_lookup(self) -> None:
        self.double_click()
        self.coordinator.record_selection(SelectionContext("two words", 1.1))

        self.run_scheduled()

        self.assertEqual(self.words, [])

    def test_newer_gesture_invalidates_an_older_pending_result(self) -> None:
        self.double_click()
        first_callback = self.scheduled[0][1]
        self.double_click()
        self.coordinator.record_selection(SelectionContext("new", 1.16))

        first_callback()  # type: ignore[operator]

        self.assertEqual(self.words, [])

    def test_clear_discards_selection_and_pending_result(self) -> None:
        self.double_click()
        self.coordinator.record_selection(SelectionContext("word", 1.1))
        self.coordinator.clear()

        self.run_scheduled()

        self.assertEqual(self.words, [])


if __name__ == "__main__":
    unittest.main()
