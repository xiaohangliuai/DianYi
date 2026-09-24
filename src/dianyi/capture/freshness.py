"""Associate text-selection events with the gesture that created them."""

from __future__ import annotations

from dianyi.capture.gesture import DoubleClick
from dianyi.selection import SelectionContext


class FreshSelectionBuffer:
    """Hold at most one selection and consume it only for its source gesture."""

    def __init__(self, maximum_age_s: float = 0.75) -> None:
        if maximum_age_s <= 0:
            raise ValueError("maximum_age_s must be positive")
        self._maximum_age_s = maximum_age_s
        self._latest: SelectionContext | None = None

    def record(self, selection: SelectionContext) -> None:
        """Replace any prior selection so text is never accumulated."""
        self._latest = selection

    def consume_for(
        self,
        gesture: DoubleClick,
        now_s: float,
    ) -> SelectionContext | None:
        """Consume a selection only when it was observed during this gesture."""
        selection = self._latest
        self._latest = None
        if selection is None:
            return None
        occurred_during_gesture = (
            gesture.started_at_s <= selection.observed_at_s <= now_s
        )
        recent_enough = now_s - selection.observed_at_s <= self._maximum_age_s
        if not occurred_during_gesture or not recent_enough:
            return None
        return selection

    def clear(self) -> None:
        """Drop the buffered selection immediately."""
        self._latest = None

