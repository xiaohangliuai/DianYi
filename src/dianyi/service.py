"""Interactive capture-only prototype service."""

from __future__ import annotations

import os
import signal
import sys
from typing import Any

from dianyi.capture.atspi import AtspiSelectionWatcher
from dianyi.capture.coordinator import CaptureCoordinator
from dianyi.capture.gesture import DoubleClickDetector, PointerEvent
from dianyi.capture.x11 import X11PointerListener
from dianyi.desktop_settings import load_input_settings
from dianyi.popup import CapturePopup


def _require_x11_session() -> None:
    """Fail clearly instead of pretending global capture works on Wayland."""
    session_type = os.environ.get("XDG_SESSION_TYPE", "").casefold()
    if session_type != "x11" or not os.environ.get("DISPLAY"):
        raise RuntimeError("DianYi capture currently requires an X11 session")


def run_capture_service() -> int:
    """Run the capture-only prototype until interrupted."""
    _require_x11_session()

    import gi

    gi.require_version("GLib", "2.0")
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk

    gtk_ready, _arguments = Gtk.init_check(None)
    if not gtk_ready:
        raise RuntimeError("GTK could not connect to the X11 display")

    settings = load_input_settings()
    popup = CapturePopup()

    def schedule(milliseconds: int, callback: Any) -> None:
        def run_once() -> bool:
            callback()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(milliseconds, run_once)

    coordinator = CaptureCoordinator(
        DoubleClickDetector(settings.double_click_ms, settings.movement_px),
        popup.show_word,
        schedule,
        on_dismiss=popup.hide,
    )

    def queue_pointer(event: PointerEvent) -> None:
        GLib.idle_add(coordinator.handle_pointer_event, event)

    def queue_capture_error(failure: Exception) -> None:
        def report_and_quit() -> bool:
            print(
                f"DianYi X11 capture stopped ({type(failure).__name__}).",
                file=sys.stderr,
            )
            Gtk.main_quit()
            return GLib.SOURCE_REMOVE

        GLib.idle_add(report_and_quit)

    selection_watcher = AtspiSelectionWatcher(coordinator.record_selection)
    pointer_listener = X11PointerListener(queue_pointer, queue_capture_error)

    def request_shutdown() -> bool:
        Gtk.main_quit()
        return GLib.SOURCE_REMOVE

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, request_shutdown)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, request_shutdown)

    try:
        selection_watcher.start()
        pointer_listener.start()
        Gtk.main()
    finally:
        coordinator.clear()
        pointer_listener.stop()
        selection_watcher.stop()
        popup.destroy()
    return 0

