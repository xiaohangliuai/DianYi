"""Global X11 pointer events using the RECORD extension."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from Xlib import X, display, error, protocol
from Xlib.ext import record

from dianyi.capture.gesture import PointerAction, PointerEvent


class X11UnavailableError(RuntimeError):
    """Raised when global pointer capture is unavailable."""


def pointer_event_from_xevent(
    event: Any,
    monotonic_s: float,
) -> PointerEvent | None:
    """Convert a python-xlib button event into the core event model."""
    actions = {
        X.ButtonPress: PointerAction.PRESS,
        X.ButtonRelease: PointerAction.RELEASE,
    }
    action = actions.get(event.type)
    if action is None:
        return None
    return PointerEvent(
        action=action,
        button=event.detail,
        x=event.root_x,
        y=event.root_y,
        timestamp_ms=event.time,
        monotonic_s=monotonic_s,
    )


class X11PointerListener:
    """Stream global button presses and releases from an X11 session."""

    def __init__(
        self,
        on_event: Callable[[PointerEvent], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self._on_event = on_event
        self._on_error = on_error or (lambda _error: None)
        self._thread: threading.Thread | None = None
        self._control_display: display.Display | None = None
        self._record_display: display.Display | None = None
        self._context: int | None = None
        self._started = threading.Event()
        self._startup_error: Exception | None = None

    def start(self, timeout_s: float = 2.0) -> None:
        """Start capture in a daemon thread and wait for initialization."""
        if self._thread is not None:
            return
        self._started.clear()
        self._startup_error = None
        self._thread = threading.Thread(
            target=self._run,
            name="dianyi-x11-record",
            daemon=True,
        )
        self._thread.start()
        if not self._started.wait(timeout_s):
            self.stop()
            raise X11UnavailableError("timed out while starting X11 capture")
        if self._startup_error is not None:
            failure = self._startup_error
            self.stop()
            raise X11UnavailableError(str(failure)) from failure

    def stop(self) -> None:
        """Disable capture, release X11 resources, and join the worker."""
        control = self._control_display
        context = self._context
        if control is not None and context is not None:
            try:
                control.record_disable_context(context)
                control.sync()
            except (error.XError, OSError):
                pass

        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._thread = None

    def _run(self) -> None:
        """Own both X connections and process RECORD replies."""
        try:
            self._control_display = display.Display()
            self._record_display = display.Display()
            if not self._record_display.has_extension("RECORD"):
                raise X11UnavailableError("X11 RECORD extension is unavailable")
            self._context = self._record_display.record_create_context(
                0,
                [record.AllClients],
                [{"core_requests": (0, 0),
                  "core_replies": (0, 0),
                  "ext_requests": (0, 0, 0, 0),
                  "ext_replies": (0, 0, 0, 0),
                  "delivered_events": (0, 0),
                  "device_events": (X.ButtonPress, X.ButtonRelease),
                  "errors": (0, 0),
                  "client_started": False,
                  "client_died": False}],
            )
            self._started.set()
            self._record_display.record_enable_context(
                self._context,
                self._handle_reply,
            )
        except Exception as failure:
            if not self._started.is_set():
                self._startup_error = failure
                self._started.set()
            else:
                self._on_error(failure)
        finally:
            self._close_displays()

    def _handle_reply(self, reply: Any) -> None:
        """Parse all core events contained in one RECORD reply."""
        if (
            reply.category != record.FromServer
            or reply.client_swapped
            or not reply.data
            or reply.data[0] == 0
        ):
            return

        data = reply.data
        record_display = self._record_display
        if record_display is None:
            return
        while data:
            event, data = protocol.rq.EventField(None).parse_binary_value(
                data,
                record_display.display,
                None,
                None,
            )
            pointer_event = pointer_event_from_xevent(event, time.monotonic())
            if pointer_event is not None:
                self._on_event(pointer_event)

    def _close_displays(self) -> None:
        """Free the RECORD context and both display connections."""
        record_display = self._record_display
        context = self._context
        self._context = None
        if record_display is not None and context is not None:
            try:
                record_display.record_free_context(context)
            except (error.XError, OSError):
                pass
        for connection in (record_display, self._control_display):
            if connection is not None:
                try:
                    connection.close()
                except OSError:
                    pass
        self._record_display = None
        self._control_display = None

