"""Read newly selected X11 words when accessibility events are unavailable."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from dianyi.capture.gesture import DoubleClick, X11_TIMESTAMP_MODULUS
from dianyi.selection import SelectionContext, validate_automatic_word


@dataclass(frozen=True)
class SelectionSource:
    owner_id: int
    active_window_id: int
    process_id: int
    application_name: str
    wm_class: str


@dataclass(frozen=True)
class SelectionChange:
    timestamp_ms: int
    observed_at_s: float
    source: SelectionSource

    def belongs_to(self, gesture: DoubleClick, now: float) -> bool:
        """Use server timestamps so delayed delivery cannot revive old text."""
        start = gesture.started_timestamp_ms
        end = gesture.completed_timestamp_ms
        if start is None or end is None or not self.timestamp_ms:
            return False
        duration = (end - start) % X11_TIMESTAMP_MODULUS
        offset = (self.timestamp_ms - start) % X11_TIMESTAMP_MODULUS
        return (
            duration < 2_000
            and offset <= duration + 80
            and 0 <= now - self.observed_at_s <= 0.75
        )


class X11SelectionSource:
    """Require selection owner and active window to belong to the same PID."""

    def __init__(self) -> None:
        from Xlib import display

        self.display = display.Display()
        try:
            version = self.display.res_query_version(1, 2)
            if (version.server_major, version.server_minor) < (1, 2):
                raise RuntimeError("XRes 1.2 is required for selection attribution")
        except Exception:
            self.display.close()
            raise

    def __call__(self) -> SelectionSource | None:
        from Xlib import Xatom
        from Xlib.ext import res

        d = self.display
        try:
            owner = d.get_selection_owner(d.intern_atom("PRIMARY"))
            active = d.screen().root.get_full_property(
                d.intern_atom("_NET_ACTIVE_WINDOW"), Xatom.WINDOW
            )
            if not owner or active is None or not active.value[0]:
                return None
            window = d.create_resource_object("window", int(active.value[0]))
            pid = window.get_full_property(d.intern_atom("_NET_WM_PID"), Xatom.CARDINAL)
            classes = window.get_wm_class()
            if pid is None or not classes or not classes[1]:
                return None
            ids = d.res_query_client_ids([
                {"client": owner.id, "mask": res.LocalClientPIDMask}
            ]).ids
            if not any(item.value and item.value[0] == pid.value[0] for item in ids):
                return None
            return SelectionSource(owner.id, window.id, int(pid.value[0]), *classes)
        except Exception:
            return None

    def close(self) -> None:
        self.display.close()


class PrimaryWordReader:
    """Track metadata only; request text only for a fresh double-click."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        source_reader: Callable[[], SelectionSource | None] | None = None,
        clipboard: Any = None,
    ) -> None:
        self._clock = clock
        self._source_reader = source_reader
        self._clipboard = clipboard
        self._handler: int | None = None
        self._latest: SelectionChange | None = None

    def start(self) -> None:
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk, Gtk

        self._source_reader = X11SelectionSource()
        self._clipboard = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        self._handler = self._clipboard.connect("owner-change", self._owner_changed)

    def _owner_changed(self, _clipboard: Any, event: Any) -> None:
        from gi.repository import Gdk

        self._latest = None
        if event.reason != Gdk.OwnerChange.NEW_OWNER or not event.owner:
            return
        source = self._source_reader() if self._source_reader else None
        if source is not None:
            self._latest = SelectionChange(event.selection_time, self._clock(), source)

    def request_word(
        self,
        gesture: DoubleClick,
        callback: Callable[[SelectionContext | None], None],
        *,
        blocklist: frozenset[str] = frozenset(),
    ) -> None:
        change = self._latest
        if (
            change is None
            or not change.belongs_to(gesture, self._clock())
            or self._source_reader is None
            or self._source_reader() != change.source
        ):
            callback(None)
            return
        source = change.source
        metadata = SelectionContext(
            "word", change.observed_at_s, source.application_name, source.wm_class
        )
        if not validate_automatic_word(metadata, blocklist).accepted:
            callback(None)
            return

        def received(_clipboard: Any, text: str | None, _data: Any = None) -> None:
            if (
                self._latest is not change
                or not change.belongs_to(gesture, self._clock())
                or self._source_reader() != source
            ):
                callback(None)
                return
            self._latest = None
            context = SelectionContext(
                text or "", change.observed_at_s, source.application_name, source.wm_class
            )
            callback(context if validate_automatic_word(context, blocklist).accepted else None)

        self._clipboard.request_text(received)

    def stop(self) -> None:
        self._latest = None
        if self._handler is not None:
            self._clipboard.disconnect(self._handler)
            self._handler = None
        if isinstance(self._source_reader, X11SelectionSource):
            self._source_reader.close()
        self._source_reader = None
