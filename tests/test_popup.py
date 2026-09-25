from __future__ import annotations

import unittest

from dianyi.dictionary.lookup import DictionaryEntry
from dianyi.popup import (
    Rectangle, format_dictionary_entry, place_popup,
    logical_pointer, physical_popup_offsets,
)


MONITOR = Rectangle(x=100, y=50, width=1_000, height=700)


class PopupPlacementTests(unittest.TestCase):
    def test_places_popup_below_and_right_of_pointer(self) -> None:
        result = place_popup(400, 300, 200, 100, MONITOR)

        self.assertEqual(result, (419, 319))

    def test_flips_popup_at_bottom_right_edge(self) -> None:
        result = place_popup(1_090, 740, 200, 100, MONITOR)

        self.assertEqual(result, (871, 621))

    def test_clamps_oversized_popup_to_monitor_margin(self) -> None:
        result = place_popup(500, 300, 2_000, 1_000, MONITOR)

        self.assertEqual(result, (108, 58))

    def test_supports_monitors_with_negative_coordinates(self) -> None:
        monitor = Rectangle(x=-1_920, y=0, width=1_920, height=1_080)

        result = place_popup(-20, 500, 300, 100, monitor)

        self.assertEqual(result, (-339, 519))

    def test_places_popup_half_centimeter_from_scaled_click(self) -> None:
        monitor = Rectangle(0, 0, 2560, 1440)
        x, y = logical_pointer(2800, 1200, 2)
        dx, dy = physical_popup_offsets(monitor, 698, 393)

        position = place_popup(x, y, 200, 100, monitor, offset=dx, vertical_offset=dy)

        self.assertEqual(position, (1418, 618))
        self.assertAlmostEqual((position[0] - x) * 698 / 2560, 5, delta=0.2)
        self.assertAlmostEqual((position[1] - y) * 393 / 1440, 5, delta=0.2)

    def test_missing_monitor_dimensions_use_fallback(self) -> None:
        self.assertEqual(physical_popup_offsets(MONITOR, 0, -1), (19, 19))

    def test_each_axis_uses_its_physical_dimension(self) -> None:
        monitor = Rectangle(0, 0, 1000, 800)
        dx, dy = physical_popup_offsets(monitor, 500, 200)
        self.assertEqual((dx, dy), (10, 20))
        self.assertEqual(
            place_popup(300, 300, 100, 100, monitor, offset=dx, vertical_offset=dy),
            (310, 320),
        )


class DictionaryPopupFormattingTests(unittest.TestCase):
    def test_displays_ecdict_escaped_newlines_as_separate_meanings(self) -> None:
        entry = DictionaryEntry(
            selected_text="apple", headword="apple", phonetic="", parts_of_speech=(),
            meanings=(r"n. 苹果, 家伙\n[医] 苹果",),
        )
        self.assertEqual(format_dictionary_entry(entry).meanings, "n. 苹果, 家伙\n[医] 苹果")

    def test_formats_full_exact_entry(self) -> None:
        entry = DictionaryEntry(
            selected_text="run",
            headword="run",
            phonetic="r\u028cn",
            parts_of_speech=("v", "n"),
            meanings=("vi. \u8dd1", "vt. \u7ba1\u7406"),
        )

        content = format_dictionary_entry(entry)

        self.assertEqual(content.title, "run")
        self.assertEqual(content.details, "/r\u028cn/  v \u00b7 n")
        self.assertEqual(content.meanings, "vi. \u8dd1\nvt. \u7ba1\u7406")

    def test_shows_normalized_headword(self) -> None:
        entry = DictionaryEntry(
            selected_text="children",
            headword="child",
            phonetic="",
            parts_of_speech=(),
            meanings=("n. \u5b69\u5b50",),
        )

        content = format_dictionary_entry(entry)

        self.assertEqual(content.details, "\u2192 child")

    def test_does_not_add_empty_detail_separators(self) -> None:
        entry = DictionaryEntry(
            selected_text="word",
            headword="word",
            phonetic="",
            parts_of_speech=(),
            meanings=("n. \u5355\u8bcd",),
        )

        content = format_dictionary_entry(entry)

        self.assertEqual(content.details, "")


if __name__ == "__main__":
    unittest.main()
