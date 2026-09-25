"""AT-SPI selection events for fresh, source-aware text capture."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from dianyi.selection import SelectionContext


LOGGER = logging.getLogger(__name__)
TEXT_SELECTION_EVENT = "object:text-selection-changed"


def _accessible_name(accessible: Any) -> str:
    """Read an accessible name, tolerating applications that disappear."""
    if accessible is None:
        return ""
    name = accessible.get_name()
    return name or ""


def _text_call(
    text_iface: Any,
    method_name: str,
    *arguments: Any,
    text_interface: Any = None,
) -> Any:
    """Call an AT-SPI Text method without Accessible method-name collisions."""
    if text_interface is None:
        return getattr(text_iface, method_name)(*arguments)
    return getattr(text_interface, method_name)(text_iface, *arguments)


def selection_from_accessible(
    source: Any,
    observed_at_s: float,
    *,
    password_role: Any = None,
    text_interface: Any = None,
) -> SelectionContext:
    """Extract the current selection and safety metadata from an accessible."""
    text = ""
    text_iface = source.get_text_iface()
    if text_iface is not None and _text_call(
        text_iface,
        "get_n_selections",
        text_interface=text_interface,
    ) == 1:
        selected_range = _text_call(
            text_iface,
            "get_selection",
            0,
            text_interface=text_interface,
        )
        if selected_range.end_offset > selected_range.start_offset:
            text = _text_call(
                text_iface,
                "get_text",
                selected_range.start_offset,
                selected_range.end_offset,
                text_interface=text_interface,
            )

    application_name = _accessible_name(source.get_application())
    role = source.get_role()
    role_name = (source.get_role_name() or "").casefold()
    is_password = role_name == "password text" or (
        password_role is not None and role == password_role
    )
    return SelectionContext(
        text=text,
        observed_at_s=observed_at_s,
        application_name=application_name,
        is_password=is_password,
    )


class AtspiSelectionWatcher:
    """Forward AT-SPI text-selection changes as in-memory selection contexts."""

    def __init__(self, on_selection: Callable[[SelectionContext], None]) -> None:
        self._on_selection = on_selection
        self._listener: Any = None
        self._atspi: Any = None

    def start(self) -> None:
        """Register the global text-selection event listener."""
        if self._listener is not None:
            return

        import gi

        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi

        Atspi.init()
        listener = Atspi.EventListener.new(self._handle_event, None)
        if not listener.register(TEXT_SELECTION_EVENT):
            raise RuntimeError("AT-SPI text-selection listener registration failed")
        self._atspi = Atspi
        self._listener = listener

    def stop(self) -> None:
        """Deregister the listener without retaining selected text."""
        listener = self._listener
        self._listener = None
        self._atspi = None
        if listener is not None:
            listener.deregister(TEXT_SELECTION_EVENT)

    def _handle_event(self, event: Any, _user_data: Any = None) -> None:
        """Convert one AT-SPI event while keeping selected text out of logs."""
        atspi = self._atspi
        if atspi is None:
            return
        try:
            context = selection_from_accessible(
                event.source,
                time.monotonic(),
                password_role=atspi.Role.PASSWORD_TEXT,
                text_interface=atspi.Text,
            )
        except Exception as error:
            LOGGER.debug(
                "Ignored inaccessible text-selection event (%s)",
                type(error).__name__,
            )
            return
        self._on_selection(context)
