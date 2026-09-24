"""Lazy offline sentence translation and asynchronous request coordination."""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Protocol


class TranslationUnavailableError(RuntimeError):
    """Raised when Argos or its English-to-Chinese model is unavailable."""


class TranslationBackend(Protocol):
    def translate_sentence(self, text: str) -> str: ...


def _load_argos_module() -> Any:
    """Import Argos only when the first sentence request reaches a worker."""
    try:
        from argostranslate import translate
    except ImportError as error:
        raise TranslationUnavailableError(
            "Argos Translate is not installed"
        ) from error
    return translate


class ArgosBackend:
    """Lazily resolve the installed Argos English-to-Chinese translation."""

    def __init__(self, module_loader: Callable[[], Any] = _load_argos_module) -> None:
        self._module_loader = module_loader
        self._translation: Any = None
        self._load_lock = threading.Lock()

    def _get_translation(self) -> Any:
        """Load and cache the installed language pair once."""
        if self._translation is not None:
            return self._translation
        with self._load_lock:
            if self._translation is not None:
                return self._translation
            module = self._module_loader()
            languages = module.get_installed_languages()
            source = next(
                (language for language in languages if language.code == "en"),
                None,
            )
            target = next(
                (language for language in languages if language.code == "zh"),
                None,
            )
            if source is None or target is None:
                raise TranslationUnavailableError(
                    "Argos English-to-Chinese model is not installed"
                )
            translation = source.get_translation(target)
            if translation is None:
                raise TranslationUnavailableError(
                    "Argos English-to-Chinese model is not installed"
                )
            self._translation = translation
            return translation

    def translate_sentence(self, text: str) -> str:
        """Translate one non-empty English sentence to Simplified Chinese."""
        sentence = text.strip()
        if not sentence:
            return ""
        translated = self._get_translation().translate(sentence).strip()
        if not translated:
            raise RuntimeError("Argos returned an empty translation")
        return translated


_DEFAULT_BACKEND = ArgosBackend()


def translate_sentence(text: str) -> str:
    """Stable internal interface for offline sentence translation."""
    return _DEFAULT_BACKEND.translate_sentence(text)


class SentenceTranslationController:
    """Run translation on one worker and publish only the newest request."""

    def __init__(
        self,
        translate: Callable[[str], str] = translate_sentence,
        dispatch: Callable[[Callable[[], None]], None] = lambda callback: callback(),
        *,
        cache_size: int = 128,
    ) -> None:
        if cache_size <= 0:
            raise ValueError("cache_size must be positive")
        self._translate = translate
        self._dispatch = dispatch
        self._cache_size = cache_size
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="dianyi-translate",
        )
        self._lock = threading.Lock()
        self._generation = 0
        self._closed = False

    def request(
        self,
        text: str,
        *,
        on_loading: Callable[[], None],
        on_result: Callable[[str], None],
        on_error: Callable[[Exception], None],
    ) -> int:
        """Start or retrieve a translation and invalidate older requests."""
        sentence = text.strip()
        if not sentence:
            raise ValueError("sentence cannot be empty")
        with self._lock:
            if self._closed:
                raise RuntimeError("translation controller is closed")
            self._generation += 1
            generation = self._generation
            cached = self._cache.get(sentence)
            if cached is not None:
                self._cache.move_to_end(sentence)

        if cached is not None:
            self._dispatch(lambda: self._deliver_result(generation, cached, on_result))
            return generation

        on_loading()
        future = self._executor.submit(self._translate, sentence)
        future.add_done_callback(
            lambda completed: self._complete(
                generation,
                sentence,
                completed,
                on_result,
                on_error,
            )
        )
        return generation

    def _complete(
        self,
        generation: int,
        sentence: str,
        future: Future[str],
        on_result: Callable[[str], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """Move a worker outcome to the caller's dispatch context."""
        try:
            translated = future.result()
        except Exception as failure:
            self._dispatch(
                lambda: self._deliver_error(generation, failure, on_error)
            )
            return
        with self._lock:
            if not self._closed:
                self._cache[sentence] = translated
                self._cache.move_to_end(sentence)
                while len(self._cache) > self._cache_size:
                    self._cache.popitem(last=False)
        self._dispatch(
            lambda: self._deliver_result(generation, translated, on_result)
        )

    def _deliver_result(
        self,
        generation: int,
        translated: str,
        on_result: Callable[[str], None],
    ) -> None:
        """Publish a result only when no newer request has replaced it."""
        with self._lock:
            current = not self._closed and generation == self._generation
        if current:
            on_result(translated)

    def _deliver_error(
        self,
        generation: int,
        failure: Exception,
        on_error: Callable[[Exception], None],
    ) -> None:
        """Publish an error only for the current request."""
        with self._lock:
            current = not self._closed and generation == self._generation
        if current:
            on_error(failure)

    def cancel(self) -> None:
        """Invalidate the current request without stopping the worker."""
        with self._lock:
            self._generation += 1

    def close(self) -> None:
        """Discard callbacks, clear selected text, and stop the worker."""
        with self._lock:
            self._closed = True
            self._generation += 1
            self._cache.clear()
        self._executor.shutdown(wait=False, cancel_futures=True)

