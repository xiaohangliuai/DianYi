"""Coordinate pointer gestures with fresh accessibility selections."""

from __future__ import annotations

import time
from dataclasses import replace
from collections.abc import Callable

from dianyi.capture.freshness import FreshSelectionBuffer
from dianyi.capture.gesture import (
    DoubleClick,
    DoubleClickDetector,
    DoubleClick,
    PointerAction,
    PointerEvent,
)
from dianyi.selection import RejectionReason, SelectionContext, validate_automatic_word


SettleScheduler = Callable[[int, Callable[[], None]], None]
WordHandler = Callable[[str, int, int], None]


class CaptureCoordinator:
    """Pair double clicks with only the selection event that they produced."""

    def __init__(
        self,
        detector: DoubleClickDetector,
        on_word: WordHandler,
        schedule: SettleScheduler,
        *,
        on_dismiss: Callable[[], None] = lambda: None,
        blocklist: frozenset[str] = frozenset(),
        settle_delay_ms: int = 80,
        clock: Callable[[], float] = time.monotonic,
        fallback: Callable[[DoubleClick, Callable[[SelectionContext | None], None]], None] | None = None,
    ) -> None:
        if settle_delay_ms < 0:
            raise ValueError("settle_delay_ms cannot be negative")
        self._detector = detector
        self._on_word = on_word
        self._schedule = schedule
        self._on_dismiss = on_dismiss
        self._blocklist = blocklist
        self._settle_delay_ms = settle_delay_ms
        self._clock = clock
        self._selections = FreshSelectionBuffer()
        self._generation = 0
        self._fallback = fallback

    def record_selection(self, selection: SelectionContext) -> None:
        """Record the most recent AT-SPI selection without persisting it."""
        self._selections.record(selection)

    def handle_pointer_event(self, event: PointerEvent) -> None:
        """Process one main-thread pointer event and schedule completed gestures."""
        if event.action is PointerAction.PRESS:
            self._generation += 1
            self._on_dismiss()

        gesture = self._detector.feed(event)
        if gesture is None:
            return

        self._generation += 1
        generation = self._generation
        self._schedule(
            self._settle_delay_ms,
            lambda: self._finish_gesture(gesture, generation),
        )

    def _finish_gesture(self, gesture: DoubleClick, generation: int) -> None:
        """Validate and publish a gesture's fresh selection after settling."""
        if generation != self._generation:
            return
        selection = self._selections.consume_for(gesture, self._clock())
        if selection is not None:
            if not validate_automatic_word(replace(selection, text="word"), self._blocklist).accepted:
                return
            result = validate_automatic_word(selection, self._blocklist)
            if result.word is not None:
                self._on_word(result.word.text, gesture.x, gesture.y)
                return
            if result.rejection is not RejectionReason.EMPTY:
                return
        if self._fallback is not None:
            def received(context: SelectionContext | None) -> None:
                if context is None or generation != self._generation:
                    return
                result = validate_automatic_word(context, self._blocklist)
                if result.word is not None:
                    self._on_word(result.word.text, gesture.x, gesture.y)
            self._fallback(gesture, received)

    def clear(self) -> None:
        """Invalidate pending work and discard any selected text in memory."""
        self._generation += 1
        self._selections.clear()

    def set_blocklist(self, blocklist: frozenset[str]) -> None:
        """Apply a validated application blocklist on the main thread."""
        self._blocklist = blocklist
        self.clear()
