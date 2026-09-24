"""Small, non-focus-stealing GTK popup for capture-prototype results."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rectangle:
    x: int
    y: int
    width: int
    height: int


def place_popup(
    pointer_x: int,
    pointer_y: int,
    popup_width: int,
    popup_height: int,
    monitor: Rectangle,
    *,
    offset: int = 14,
    margin: int = 8,
) -> tuple[int, int]:
    """Place a popup near the pointer while keeping it inside one monitor."""
    min_x = monitor.x + margin
    min_y = monitor.y + margin
    max_x = max(min_x, monitor.x + monitor.width - popup_width - margin)
    max_y = max(min_y, monitor.y + monitor.height - popup_height - margin)

    proposed_x = pointer_x + offset
    proposed_y = pointer_y + offset
    if proposed_x > max_x:
        proposed_x = pointer_x - popup_width - offset
    if proposed_y > max_y:
        proposed_y = pointer_y - popup_height - offset
    return (
        min(max(proposed_x, min_x), max_x),
        min(max(proposed_y, min_y), max_y),
    )


class CapturePopup:
    """Display captured text without taking focus or changing the selection."""

    def __init__(self) -> None:
        import gi

        gi.require_version("Gdk", "3.0")
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gdk, Gtk

        self._gdk = Gdk
        self._gtk = Gtk
        self._window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self._window.set_name("dianyi-capture-popup")
        self._window.set_decorated(False)
        self._window.set_resizable(False)
        self._window.set_keep_above(True)
        self._window.set_accept_focus(False)
        self._window.set_focus_on_map(False)
        self._window.set_skip_pager_hint(True)
        self._window.set_skip_taskbar_hint(True)
        self._window.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)

        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        self._label = Gtk.Label(xalign=0)
        self._label.set_line_wrap(True)
        self._label.set_max_width_chars(36)
        self._label.set_margin_start(14)
        self._label.set_margin_end(14)
        self._label.set_margin_top(10)
        self._label.set_margin_bottom(10)
        frame.add(self._label)
        self._window.add(frame)

    def show_word(self, word: str, pointer_x: int, pointer_y: int) -> None:
        """Show one captured word beside the pointer on its active monitor."""
        self._label.set_text(word)
        self._window.show_all()
        _minimum, natural = self._window.get_preferred_size()

        display = self._gdk.Display.get_default()
        monitor = display.get_monitor_at_point(pointer_x, pointer_y)
        if monitor is None:
            monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        position = place_popup(
            pointer_x,
            pointer_y,
            natural.width,
            natural.height,
            Rectangle(
                geometry.x,
                geometry.y,
                geometry.width,
                geometry.height,
            ),
        )
        self._window.move(*position)
        self._window.present_with_time(self._gdk.CURRENT_TIME)

    def hide(self) -> None:
        """Hide the popup and its selected-text content."""
        self._window.hide()
        self._label.set_text("")

    def destroy(self) -> None:
        """Destroy the popup and release its GTK resources."""
        self.hide()
        self._window.destroy()

