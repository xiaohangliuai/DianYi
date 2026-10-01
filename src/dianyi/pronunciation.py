"""Speak one English word through a local offline voice."""

from __future__ import annotations

import shutil
import subprocess
import threading

from dianyi.selection import ENGLISH_WORD


def pronunciation_available() -> bool:
    """Return whether a supported local speech client is installed."""
    return shutil.which("espeak-ng") is not None or shutil.which("spd-say") is not None


def speak_word(word: str) -> bool:
    """Queue an offline English pronunciation without blocking GTK."""
    if ENGLISH_WORD.fullmatch(word) is None:
        return False
    direct = shutil.which("espeak-ng")
    dispatcher = None if direct else shutil.which("spd-say")
    if direct is None and dispatcher is None:
        return False
    command = [direct, "-v", "en", word] if direct else [
        dispatcher, "-o", "espeak-ng", "-l", "en", word,
    ]

    def speak() -> None:
        try:
            subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass

    threading.Thread(target=speak, name="dianyi-pronunciation", daemon=True).start()
    return True
