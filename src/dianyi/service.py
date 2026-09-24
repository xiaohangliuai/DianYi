"""Interactive word-lookup service."""

from __future__ import annotations

import os
import signal
import sys
from dataclasses import replace
from typing import Any

from dianyi.capture.atspi import AtspiSelectionWatcher
from dianyi.capture.coordinator import CaptureCoordinator
from dianyi.capture.gesture import DoubleClickDetector, PointerEvent
from dianyi.capture.x11 import X11PointerListener
from dianyi.controls import PreferencesDialog, TrayController
from dianyi.desktop_settings import load_input_settings
from dianyi.dictionary.lookup import DictionaryUnavailableError, lookup_word
from dianyi.popup import CapturePopup
from dianyi.preferences import PreferencesStore
from dianyi.selection import SelectionContext


def _require_x11_session() -> None:
    """Fail clearly instead of pretending global capture works on Wayland."""
    session_type = os.environ.get("XDG_SESSION_TYPE", "").casefold()
    if session_type != "x11" or not os.environ.get("DISPLAY"):
        raise RuntimeError("DianYi capture currently requires an X11 session")


def run_capture_service() -> int:
    """Run the word-lookup service until interrupted."""
    _require_x11_session()

    import gi

    gi.require_version("GLib", "2.0")
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk

    gtk_ready, _arguments = Gtk.init_check(None)
    if not gtk_ready:
        raise RuntimeError("GTK could not connect to the X11 display")

    settings = load_input_settings()
    preferences_store = PreferencesStore()
    preferences = preferences_store.load()
    blocklist = frozenset(preferences.blocked_applications)
    popup = CapturePopup()

    def show_lookup(word: str, pointer_x: int, pointer_y: int) -> None:
        try:
            entry = lookup_word(word)
        except DictionaryUnavailableError:
            popup.show_status(
                word,
                "Dictionary not installed. Run: dianyi --install-dictionary",
                pointer_x,
                pointer_y,
            )
            return
        if entry is None:
            popup.show_status(
                word,
                "No dictionary entry found.",
                pointer_x,
                pointer_y,
            )
            return
        popup.show_entry(entry, pointer_x, pointer_y)

    def schedule(milliseconds: int, callback: Any) -> None:
        def run_once() -> bool:
            callback()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(milliseconds, run_once)

    def dismiss() -> None:
        popup.hide()

    coordinator = CaptureCoordinator(
        DoubleClickDetector(settings.double_click_ms, settings.movement_px),
        show_lookup,
        schedule,
        on_dismiss=dismiss,
        blocklist=blocklist,
    )

    def record_selection(selection: SelectionContext) -> None:
        if preferences.paused:
            return
        coordinator.record_selection(selection)

    def queue_pointer(event: PointerEvent) -> None:
        if preferences.paused or not preferences.automatic_word_lookup:
            return
        GLib.idle_add(coordinator.handle_pointer_event, event)

    def queue_escape() -> None:
        GLib.idle_add(dismiss)

    def queue_runtime_error(failure: Exception) -> None:
        def report_and_quit() -> bool:
            print(
                f"DianYi input capture stopped ({type(failure).__name__}).",
                file=sys.stderr,
            )
            Gtk.main_quit()
            return GLib.SOURCE_REMOVE

        GLib.idle_add(report_and_quit)

    selection_watcher = AtspiSelectionWatcher(record_selection)
    pointer_listener = X11PointerListener(
        queue_pointer,
        queue_runtime_error,
        queue_escape,
    )

    def set_paused(paused: bool) -> None:
        nonlocal preferences
        preferences = replace(preferences, paused=paused)
        preferences_store.save(preferences)
        if paused:
            coordinator.clear()
            popup.hide()

    def show_preferences() -> None:
        nonlocal preferences, blocklist
        updated = PreferencesDialog().run(preferences)
        if updated is None:
            return
        preferences = updated
        blocklist = frozenset(updated.blocked_applications)
        preferences_store.save(updated)
        coordinator.set_blocklist(blocklist)

    tray = TrayController(
        paused=preferences.paused,
        on_pause_changed=set_paused,
        on_preferences=show_preferences,
        on_quit=Gtk.main_quit,
    )

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
        tray.destroy()
        pointer_listener.stop()
        selection_watcher.stop()
        popup.destroy()
    return 0
