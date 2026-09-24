from __future__ import annotations

import unittest

from dianyi.capture.gesture import (
    DoubleClickDetector,
    PointerAction,
    PointerEvent,
)


def pointer(
    action: PointerAction,
    timestamp_ms: int,
    *,
    x: int = 100,
    y: int = 200,
    button: int = 1,
) -> PointerEvent:
    return PointerEvent(
        action=action,
        button=button,
        x=x,
        y=y,
        timestamp_ms=timestamp_ms,
        monotonic_s=timestamp_ms / 1_000,
    )


class DoubleClickDetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = DoubleClickDetector(interval_ms=400, movement_px=8)

    def click(self, start_ms: int, **kwargs: int) -> object:
        self.detector.feed(pointer(PointerAction.PRESS, start_ms, **kwargs))
        return self.detector.feed(
            pointer(PointerAction.RELEASE, start_ms + 20, **kwargs)
        )

    def test_recognizes_two_nearby_clicks(self) -> None:
        self.assertIsNone(self.click(1_000))
        gesture = self.click(1_180, x=105, y=204)

        self.assertIsNotNone(gesture)
        assert gesture is not None
        self.assertEqual((gesture.x, gesture.y), (105, 204))
        self.assertEqual(gesture.started_at_s, 1.0)

    def test_rejects_clicks_that_are_too_slow(self) -> None:
        self.click(1_000)
        self.assertIsNone(self.click(1_500))

    def test_rejects_clicks_that_are_too_far_apart(self) -> None:
        self.click(1_000)
        self.assertIsNone(self.click(1_180, x=109))

    def test_rejects_a_dragged_click(self) -> None:
        self.detector.feed(pointer(PointerAction.PRESS, 1_000))
        self.detector.feed(pointer(PointerAction.RELEASE, 1_100, x=120))
        self.assertIsNone(self.click(1_200, x=120))

    def test_ignores_non_left_buttons(self) -> None:
        self.click(1_000, button=3)
        self.assertIsNone(self.click(1_100, button=3))

    def test_handles_x11_timestamp_wraparound(self) -> None:
        near_wrap = 2**32 - 100
        self.detector.feed(pointer(PointerAction.PRESS, near_wrap - 20))
        self.detector.feed(pointer(PointerAction.RELEASE, near_wrap))
        self.detector.feed(pointer(PointerAction.PRESS, 20))
        gesture = self.detector.feed(pointer(PointerAction.RELEASE, 40))

        self.assertIsNotNone(gesture)

    def test_does_not_report_overlapping_double_clicks_for_a_triple_click(self) -> None:
        self.click(1_000)
        self.assertIsNotNone(self.click(1_100))
        self.assertIsNone(self.click(1_200))

    def test_rejects_invalid_thresholds(self) -> None:
        with self.assertRaises(ValueError):
            DoubleClickDetector(interval_ms=0, movement_px=8)
        with self.assertRaises(ValueError):
            DoubleClickDetector(interval_ms=400, movement_px=-1)


if __name__ == "__main__":
    unittest.main()
