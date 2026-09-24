from __future__ import annotations

import threading
import unittest

from dianyi.translation import (
    ArgosBackend,
    SentenceTranslationController,
    TranslationUnavailableError,
)


class FakeTranslation:
    def __init__(self) -> None:
        self.inputs: list[str] = []

    def translate(self, text: str) -> str:
        self.inputs.append(text)
        return f"\u4e2d\u6587: {text}"


class FakeLanguage:
    def __init__(self, code: str, translation: FakeTranslation | None = None) -> None:
        self.code = code
        self.translation = translation

    def get_translation(self, _target: "FakeLanguage") -> FakeTranslation | None:
        return self.translation


class FakeArgosModule:
    def __init__(self, languages: list[FakeLanguage]) -> None:
        self.languages = languages
        self.calls = 0

    def get_installed_languages(self) -> list[FakeLanguage]:
        self.calls += 1
        return self.languages


class ArgosBackendTests(unittest.TestCase):
    def test_loads_language_pair_lazily_and_only_once(self) -> None:
        translation = FakeTranslation()
        module = FakeArgosModule(
            [FakeLanguage("en", translation), FakeLanguage("zh")]
        )
        loader_calls = 0

        def load_module() -> FakeArgosModule:
            nonlocal loader_calls
            loader_calls += 1
            return module

        backend = ArgosBackend(load_module)
        self.assertEqual(loader_calls, 0)

        self.assertEqual(backend.translate_sentence(" Hello. "), "\u4e2d\u6587: Hello.")
        self.assertEqual(backend.translate_sentence("Again."), "\u4e2d\u6587: Again.")

        self.assertEqual(loader_calls, 1)
        self.assertEqual(module.calls, 1)

    def test_reports_missing_language_pair(self) -> None:
        backend = ArgosBackend(lambda: FakeArgosModule([FakeLanguage("en")]))

        with self.assertRaisesRegex(TranslationUnavailableError, "model"):
            backend.translate_sentence("Hello")

    def test_empty_sentence_does_not_load_model(self) -> None:
        backend = ArgosBackend(lambda: self.fail("loader should not be called"))

        self.assertEqual(backend.translate_sentence("  "), "")


class SentenceTranslationControllerTests(unittest.TestCase):
    def test_shows_loading_immediately_and_delivers_worker_result(self) -> None:
        finished = threading.Event()
        events: list[str] = []
        controller = SentenceTranslationController(
            lambda text: f"translated {text}",
        )
        self.addCleanup(controller.close)

        controller.request(
            "hello",
            on_loading=lambda: events.append("loading"),
            on_result=lambda value: (events.append(value), finished.set()),
            on_error=lambda _error: self.fail("unexpected error"),
        )

        self.assertEqual(events[0], "loading")
        self.assertTrue(finished.wait(1.0))
        self.assertEqual(events, ["loading", "translated hello"])

    def test_discards_late_result_after_newer_request(self) -> None:
        release_first = threading.Event()
        second_finished = threading.Event()
        results: list[str] = []

        def translate(text: str) -> str:
            if text == "first":
                release_first.wait(1.0)
            return f"result {text}"

        controller = SentenceTranslationController(translate)
        self.addCleanup(controller.close)
        controller.request(
            "first",
            on_loading=lambda: None,
            on_result=results.append,
            on_error=lambda _error: self.fail("unexpected error"),
        )
        controller.request(
            "second",
            on_loading=lambda: None,
            on_result=lambda value: (results.append(value), second_finished.set()),
            on_error=lambda _error: self.fail("unexpected error"),
        )
        release_first.set()

        self.assertTrue(second_finished.wait(1.0))
        self.assertEqual(results, ["result second"])

    def test_caches_recent_translation_in_memory(self) -> None:
        calls = 0
        first_finished = threading.Event()
        results: list[str] = []

        def translate(text: str) -> str:
            nonlocal calls
            calls += 1
            return text.upper()

        controller = SentenceTranslationController(translate)
        self.addCleanup(controller.close)
        controller.request(
            "cached",
            on_loading=lambda: None,
            on_result=lambda value: (results.append(value), first_finished.set()),
            on_error=lambda _error: self.fail("unexpected error"),
        )
        self.assertTrue(first_finished.wait(1.0))

        controller.request(
            "cached",
            on_loading=lambda: self.fail("cache hit should not load"),
            on_result=results.append,
            on_error=lambda _error: self.fail("unexpected error"),
        )

        self.assertEqual(calls, 1)
        self.assertEqual(results, ["CACHED", "CACHED"])

    def test_delivers_current_error(self) -> None:
        finished = threading.Event()
        failures: list[Exception] = []

        def fail(_text: str) -> str:
            raise RuntimeError("broken model")

        controller = SentenceTranslationController(fail)
        self.addCleanup(controller.close)
        controller.request(
            "hello",
            on_loading=lambda: None,
            on_result=lambda _value: self.fail("unexpected result"),
            on_error=lambda error: (failures.append(error), finished.set()),
        )

        self.assertTrue(finished.wait(1.0))
        self.assertEqual(str(failures[0]), "broken model")

    def test_rejects_empty_sentence_and_invalid_cache_size(self) -> None:
        with self.assertRaises(ValueError):
            SentenceTranslationController(cache_size=0)
        controller = SentenceTranslationController()
        self.addCleanup(controller.close)
        with self.assertRaises(ValueError):
            controller.request(
                " ",
                on_loading=lambda: None,
                on_result=lambda _value: None,
                on_error=lambda _error: None,
            )


if __name__ == "__main__":
    unittest.main()
