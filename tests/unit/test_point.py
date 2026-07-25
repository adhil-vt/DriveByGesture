"""
tests.unit.test_point
=====================
Unit tests for PointGesture implementation.
"""

import unittest
from unittest.mock import MagicMock

from analysis.finger_state import FingerName, FingerPosition, FingerState, HandAnalysis
from core.models import Handedness
from gestures.builtins.point import PointGesture


def make_hand_analysis(
    thumb_pos=FingerPosition.CURLED,
    index_pos=FingerPosition.EXTENDED,
    middle_pos=FingerPosition.CURLED,
    ring_pos=FingerPosition.CURLED,
    pinky_pos=FingerPosition.CURLED,
    confidence=0.9,
    handedness=Handedness.RIGHT,
    timestamp=100.0,
):
    analysis = MagicMock(spec=HandAnalysis)
    analysis.timestamp = timestamp
    analysis.hand_state = MagicMock()
    analysis.hand_state.handedness = handedness

    analysis.thumb = FingerState(name=FingerName.THUMB, position=thumb_pos, confidence=confidence)
    analysis.index = FingerState(name=FingerName.INDEX, position=index_pos, confidence=confidence)
    analysis.middle = FingerState(name=FingerName.MIDDLE, position=middle_pos, confidence=confidence)
    analysis.ring = FingerState(name=FingerName.RING, position=ring_pos, confidence=confidence)
    analysis.pinky = FingerState(name=FingerName.PINKY, position=pinky_pos, confidence=confidence)
    return analysis


class TestPointGesture(unittest.TestCase):
    def setUp(self):
        self.gesture = PointGesture()

    def test_point_gesture(self):
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.CURLED,
            index_pos=FingerPosition.EXTENDED,
            middle_pos=FingerPosition.CURLED,
            ring_pos=FingerPosition.CURLED,
            pinky_pos=FingerPosition.CURLED,
            confidence=0.95,
        )
        res = self.gesture.recognize(hand)
        self.assertEqual(res.gesture_name, "Point")
        self.assertTrue(res.detected)
        self.assertGreaterEqual(res.confidence, 0.90)
        self.assertEqual(res.handedness, "RIGHT")

    def test_point_gesture_thumb_extended_or_partially_bent(self):
        # Thumb state should not affect Point detection success
        hand_thumb_ext = make_hand_analysis(thumb_pos=FingerPosition.EXTENDED)
        hand_thumb_bent = make_hand_analysis(thumb_pos=FingerPosition.PARTIALLY_BENT)

        res_ext = self.gesture.recognize(hand_thumb_ext)
        res_bent = self.gesture.recognize(hand_thumb_bent)

        self.assertTrue(res_ext.detected)
        self.assertTrue(res_bent.detected)

    def test_slightly_relaxed_point_index_partially_bent(self):
        hand = make_hand_analysis(
            index_pos=FingerPosition.PARTIALLY_BENT,
            middle_pos=FingerPosition.CURLED,
            ring_pos=FingerPosition.CURLED,
            pinky_pos=FingerPosition.CURLED,
            confidence=0.9,
        )
        res = self.gesture.recognize(hand)
        self.assertTrue(res.detected)
        self.assertGreater(res.confidence, 0.70)

    def test_slightly_relaxed_point_one_other_finger_partially_bent(self):
        hand = make_hand_analysis(
            index_pos=FingerPosition.EXTENDED,
            middle_pos=FingerPosition.PARTIALLY_BENT,
            ring_pos=FingerPosition.CURLED,
            pinky_pos=FingerPosition.CURLED,
            confidence=0.9,
        )
        res = self.gesture.recognize(hand)
        self.assertTrue(res.detected)

    def test_open_palm_must_fail(self):
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.EXTENDED,
            index_pos=FingerPosition.EXTENDED,
            middle_pos=FingerPosition.EXTENDED,
            ring_pos=FingerPosition.EXTENDED,
            pinky_pos=FingerPosition.EXTENDED,
        )
        res = self.gesture.recognize(hand)
        self.assertFalse(res.detected)
        self.assertEqual(res.confidence, 0.0)

    def test_fist_must_fail(self):
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.CURLED,
            index_pos=FingerPosition.CURLED,
            middle_pos=FingerPosition.CURLED,
            ring_pos=FingerPosition.CURLED,
            pinky_pos=FingerPosition.CURLED,
        )
        res = self.gesture.recognize(hand)
        self.assertFalse(res.detected)
        self.assertEqual(res.confidence, 0.0)

    def test_peace_must_fail(self):
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.CURLED,
            index_pos=FingerPosition.EXTENDED,
            middle_pos=FingerPosition.EXTENDED,
            ring_pos=FingerPosition.CURLED,
            pinky_pos=FingerPosition.CURLED,
        )
        res = self.gesture.recognize(hand)
        self.assertFalse(res.detected)
        self.assertEqual(res.confidence, 0.0)

    def test_pinch_must_fail(self):
        # Pinch: Thumb and Index close together while Middle/Ring/Pinky extended or curled with middle extended
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.EXTENDED,
            index_pos=FingerPosition.EXTENDED,
            middle_pos=FingerPosition.EXTENDED,
            ring_pos=FingerPosition.CURLED,
            pinky_pos=FingerPosition.CURLED,
        )
        res = self.gesture.recognize(hand)
        self.assertFalse(res.detected)
        self.assertEqual(res.confidence, 0.0)

    def test_left_and_right_handedness(self):
        left_hand = make_hand_analysis(handedness=Handedness.LEFT)
        right_hand = make_hand_analysis(handedness=Handedness.RIGHT)

        res_left = self.gesture.recognize(left_hand)
        res_right = self.gesture.recognize(right_hand)

        self.assertTrue(res_left.detected)
        self.assertEqual(res_left.handedness, "LEFT")

        self.assertTrue(res_right.detected)
        self.assertEqual(res_right.handedness, "RIGHT")


if __name__ == "__main__":
    unittest.main()
