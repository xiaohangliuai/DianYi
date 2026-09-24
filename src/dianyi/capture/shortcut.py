"""Configurable X11 global shortcut registration."""

from __future__ import annotations

import select
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from Xlib import X, XK, display, error


DEFAULT_SHORTCUT = "Super+T"
LOCK_VARIANTS = (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask)
MODIFIERS = {
    "shift": X.ShiftMask,
    "control": X.ControlMask,
    "ctrl": X.ControlMask,
    "alt": X.Mod1Mask,
    "super": X.Mod4Mask,
}


class ShortcutConflictError(RuntimeError):
    """Raised when another X11 client already owns the shortcut."""


class ShortcutUnavailableError(RuntimeError):
    """Raised when a shortcut cannot be represented or registered."""


@dataclass(frozen=True, slots=True)
class Shortcut:
    label: str
    key_name: str
    modifiers: int


def parse_shortcut(value: str) -> Shortcut:
    """Parse a readable X11 shortcut such as ``Super+T``."""
    parts = [part.strip() for part in value.split("+") if part.strip()]
    if len(parts) < 2:
        raise ValueError("shortcut must include a modifier and key")
    key_name = parts[-1]
    if len(key_name) != 1 or not key_name.isascii():
        raise ValueError("shortcut key must be one ASCII character")
    modifiers = 0
    seen: set[str] = set()
    for raw_modifier in parts[:-1]:
        modifier = raw_modifier.casefold()
        if modifier not in MODIFIERS:
            raise ValueError(f"unsupported shortcut modifier: {raw_modifier}")
        if modifier in seen:
            raise ValueError(f"duplicate shortcut modifier: {raw_modifier}")
        seen.add(modifier)
        modifiers |= MODIFIERS[modifier]
    canonical = "+".join(
        [part.title() for part in parts[:-1]] + [key_name.upper()]
    )
    return Shortcut(canonical, key_name.lower(), modifiers)


class X11ShortcutListener:
    """Own an X11 passive key grab and forward activations from a worker."""

    def __init__(
        self,
        shortcut: str,
        on_activate: Callable[[], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self.shortcut = parse_shortcut(shortcut)
        self._on_activate = on_activate
        self._on_error = on_error or (lambda _error: None)
        self._thread: threading.Thread | None = None
        self._stop_requested = threading.Event()
        self._started = threading.Event()
        self._startup_error: Exception | None = None

    def start(self, timeout_s: float = 2.0) -> None:
        """Register the shortcut and wait for conflict detection to finish."""
        if self._thread is not None:
            return
        self._stop_requested.clear()
        self._started.clear()
        self._startup_error = None
        self._thread = threading.Thread(
            target=self._run,
            name="dianyi-x11-shortcut",
            daemon=True,
        )
        self._thread.start()
        if not self._started.wait(timeout_s):
            self.stop()
            raise ShortcutUnavailableError("timed out while registering shortcut")
        if self._startup_error is not None:
            failure = self._startup_error
            self.stop()
            raise failure

    def stop(self) -> None:
        """Request shutdown and wait for the worker to release its key grabs."""
        self._stop_requested.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._thread = None

    def _run(self) -> None:
        """Register and process shortcut events on one Xlib-owned thread."""
        connection: display.Display | None = None
        root: Any = None
        keycode = 0
        grabbed_modifiers: list[int] = []
        try:
            connection = display.Display()
            root = connection.screen().root
            keysym = XK.string_to_keysym(self.shortcut.key_name)
            keycode = connection.keysym_to_keycode(keysym)
            if keysym == 0 or keycode == 0:
                raise ShortcutUnavailableError(
                    f"X11 cannot map shortcut key {self.shortcut.key_name!r}"
                )

            registration_errors: list[error.XError] = []

            def collect_error(
                failure: error.XError,
                _request: Any = None,
            ) -> None:
                registration_errors.append(failure)

            previous_handler = connection.set_error_handler(collect_error)
            for lock_mask in LOCK_VARIANTS:
                modifiers = self.shortcut.modifiers | lock_mask
                root.grab_key(
                    keycode,
                    modifiers,
                    False,
                    X.GrabModeAsync,
                    X.GrabModeAsync,
                )
                grabbed_modifiers.append(modifiers)
            connection.sync()
            connection.set_error_handler(previous_handler)
            if registration_errors:
                raise ShortcutConflictError(
                    f"shortcut {self.shortcut.label} is already in use"
                )
            self._started.set()

            last_activation_ms: int | None = None
            while not self._stop_requested.is_set():
                readable, _writable, _errors = select.select(
                    [connection.fileno()],
                    [],
                    [],
                    0.25,
                )
                if not readable:
                    continue
                while connection.pending_events():
                    event = connection.next_event()
                    if event.type != X.KeyPress:
                        continue
                    if (
                        last_activation_ms is not None
                        and (event.time - last_activation_ms) % 2**32 < 200
                    ):
                        continue
                    last_activation_ms = event.time
                    self._on_activate()
        except Exception as failure:
            if not self._started.is_set():
                self._startup_error = failure
                self._started.set()
            else:
                self._on_error(failure)
        finally:
            if connection is not None and root is not None and keycode:
                for modifiers in grabbed_modifiers:
                    try:
                        root.ungrab_key(keycode, modifiers)
                    except error.XError:
                        pass
                try:
                    connection.sync()
                except (error.XError, OSError):
                    pass
            if connection is not None:
                try:
                    connection.close()
                except OSError:
                    pass

