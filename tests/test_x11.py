from __future__ import annotations

import unittest
from types import SimpleNamespace

from Xlib import X

from dianyi.capture.gesture import PointerAction
from dianyi.capture.x11 import pointer_event_from_xevent


class X11EventConversionTests(unittest.TestCase):
    def event(self, event_type: int) -> SimpleNamespace:
        return SimpleNamespace(
            type=event_type,
            detail=1,
            root_x=123,
            root_y=456,
            time=789,
        )

    def test_converts_button_press(self) -> None:
        result = pointer_event_from_xevent(self.event(X.ButtonPress), 1.25)

        assert result is not None
        self.assertEqual(result.action, PointerAction.PRESS)
        self.assertEqual((result.x, result.y), (123, 456))
        self.assertEqual(result.timestamp_ms, 789)
        self.assertEqual(result.monotonic_s, 1.25)

    def test_converts_button_release(self) -> None:
        result = pointer_event_from_xevent(self.event(X.ButtonRelease), 1.25)

        assert result is not None
        self.assertEqual(result.action, PointerAction.RELEASE)

    def test_ignores_unrelated_events(self) -> None:
        self.assertIsNone(
            pointer_event_from_xevent(self.event(X.MotionNotify), 1.25)
        )


if __name__ == "__main__":
    unittest.main()
