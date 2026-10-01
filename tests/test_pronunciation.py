from __future__ import annotations

import unittest
from unittest.mock import patch

from dianyi.pronunciation import speak_word


class PronunciationTests(unittest.TestCase):
    def test_speaks_only_one_english_word_as_an_argument(self) -> None:
        commands: list[list[str]] = []

        class ImmediateThread:
            def __init__(self, *, target, **_kwargs):
                self._target = target

            def start(self):
                self._target()

        def record(command, **_kwargs):
            commands.append(command)

        with patch("dianyi.pronunciation.shutil.which", return_value="/usr/bin/espeak-ng"), \
             patch("dianyi.pronunciation.threading.Thread", ImmediateThread), \
             patch("dianyi.pronunciation.subprocess.run", side_effect=record):
            self.assertTrue(speak_word("curious"))
            self.assertFalse(speak_word("two words"))

        self.assertEqual(commands, [["/usr/bin/espeak-ng", "-v", "en", "curious"]])

    def test_uses_existing_speech_dispatcher_when_direct_client_is_missing(self) -> None:
        def find(name):
            return "/usr/bin/spd-say" if name == "spd-say" else None

        with patch("dianyi.pronunciation.shutil.which", side_effect=find), \
             patch("dianyi.pronunciation.threading.Thread") as thread:
            self.assertTrue(speak_word("curious"))
            thread.assert_called_once()

    def test_missing_speech_client_does_not_start_playback(self) -> None:
        with patch("dianyi.pronunciation.shutil.which", return_value=None), \
             patch("dianyi.pronunciation.threading.Thread") as thread:
            self.assertFalse(speak_word("curious"))
            thread.assert_not_called()


if __name__ == "__main__":
    unittest.main()
