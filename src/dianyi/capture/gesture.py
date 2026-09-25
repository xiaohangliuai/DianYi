"""Pure pointer-gesture recognition used by the X11 event adapter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


X11_TIMESTAMP_MODULUS = 2**32


class PointerAction(Enum):
    """Pointer actions relevant to selection gestures."""

    PRESS = "press"
    RELEASE = "release"


@dataclass(frozen=True, slots=True)
class PointerEvent:
    """Desktop-independent representation of an X11 pointer event."""

    action: PointerAction
    button: int
    x: int
    y: int
    timestamp_ms: int
    monotonic_s: float


@dataclass(frozen=True, slots=True)
class _Click:
    press: PointerEvent
    release: PointerEvent


@dataclass(frozen=True, slots=True)
class DoubleClick:
    """A completed double click and its freshness interval."""

    started_at_s: float
    completed_at_s: float
    x: int
    y: int
    started_timestamp_ms: int | None = None
    completed_timestamp_ms: int | None = None


def _x11_elapsed_ms(earlier: int, later: int) -> int:
    """Calculate elapsed X11 milliseconds, including uint32 wraparound."""
    return (later - earlier) % X11_TIMESTAMP_MODULUS


def _within_distance(first: PointerEvent, second: PointerEvent, limit: int) -> bool:
    """Return whether two pointer positions fit the desktop movement limit."""
    return abs(second.x - first.x) <= limit and abs(second.y - first.y) <= limit


class DoubleClickDetector:
    """Recognize non-dragging left-button double clicks from pointer events."""

    def __init__(self, interval_ms: int, movement_px: int) -> None:
        if interval_ms <= 0:
            raise ValueError("interval_ms must be positive")
        if movement_px < 0:
            raise ValueError("movement_px cannot be negative")
        self._interval_ms = interval_ms
        self._movement_px = movement_px
        self._active_press: PointerEvent | None = None
        self._previous_click: _Click | None = None

    def feed(self, event: PointerEvent) -> DoubleClick | None:
        """Consume one pointer event and return a newly completed double click."""
        if event.button != 1:
            return None

        if event.action is PointerAction.PRESS:
            self._active_press = event
            return None

        press = self._active_press
        self._active_press = None
        if press is None or not _within_distance(press, event, self._movement_px):
            self._previous_click = None
            return None

        current = _Click(press=press, release=event)
        previous = self._previous_click
        if previous is None:
            self._previous_click = current
            return None

        elapsed_ms = _x11_elapsed_ms(
            previous.release.timestamp_ms,
            current.release.timestamp_ms,
        )
        close_enough = _within_distance(
            previous.release,
            current.release,
            self._movement_px,
        )
        if elapsed_ms <= self._interval_ms and close_enough:
            self._previous_click = None
            return DoubleClick(
                started_at_s=previous.press.monotonic_s,
                completed_at_s=current.release.monotonic_s,
                x=current.release.x,
                y=current.release.y,
                started_timestamp_ms=previous.press.timestamp_ms,
                completed_timestamp_ms=current.release.timestamp_ms,
            )

        self._previous_click = current
        return None
