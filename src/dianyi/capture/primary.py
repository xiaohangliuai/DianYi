"""Asynchronous access to the current X11 PRIMARY text selection."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class PrimarySelectionReader:
    """Read PRIMARY without claiming ownership or modifying selected text."""

    def __init__(self, clipboard: Any = None) -> None:
        if clipboard is None:
            import gi

            gi.require_version("Gdk", "3.0")
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gdk, Gtk

            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        self._clipboard = clipboard

    def read(self, on_text: Callable[[str], None]) -> None:
        """Request current text and invoke the callback on the GTK main loop."""
        self._clipboard.request_text(self._receive_text, on_text)

    @staticmethod
    def _receive_text(
        _clipboard: Any,
        text: str | None,
        on_text: Callable[[str], None],
    ) -> None:
        """Normalize an unavailable selection to an empty string."""
        on_text(text or "")

