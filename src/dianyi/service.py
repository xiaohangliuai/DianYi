"""Interactive capture-only prototype service."""

from __future__ import annotations

import os
import signal
import sys
import time
from dataclasses import replace
from typing import Any

from dianyi.capture.atspi import AtspiSelectionWatcher
from dianyi.capture.coordinator import CaptureCoordinator
from dianyi.capture.gesture import DoubleClickDetector, PointerEvent
from dianyi.capture.primary import PrimarySelectionReader
from dianyi.capture.shortcut import X11ShortcutListener
from dianyi.capture.x11 import X11PointerListener
from dianyi.desktop_settings import load_input_settings
from dianyi.controls import PreferencesDialog, TrayController
from dianyi.dictionary.lookup import DictionaryUnavailableError, lookup_word
from dianyi.popup import CapturePopup
from dianyi.preferences import PreferencesStore
from dianyi.selection import SelectionContext, validate_sentence
from dianyi.translation import SentenceTranslationController


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
    gi.require_version("Gdk", "3.0")
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gdk, GLib, Gtk

    gtk_ready, _arguments = Gtk.init_check(None)
    if not gtk_ready:
        raise RuntimeError("GTK could not connect to the X11 display")

    settings = load_input_settings()
    preferences_store = PreferencesStore()
    preferences = preferences_store.load()
    blocklist = frozenset(preferences.blocked_applications)
    popup = CapturePopup()
    primary_selection = PrimarySelectionReader()

    def dispatch(callback: Any) -> None:
        def run_once() -> bool:
            callback()
            return GLib.SOURCE_REMOVE

        GLib.idle_add(run_once)

    translator = SentenceTranslationController(dispatch=dispatch)

    def pointer_position() -> tuple[int, int]:
        display = Gdk.Display.get_default()
        pointer = display.get_default_seat().get_pointer()
        _screen, x, y = pointer.get_position()
        return x, y

    def start_translation(
        sentence: str,
        pointer_x: int,
        pointer_y: int,
        *,
        fallback: bool = False,
    ) -> None:
        translator.request(
            sentence,
            on_loading=lambda: popup.show_translation_loading(
                sentence,
                pointer_x,
                pointer_y,
            ),
            on_result=lambda translated: popup.show_translation(
                sentence,
                translated,
                pointer_x,
                pointer_y,
                fallback=fallback,
            ),
            on_error=lambda _error: popup.show_status(
                sentence,
                "Translation unavailable. Install the Argos runtime and model.",
                pointer_x,
                pointer_y,
            ),
        )

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
            start_translation(word, pointer_x, pointer_y, fallback=True)
            return
        popup.show_entry(entry, pointer_x, pointer_y)

    def schedule(milliseconds: int, callback: Any) -> None:
        def run_once() -> bool:
            callback()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(milliseconds, run_once)

    def dismiss() -> None:
        translator.cancel()
        popup.hide()

    coordinator = CaptureCoordinator(
        DoubleClickDetector(settings.double_click_ms, settings.movement_px),
        show_lookup,
        schedule,
        on_dismiss=dismiss,
        blocklist=blocklist,
    )

    latest_accessible_selection: SelectionContext | None = None

    def record_selection(selection: SelectionContext) -> None:
        nonlocal latest_accessible_selection
        if preferences.paused:
            return
        latest_accessible_selection = selection
        coordinator.record_selection(selection)

    def translate_primary(text: str, pointer_x: int, pointer_y: int) -> None:
        source = latest_accessible_selection
        if source is not None and source.text.strip() == text.strip():
            context = SelectionContext(
                text=text,
                observed_at_s=time.monotonic(),
                application_name=source.application_name,
                wm_class=source.wm_class,
                is_password=source.is_password,
            )
        else:
            context = SelectionContext(text=text, observed_at_s=time.monotonic())
        validation = validate_sentence(context, blocklist)
        if validation.sentence is None:
            popup.show_status(
                "Selection not translated",
                validation.rejection.value,
                pointer_x,
                pointer_y,
            )
            return
        start_translation(validation.sentence.text, pointer_x, pointer_y)

    def request_sentence_translation() -> bool:
        if preferences.paused:
            return GLib.SOURCE_REMOVE
        translator.cancel()
        popup.hide()
        pointer_x, pointer_y = pointer_position()
        primary_selection.read(
            lambda text: translate_primary(text, pointer_x, pointer_y)
        )
        return GLib.SOURCE_REMOVE

    def queue_shortcut() -> None:
        GLib.idle_add(request_sentence_translation)

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
    shortcut_listener = X11ShortcutListener(
        preferences.shortcut,
        queue_shortcut,
        queue_runtime_error,
    )

    def set_paused(paused: bool) -> None:
        nonlocal preferences, latest_accessible_selection
        preferences = replace(preferences, paused=paused)
        preferences_store.save(preferences)
        if paused:
            latest_accessible_selection = None
            coordinator.clear()
            translator.cancel()
            popup.hide()

    def show_preferences() -> None:
        nonlocal preferences, blocklist
        updated = PreferencesDialog().run(preferences)
        if updated is None:
            return
        shortcut_changed = updated.shortcut != preferences.shortcut
        preferences = updated
        blocklist = frozenset(updated.blocked_applications)
        preferences_store.save(updated)
        coordinator.set_blocklist(blocklist)
        if shortcut_changed:
            x, y = pointer_position()
            popup.show_status(
                "Preferences saved",
                "Restart DianYi to activate the new shortcut.",
                x,
                y,
            )

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
        shortcut_listener.start()
        Gtk.main()
    finally:
        coordinator.clear()
        translator.close()
        tray.destroy()
        shortcut_listener.stop()
        pointer_listener.stop()
        selection_watcher.stop()
        popup.destroy()
    return 0
