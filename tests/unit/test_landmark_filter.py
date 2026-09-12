"""
tests.unit.test_landmark_filter
================================
Unit tests for OneEuroFilter and HandLandmarkFilter.
"""

import unittest
from tracking.hand_state import Landmark
from tracking.landmark_filter import HandLandmarkFilter, OneEuroFilter


class TestLandmarkFilter(unittest.TestCase):
    def setUp(self):
        self.one_euro = OneEuroFilter(min_cutoff=1.0, beta=0.007, d_cutoff=1.0)
        self.hand_filter = HandLandmarkFilter(min_cutoff=1.0, beta=0.007, d_cutoff=1.0)

    def test_one_euro_filter_initialization(self):
        val = self.one_euro.filter(0.5, timestamp=1.0)
        self.assertEqual(val, 0.5)

    def test_one_euro_filter_smoothing_noisy_signal(self):
        ts = 1.0
        outputs = []
        # Noisy signal oscillating around 0.50
        noisy_inputs = [0.50, 0.52, 0.48, 0.51, 0.49, 0.52, 0.48]
        for val in noisy_inputs:
            ts += 0.033
            outputs.append(self.one_euro.filter(val, ts))

        # Check variance of outputs vs inputs
        input_variance = sum((x - 0.50) ** 2 for x in noisy_inputs)
        output_variance = sum((x - 0.50) ** 2 for x in outputs)
        self.assertLess(output_variance, input_variance, "Filtered output must have lower variance than noisy input")

    def test_hand_landmark_filter(self):
        lms = [Landmark(id=i, x=0.5, y=0.5, z=0.0) for i in range(21)]
        filtered = self.hand_filter.filter_landmarks(lms, timestamp=1.0)
        self.assertEqual(len(filtered), 21)
        self.assertEqual(filtered[0].x, 0.5)


if __name__ == "__main__":
    unittest.main()
