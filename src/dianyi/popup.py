"""Small, non-focus-stealing GTK popup for dictionary results."""

from __future__ import annotations

from dataclasses import dataclass

from dianyi.dictionary.lookup import DictionaryEntry


POPUP_CSS = b"""
#dianyi-capture-popup {
    background-color: transparent;
    background-image: none;
    box-shadow: none;
}
#dianyi-capture-popup .dictionary-card {
    background-color: #f8faff;
    background-image: none;
    border: 1px solid #7e9dcb;
    border-radius: 13px;
    padding: 18px 20px;
    box-shadow: 0 3px 7px rgba(35, 51, 75, 0.16);
}
#dianyi-capture-popup label {
    color: #23334b;
    font-family: sans-serif;
    text-shadow: none;
}
#dianyi-capture-popup .dictionary-title {
    font-size: 22px;
    font-weight: 700;
}
#dianyi-capture-popup .dictionary-details {
    color: #5e6f88;
    font-size: 15px;
    font-weight: 400;
}
#dianyi-capture-popup .dictionary-meanings {
    font-size: 19px;
    font-weight: 400;
}
#dianyi-capture-popup scrolledwindow,
#dianyi-capture-popup viewport {
    background-color: transparent;
    border: none;
    box-shadow: none;
}
#dianyi-capture-popup scrollbar {
    background-color: transparent;
}
#dianyi-capture-popup scrollbar slider {
    background-color: #a6b9d7;
    border-radius: 4px;
    min-width: 5px;
    min-height: 24px;
    border: none;
}
"""


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
        meanings="\n".join(entry.meanings).replace(r"\n", "\n"),
    )


def logical_pointer(x: int, y: int, scale: int) -> tuple[int, int]:
    """Convert X11 device coordinates to GTK logical coordinates."""
    scale = max(1, scale)
    return x // scale, y // scale


def physical_popup_offsets(
    monitor: Rectangle, width_mm: int, height_mm: int,
) -> tuple[int, int]:
    """Return a 5 mm gap per axis, falling back to 96 DPI if size is unknown."""
    return (
        max(1, round(5 * monitor.width / width_mm)) if width_mm > 0 else 19,
        max(1, round(5 * monitor.height / height_mm)) if height_mm > 0 else 19,
    )


def place_popup(
    pointer_x: int,
    pointer_y: int,
    popup_width: int,
    popup_height: int,
    monitor: Rectangle,
    *,
    offset: int = 19,
    vertical_offset: int | None = None,
    margin: int = 8,
) -> tuple[int, int]:
    """Place a popup near the pointer while keeping it inside one monitor."""
    min_x = monitor.x + margin
    min_y = monitor.y + margin
    max_x = max(min_x, monitor.x + monitor.width - popup_width - margin)
    max_y = max(min_y, monitor.y + monitor.height - popup_height - margin)

    offset_y = offset if vertical_offset is None else vertical_offset
    proposed_x = pointer_x + offset
    proposed_y = pointer_y + offset_y
    if proposed_x > max_x:
        proposed_x = pointer_x - popup_width - offset
    if proposed_y > max_y:
        proposed_y = pointer_y - popup_height - offset_y
    return (
        min(max(proposed_x, min_x), max_x),
        min(max(proposed_y, min_y), max_y),
    )


class CapturePopup:
    """Display dictionary content without taking focus."""

    def __init__(self) -> None:
        import gi

        gi.require_version("Gdk", "3.0")
        gi.require_version("Gtk", "3.0")
        gi.require_version("Pango", "1.0")
        from gi.repository import Gdk, Gtk, Pango

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
        screen = self._window.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None:
            self._window.set_visual(visual)
        self._css = Gtk.CssProvider()
        self._css.load_from_data(POPUP_CSS)
        Gtk.StyleContext.add_provider_for_screen(
            screen, self._css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.get_style_context().add_class("dictionary-card")
        content.set_margin_start(8)
        content.set_margin_end(8)
        content.set_margin_top(8)
        content.set_margin_bottom(8)
        content.set_size_request(400, -1)

        self._title = Gtk.Label(xalign=0)
        self._title.set_line_wrap(True)
        self._title.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._title.set_max_width_chars(28)
        self._title.get_style_context().add_class("dictionary-title")
        self._details = Gtk.Label(xalign=0)
        self._details.set_line_wrap(True)
        self._details.set_max_width_chars(40)
        self._details.set_no_show_all(True)
        self._details.get_style_context().add_class("dictionary-details")
        self._meanings = Gtk.Label(xalign=0)
        self._meanings.set_line_wrap(True)
        self._meanings.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._meanings.set_max_width_chars(34)
        self._meanings.set_selectable(False)
        self._meanings.set_margin_top(10)
        self._meanings.get_style_context().add_class("dictionary-meanings")

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_shadow_type(Gtk.ShadowType.NONE)
        scroller.set_min_content_width(358)
        scroller.set_max_content_width(420)
        scroller.set_propagate_natural_width(True)
        scroller.set_max_content_height(320)
        scroller.set_propagate_natural_height(True)
        scroller.add(self._meanings)
        content.pack_start(self._title, False, False, 0)
        content.pack_start(self._details, False, False, 0)
        content.pack_start(scroller, True, True, 0)
        self._scroller = scroller
        self._window.add(content)

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
        self._scroller.get_vadjustment().set_value(0)
        self._window.resize(1, 1)
        self._window.show_all()
        self._details.set_visible(bool(content.details))
        _minimum, natural = self._window.get_preferred_size()

        display = self._gdk.Display.get_default()
        pointer_x, pointer_y = logical_pointer(
            pointer_x, pointer_y, self._window.get_scale_factor()
        )
        monitor = display.get_monitor_at_point(pointer_x, pointer_y)
        if monitor is None:
            monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        bounds = Rectangle(geometry.x, geometry.y, geometry.width, geometry.height)
        offset_x, offset_y = physical_popup_offsets(
            bounds, monitor.get_width_mm(), monitor.get_height_mm()
        )
        position = place_popup(
            pointer_x,
            pointer_y,
            natural.width,
            natural.height,
            bounds,
            offset=offset_x,
            vertical_offset=offset_y,
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
        self._gtk.StyleContext.remove_provider_for_screen(
            self._window.get_screen(), self._css
        )
        self._window.destroy()
