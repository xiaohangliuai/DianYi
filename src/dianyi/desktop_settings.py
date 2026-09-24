"""Read the GNOME desktop settings used by DianYi."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


MOUSE_SCHEMA = "org.gnome.desktop.peripherals.mouse"


class IntegerSettings(Protocol):
    """Small part of Gio.Settings needed by this module."""

    def get_int(self, key: str) -> int: ...


@dataclass(frozen=True, slots=True)
class DesktopInputSettings:
    """GNOME pointer thresholds relevant to double-click selection."""

    double_click_ms: int
    movement_px: int


def read_input_settings(settings: IntegerSettings) -> DesktopInputSettings:
    """Read and validate input thresholds from a settings provider."""
    double_click_ms = settings.get_int("double-click")
    movement_px = settings.get_int("drag-threshold")
    if double_click_ms <= 0:
        raise ValueError("GNOME double-click time must be positive")
    if movement_px < 0:
        raise ValueError("GNOME drag threshold cannot be negative")
    return DesktopInputSettings(
        double_click_ms=double_click_ms,
        movement_px=movement_px,
    )


def load_input_settings() -> DesktopInputSettings:
    """Load pointer thresholds from the active GNOME session."""
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio

    return read_input_settings(Gio.Settings.new(MOUSE_SCHEMA))

