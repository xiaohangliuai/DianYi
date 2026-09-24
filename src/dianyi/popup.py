"""Small, non-focus-stealing GTK popup for capture-prototype results."""

from __future__ import annotations

from dataclasses import dataclass

from dianyi.dictionary.lookup import DictionaryEntry


@dataclass(frozen=True, slots=True)
class Rectangle:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class DictionaryPopupContent:
    title: str
    details: str
    meanings: str


def format_dictionary_entry(entry: DictionaryEntry) -> DictionaryPopupContent:
    """Format structured dictionary data without GTK markup or HTML."""
    details: list[str] = []
    if entry.normalized:
        details.append(f"\u2192 {entry.headword}")
    if entry.phonetic:
        details.append(f"/{entry.phonetic.strip('/[]')}/")
    if entry.parts_of_speech:
        details.append(" \u00b7 ".join(entry.parts_of_speech))
    return DictionaryPopupContent(
        title=entry.selected_text,
        details="  ".join(details),
        meanings="\n".join(entry.meanings),
    )


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
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        content.set_margin_start(14)
        content.set_margin_end(14)
        content.set_margin_top(10)
        content.set_margin_bottom(10)

        self._title = Gtk.Label(xalign=0)
        self._title.get_style_context().add_class("title")
        self._details = Gtk.Label(xalign=0)
        self._details.get_style_context().add_class("dim-label")
        self._meanings = Gtk.Label(xalign=0)
        self._meanings.set_line_wrap(True)
        self._meanings.set_line_wrap_mode(2)
        self._meanings.set_max_width_chars(46)
        self._meanings.set_selectable(False)
        content.pack_start(self._title, False, False, 0)
        content.pack_start(self._details, False, False, 0)
        content.pack_start(self._meanings, False, False, 0)
        frame.add(content)
        self._window.add(frame)

    def show_entry(
        self,
        entry: DictionaryEntry,
        pointer_x: int,
        pointer_y: int,
    ) -> None:
        """Show a structured dictionary result beside the pointer."""
        content = format_dictionary_entry(entry)
        self._show_content(content, pointer_x, pointer_y)

    def show_status(
        self,
        title: str,
        message: str,
        pointer_x: int,
        pointer_y: int,
    ) -> None:
        """Show a non-sensitive setup or lookup status beside the pointer."""
        self._show_content(
            DictionaryPopupContent(title=title, details="", meanings=message),
            pointer_x,
            pointer_y,
        )

    def _show_content(
        self,
        content: DictionaryPopupContent,
        pointer_x: int,
        pointer_y: int,
    ) -> None:
        """Populate, position, and reveal the shared popup window."""
        self._title.set_text(content.title)
        self._details.set_text(content.details)
        self._details.set_visible(bool(content.details))
        self._meanings.set_text(content.meanings)
        self._window.show_all()
        self._details.set_visible(bool(content.details))
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
        self._title.set_text("")
        self._details.set_text("")
        self._meanings.set_text("")

    def destroy(self) -> None:
        """Destroy the popup and release its GTK resources."""
        self.hide()
        self._window.destroy()
