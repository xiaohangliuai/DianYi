"""Offline pronunciation with a lazily loaded, reusable Piper voice."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import select
import shutil
import subprocess
import threading

from dianyi.selection import ENGLISH_WORD
from dianyi.voice_install import voice_model_path, voice_runtime_path


def pronunciation_available() -> bool:
    runtime = voice_runtime_path()
    model = voice_model_path()
    return (
        (runtime / "bin/python").is_file()
        and (runtime / ".ready").is_file()
        and model.is_file()
        and model.with_suffix(".onnx.json").is_file()
        and shutil.which("aplay") is not None
    )


class PiperPronouncer:
    """Keep the model loaded between clicks; never queue overlapping speech."""

    def __init__(self) -> None:
        self._busy = threading.Lock()
        self._process_lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        self._closed = False

    def speak(self, word: str, on_done: Callable[[bool], None] | None = None) -> bool:
        if (
            self._closed or ENGLISH_WORD.fullmatch(word) is None
            or not pronunciation_available() or not self._busy.acquire(blocking=False)
        ):
            return False

        def play() -> None:
            success = False
            try:
                with self._process_lock:
                    if self._closed:
                        return
                    if self._process is None or self._process.poll() is not None:
                        self._discard_process()
                        self._process = subprocess.Popen(
                            [str(voice_runtime_path() / "bin/python"), "-u",
                             str(Path(__file__).with_name("piper_worker.py")),
                             str(voice_model_path()), shutil.which("aplay")],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True,
                        )
                    process = self._process
                process.stdin.write(word + "\n")
                process.stdin.flush()
                readable, _, _ = select.select([process.stdout], [], [], 30)
                success = bool(readable) and process.stdout.readline().strip() == "ok"
            except (OSError, ValueError):
                pass
            finally:
                if not success:
                    with self._process_lock:
                        self._discard_process()
                self._busy.release()
                if on_done is not None:
                    on_done(success)

        threading.Thread(target=play, name="dianyi-pronunciation", daemon=True).start()
        return True

    def _discard_process(self) -> None:
        """Called with the process lock held."""
        process, self._process = self._process, None
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for stream in (process.stdin, process.stdout):
            if stream is not None:
                stream.close()

    def close(self) -> None:
        with self._process_lock:
            self._closed = True
            self._discard_process()


_pronouncer = PiperPronouncer()


def speak_word(word: str, on_done: Callable[[bool], None] | None = None) -> bool:
    return _pronouncer.speak(word, on_done)


def close_pronunciation() -> None:
    _pronouncer.close()
