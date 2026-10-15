import unittest
from types import SimpleNamespace

from hand_cursor import ClickGate, classify_gesture, map_to_screen, smoothing_alpha


def hand_pose(thumb, index, middle):
    """Create enough normalized landmarks to exercise gesture geometry without a camera."""
    points = [SimpleNamespace(x=0.5, y=0.5, z=0.0) for _ in range(21)]
    points[0] = SimpleNamespace(x=0.5, y=0.76, z=0.0)  # wrist
    points[5] = SimpleNamespace(x=0.42, y=0.50, z=0.0)  # index MCP
    points[9] = SimpleNamespace(x=0.50, y=0.48, z=0.0)  # middle MCP
    points[17] = SimpleNamespace(x=0.62, y=0.50, z=0.0)  # pinky MCP
    points[6] = SimpleNamespace(x=0.42, y=0.42, z=0.0)
    points[8] = SimpleNamespace(x=index[0], y=index[1], z=0.0)
    points[4] = SimpleNamespace(x=thumb[0], y=thumb[1], z=0.0)
    points[12] = SimpleNamespace(x=middle[0], y=middle[1], z=0.0)
    return points


class GestureTests(unittest.TestCase):
    def test_index_thumb_pinch_is_click_not_scroll(self):
        hand = hand_pose(thumb=(0.425, 0.305), index=(0.42, 0.30), middle=(0.58, 0.28))
        self.assertEqual(classify_gesture(hand), "click")

    def test_click_still_registers_if_middle_tip_is_nearby(self):
        hand = hand_pose(thumb=(0.425, 0.305), index=(0.42, 0.30), middle=(0.53, 0.30))
        self.assertEqual(classify_gesture(hand), "click")

    def test_pointing_index_is_move(self):
        hand = hand_pose(thumb=(0.27, 0.58), index=(0.42, 0.30), middle=(0.58, 0.28))
        self.assertEqual(classify_gesture(hand), "move")

    def test_all_three_tips_together_is_scroll(self):
        hand = hand_pose(thumb=(0.424, 0.305), index=(0.42, 0.30), middle=(0.43, 0.31))
        self.assertEqual(classify_gesture(hand), "scroll")

    def test_click_gate_clicks_once_until_release(self):
        gate = ClickGate()
        self.assertFalse(gate.update("click"))
        self.assertTrue(gate.update("click"))
        self.assertFalse(gate.update("click"))
        self.assertFalse(gate.update("move"))
        self.assertFalse(gate.update("click"))
        self.assertTrue(gate.update("click"))

    def test_control_box_maps_all_edges_to_screen(self):
        self.assertEqual(map_to_screen(0.14, 0.10, 1920, 1080), (1, 1))
        self.assertEqual(map_to_screen(0.86, 0.90, 1920, 1080), (1918, 1078))
        left = map_to_screen(0.30, 0.50, 1920, 1080)
        right = map_to_screen(0.70, 0.50, 1920, 1080)
        self.assertLess(left[0], right[0])

    def test_filter_ignores_tiny_jitter_and_keeps_large_motion_fast(self):
        self.assertEqual(smoothing_alpha(1.0), 0.0)
        self.assertGreater(smoothing_alpha(500.0), 0.8)


if __name__ == "__main__":
    unittest.main()
