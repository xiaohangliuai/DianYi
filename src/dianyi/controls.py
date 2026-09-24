"""GTK preferences dialog and tray controls."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from dianyi.preferences import Preferences, preferences_from_mapping


def preferences_from_controls(
    automatic_word_lookup: bool,
    blocked_applications_text: str,
    paused: bool,
) -> Preferences:
    """Validate dialog values through the persisted-settings boundary."""
    return preferences_from_mapping(
        {
            "automatic_word_lookup": automatic_word_lookup,
            "blocked_applications": blocked_applications_text.splitlines(),
            "paused": paused,
        }
    )


class PreferencesDialog:
    """Edit user-facing settings without exposing selected text."""

    def run(self, current: Preferences) -> Preferences | None:
        """Run a modal preferences dialog and return validated settings."""
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk

        dialog = Gtk.Dialog(title="DianYi Preferences")
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save", Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_resizable(False)

        grid = Gtk.Grid(column_spacing=12, row_spacing=10)
        grid.set_margin_start(16)
        grid.set_margin_end(16)
        grid.set_margin_top(16)
        grid.set_margin_bottom(16)

        automatic = Gtk.CheckButton(
            label="Automatically look up double-clicked words"
        )
        automatic.set_active(current.automatic_word_lookup)
        blocked = Gtk.TextView()
        blocked.set_wrap_mode(Gtk.WrapMode.NONE)
        blocked.set_size_request(320, 120)
        blocked.get_buffer().set_text("\n".join(current.blocked_applications))

        grid.attach(automatic, 0, 0, 2, 1)
        grid.attach(
            Gtk.Label(
                label="Blocked WM_CLASS values (one per line)",
                xalign=0,
            ),
            0,
            1,
            2,
            1,
        )
        grid.attach(blocked, 0, 2, 2, 1)
        dialog.get_content_area().add(grid)
        dialog.show_all()

        try:
            while dialog.run() == Gtk.ResponseType.OK:
                buffer = blocked.get_buffer()
                blocked_text = buffer.get_text(
                    buffer.get_start_iter(),
                    buffer.get_end_iter(),
                    True,
                )
                try:
                    return preferences_from_controls(
                        automatic.get_active(),
                        blocked_text,
                        current.paused,
                    )
                except Exception as failure:
                    message = Gtk.MessageDialog(
                        transient_for=dialog,
                        modal=True,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.CLOSE,
                        text="Invalid preferences",
                    )
                    message.format_secondary_text(str(failure))
                    message.run()
                    message.destroy()
            return None
        finally:
            dialog.destroy()


class TrayController:
    """Expose Pause/Resume, Preferences, and Quit from a GTK tray menu."""

    def __init__(
        self,
        *,
        paused: bool,
        on_pause_changed: Callable[[bool], None],
        on_preferences: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk

        self._gtk = Gtk
        self._pause_item = Gtk.CheckMenuItem(label="Pause")
        self._pause_item.set_active(paused)
        self._pause_item.connect(
            "toggled",
            lambda item: on_pause_changed(item.get_active()),
        )
        preferences_item = Gtk.MenuItem(label="Preferences")
        preferences_item.connect("activate", lambda _item: on_preferences())
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _item: on_quit())
        self._menu = Gtk.Menu()
        self._menu.append(self._pause_item)
        self._menu.append(preferences_item)
        self._menu.append(Gtk.SeparatorMenuItem())
        self._menu.append(quit_item)
        self._menu.show_all()

        self._indicator: Any = None
        self._status_icon: Any = None
        try:
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import AyatanaAppIndicator3

            self._indicator = AyatanaAppIndicator3.Indicator.new(
                "dianyi",
                "accessories-dictionary",
                AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )
            self._indicator.set_status(
                AyatanaAppIndicator3.IndicatorStatus.ACTIVE
            )
            self._indicator.set_menu(self._menu)
        except (ImportError, ValueError):
            self._status_icon = Gtk.StatusIcon.new_from_icon_name(
                "accessories-dictionary"
            )
            self._status_icon.set_tooltip_text("DianYi")
            self._status_icon.set_visible(True)
            self._status_icon.connect(
                "activate",
                lambda _icon: self._toggle_pause(),
            )
            self._status_icon.connect("popup-menu", self._show_menu)

    def _toggle_pause(self) -> None:
        """Toggle pause from a primary click on the fallback status icon."""
        self._pause_item.set_active(not self._pause_item.get_active())

    def _show_menu(
        self,
        icon: Any,
        button: int,
        activate_time: int,
    ) -> None:
        """Open the fallback GTK status-icon menu."""
        self._menu.popup(
            None,
            None,
            self._gtk.StatusIcon.position_menu,
            icon,
            button,
            activate_time,
        )

    def destroy(self) -> None:
        """Hide tray resources during clean shutdown."""
        if self._status_icon is not None:
            self._status_icon.set_visible(False)
        self._menu.destroy()
        self._indicator = None
