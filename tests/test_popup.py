from __future__ import annotations

import unittest

from dianyi.popup import Rectangle, place_popup


MONITOR = Rectangle(x=100, y=50, width=1_000, height=700)


class PopupPlacementTests(unittest.TestCase):
    def test_places_popup_below_and_right_of_pointer(self) -> None:
        result = place_popup(400, 300, 200, 100, MONITOR)

        self.assertEqual(result, (414, 314))

    def test_flips_popup_at_bottom_right_edge(self) -> None:
        result = place_popup(1_090, 740, 200, 100, MONITOR)

        self.assertEqual(result, (876, 626))

    def test_clamps_oversized_popup_to_monitor_margin(self) -> None:
        result = place_popup(500, 300, 2_000, 1_000, MONITOR)

        self.assertEqual(result, (108, 58))

    def test_supports_monitors_with_negative_coordinates(self) -> None:
        monitor = Rectangle(x=-1_920, y=0, width=1_920, height=1_080)

        result = place_popup(-20, 500, 300, 100, monitor)

        self.assertEqual(result, (-334, 514))


if __name__ == "__main__":
    unittest.main()
