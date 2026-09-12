"""
tests.unit.test_handedness_stabilizer
======================================
Unit tests for HandednessStabilizer implementation.
"""

import unittest
from core.models import Handedness
from tracking.handedness_stabilizer import HandednessStabilizer


class TestHandednessStabilizer(unittest.TestCase):
    def setUp(self):
        self.stabilizer = HandednessStabilizer(window_size=7, switch_threshold=0.65)

    def test_initial_handedness(self):
        h, conf = self.stabilizer.update(Handedness.RIGHT, 0.95)
        self.assertEqual(h, Handedness.RIGHT)
        self.assertGreaterEqual(conf, 0.90)

    def test_single_frame_flip_rejected(self):
        # Establish RIGHT hand for 5 frames
        for _ in range(5):
            self.stabilizer.update(Handedness.RIGHT, 0.95)

        # Single frame glitch to LEFT
        h, conf = self.stabilizer.update(Handedness.LEFT, 0.60)
        self.assertEqual(h, Handedness.RIGHT, "Single-frame glitch to LEFT must be rejected")

        # Next frame returns to RIGHT
        h, conf = self.stabilizer.update(Handedness.RIGHT, 0.95)
        self.assertEqual(h, Handedness.RIGHT)

    def test_sustained_transition(self):
        # Establish RIGHT hand
        for _ in range(7):
            self.stabilizer.update(Handedness.RIGHT, 0.90)

        # Sustained LEFT hand for 6 frames should trigger transition
        final_h = None
        for _ in range(6):
            final_h, _ = self.stabilizer.update(Handedness.LEFT, 0.95)

        self.assertEqual(final_h, Handedness.LEFT, "Sustained LEFT classification should switch state")


if __name__ == "__main__":
    unittest.main()
