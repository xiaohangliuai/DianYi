from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from dianyi.pronunciation import PiperPronouncer


class PronunciationTests(unittest.TestCase):
    def setUp(self) -> None:
        class ImmediateThread:
            def __init__(self, *, target, **_kwargs):
                self._target = target

            def start(self):
                self._target()
        self.player = PiperPronouncer()
        self.process = MagicMock()
        self.process.poll.return_value = None
        self.process.stdout.readline.return_value = "ok\n"
        self.spawn = self.enterContext(patch("dianyi.pronunciation.subprocess.Popen", return_value=self.process))
        self.ready = self.enterContext(patch("dianyi.pronunciation.select.select", return_value=([self.process.stdout], [], [])))
        self.available = self.enterContext(patch("dianyi.pronunciation.pronunciation_available", return_value=True))
        self.enterContext(patch("dianyi.pronunciation.threading.Thread", ImmediateThread))
        self.addCleanup(self.player.close)

    def test_reuses_model_and_reports_completed_playback(self) -> None:
        results = []
        self.assertTrue(self.player.speak("curious", results.append))
        self.assertTrue(self.player.speak("hello", results.append))
        self.assertEqual(results, [True, True])
        self.spawn.assert_called_once()
        self.assertEqual([call.args[0] for call in self.process.stdin.write.call_args_list], ["curious\n", "hello\n"])

    def test_rejects_phrases_and_unavailable_voice(self) -> None:
        self.assertFalse(self.player.speak("two words"))
        self.available.return_value = False
        self.assertFalse(self.player.speak("curious"))
        self.spawn.assert_not_called()

    def test_drops_repeat_clicks_while_busy(self) -> None:
        self.player._busy.acquire()
        try:
            self.assertFalse(self.player.speak("curious"))
            self.spawn.assert_not_called()
        finally:
            self.player._busy.release()

    def test_timeout_stops_worker_and_allows_retry(self) -> None:
        self.ready.return_value = ([], [], [])
        results = []
        self.assertTrue(self.player.speak("curious", results.append))
        self.assertEqual(results, [False])
        self.process.terminate.assert_called_once()
        self.ready.return_value = ([self.process.stdout], [], [])
        self.assertTrue(self.player.speak("curious", results.append))
        self.assertEqual(results, [False, True])
        self.assertEqual(self.spawn.call_count, 2)

    def test_close_ends_worker_and_prevents_new_speech(self) -> None:
        self.player.speak("curious")
        self.player.close()
        self.process.terminate.assert_called_once()
        self.assertFalse(self.player.speak("hello"))


if __name__ == "__main__":
    unittest.main()
