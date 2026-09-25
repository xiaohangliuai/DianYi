from __future__ import annotations

import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

from dianyi.capture.gesture import DoubleClick
from dianyi.capture.primary_word import PrimaryWordReader, SelectionChange, SelectionSource, X11SelectionSource


class Clipboard:
    def __init__(self):
        self.callback = None
        self.requests = 0

    def request_text(self, callback):
        self.callback = callback
        self.requests += 1

    def reply(self, text):
        self.callback(self, text)


class PrimaryWordTests(unittest.TestCase):
    def setUp(self):
        self.source = SelectionSource(10, 20, 30, "chrome", "Google-chrome")
        self.now = 1.25
        self.clipboard = Clipboard()
        self.reader = PrimaryWordReader(
            clock=lambda: self.now,
            source_reader=lambda: self.source,
            clipboard=self.clipboard,
        )
        self.reader._latest = SelectionChange(1150, 1.16, self.source)
        self.gesture = DoubleClick(1.0, 1.17, 100, 200, 1000, 1170)
        self.results = []

    def request(self, **kwargs):
        self.reader.request_word(self.gesture, self.results.append, **kwargs)

    def test_reads_fresh_word_with_source_metadata(self):
        self.request()
        self.clipboard.reply("hello")
        self.assertEqual(self.results[0].text, "hello")
        self.assertEqual(self.results[0].wm_class, "Google-chrome")
        self.request()
        self.assertIsNone(self.results[-1])
        self.assertEqual(self.clipboard.requests, 1)

    def test_delayed_old_owner_event_does_not_make_old_text_fresh(self):
        self.reader._latest = SelectionChange(900, 1.2, self.source)
        self.request()
        self.assertEqual(self.clipboard.requests, 0)
        self.assertEqual(self.results, [None])

    def test_rejects_change_after_gesture_window(self):
        self.reader._latest = SelectionChange(1400, 1.2, self.source)
        self.request()
        self.assertEqual(self.clipboard.requests, 0)

    def test_rejects_blocked_app_before_reading_text(self):
        self.request(blocklist=frozenset({"google-chrome"}))
        self.assertEqual(self.clipboard.requests, 0)

    def test_rejects_changed_active_window_before_request(self):
        self.source = replace(self.source, active_window_id=40)
        self.request()
        self.assertEqual(self.clipboard.requests, 0)

    def test_rejects_owner_changed_during_async_read(self):
        self.request()
        self.source = replace(self.source, owner_id=11)
        self.clipboard.reply("hello")
        self.assertEqual(self.results, [None])

    def test_rejects_new_selection_even_when_owner_stays_the_same(self):
        self.request()
        self.reader._latest = SelectionChange(1180, 1.18, self.source)
        self.clipboard.reply("hello")
        self.assertEqual(self.results, [None])

    def test_rejects_late_results(self):
        self.request()
        self.now = 2.5
        self.clipboard.reply("hello")
        self.assertEqual(self.results, [None])

    def test_rejects_sentences(self):
        self.request()
        self.clipboard.reply("hello world")
        self.assertEqual(self.results, [None])

    def test_handles_server_timestamp_wrap(self):
        self.gesture = replace(self.gesture, started_timestamp_ms=2**32-50,
                               completed_timestamp_ms=20)
        self.reader._latest = SelectionChange(10, 1.16, self.source)
        self.request()
        self.clipboard.reply("hello")
        self.assertEqual(self.results[0].text, "hello")

    def test_stop_discards_pending_reply(self):
        self.request()
        self.reader.stop()
        self.clipboard.reply("hello")
        self.assertEqual(self.results, [None])


class SourceAttributionTests(unittest.TestCase):
    def make_reader(self, owner_pid):
        reader = object.__new__(X11SelectionSource)
        reader.display = Mock()
        d = reader.display
        d.get_selection_owner.return_value = SimpleNamespace(id=10)
        d.screen.return_value.root.get_full_property.return_value = SimpleNamespace(value=[20])
        w = d.create_resource_object.return_value
        w.id = 20
        w.get_wm_class.return_value = ("chrome", "Google-chrome")
        w.get_full_property.return_value = SimpleNamespace(value=[30])
        d.res_query_client_ids.return_value = SimpleNamespace(
            ids=[SimpleNamespace(value=[owner_pid])]
        )
        return reader

    def test_accepts_same_application_process(self):
        result = self.make_reader(30)()
        self.assertEqual(result, SelectionSource(10,20,30,"chrome","Google-chrome"))

    def test_rejects_selection_from_another_process(self):
        self.assertIsNone(self.make_reader(99)())
