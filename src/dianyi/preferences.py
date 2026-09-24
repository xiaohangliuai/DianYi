"""XDG-compliant, selection-free local preferences."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class PreferencesError(RuntimeError):
    """Raised when a preferences file is malformed or cannot be used."""


@dataclass(frozen=True, slots=True)
class Preferences:
    automatic_word_lookup: bool = True
    blocked_applications: tuple[str, ...] = ()
    paused: bool = False


def default_preferences_path() -> Path:
    """Return the XDG path for DianYi's local settings file."""
    config_home = os.environ.get("XDG_CONFIG_HOME")
    root = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return root / "dianyi" / "settings.json"


def preferences_from_mapping(values: dict[str, Any]) -> Preferences:
    """Validate preferences loaded from JSON and normalize the blocklist."""
    automatic = values.get("automatic_word_lookup", True)
    blocked = values.get("blocked_applications", [])
    paused = values.get("paused", False)
    if not isinstance(automatic, bool):
        raise PreferencesError("automatic_word_lookup must be a boolean")
    if not isinstance(paused, bool):
        raise PreferencesError("paused must be a boolean")
    if not isinstance(blocked, list) or not all(
        isinstance(item, str) for item in blocked
    ):
        raise PreferencesError("blocked_applications must be a list of strings")

    normalized_blocklist: list[str] = []
    for item in blocked:
        application = item.strip()
        if application and application.casefold() not in {
            existing.casefold() for existing in normalized_blocklist
        }:
            normalized_blocklist.append(application)
    return Preferences(
        automatic_word_lookup=automatic,
        blocked_applications=tuple(normalized_blocklist),
        paused=paused,
    )


class PreferencesStore:
    """Load and atomically save settings without any selected-text fields."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = (
            Path(path).expanduser().resolve()
            if path is not None
            else default_preferences_path()
        )

    def load(self) -> Preferences:
        """Return defaults when absent, otherwise validate the complete file."""
        if not self.path.exists():
            return Preferences()
        try:
            values = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise PreferencesError(f"cannot read preferences: {error}") from error
        if not isinstance(values, dict):
            raise PreferencesError("preferences root must be a JSON object")
        return preferences_from_mapping(values)

    def save(self, preferences: Preferences) -> None:
        """Atomically replace the settings file with mode 0600."""
        validated = preferences_from_mapping(
            {
                **asdict(preferences),
                "blocked_applications": list(preferences.blocked_applications),
            }
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
            delete=False,
        )
        temporary_path = Path(temporary_file.name)
        try:
            with temporary_file:
                json.dump(
                    {
                        **asdict(validated),
                        "blocked_applications": list(
                            validated.blocked_applications
                        ),
                    },
                    temporary_file,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            temporary_path.chmod(0o600)
            os.replace(temporary_path, self.path)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise
