"""
tests.unit.test_open_palm
=========================
Unit tests for OpenPalmGesture implementation.
"""

import unittest
from unittest.mock import MagicMock

from analysis.finger_state import FingerName, FingerPosition, FingerState, HandAnalysis
from core.models import Handedness
from gestures.builtins.open_palm import OpenPalmGesture


def make_hand_analysis(
    thumb_pos=FingerPosition.EXTENDED,
    index_pos=FingerPosition.EXTENDED,
    middle_pos=FingerPosition.EXTENDED,
    ring_pos=FingerPosition.EXTENDED,
    pinky_pos=FingerPosition.EXTENDED,
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


class TestOpenPalmGesture(unittest.TestCase):
    def setUp(self):
        self.gesture = OpenPalmGesture()

    def test_open_palm_fully_extended(self):
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.EXTENDED,
            index_pos=FingerPosition.EXTENDED,
            middle_pos=FingerPosition.EXTENDED,
            ring_pos=FingerPosition.EXTENDED,
            pinky_pos=FingerPosition.EXTENDED,
            confidence=0.95,
        )
        res = self.gesture.recognize(hand)
        self.assertEqual(res.gesture_name, "Open Palm")
        self.assertTrue(res.detected)
        self.assertGreaterEqual(res.confidence, 0.90)
        self.assertEqual(res.handedness, "RIGHT")

    def test_nearly_open_palm_thumb_partially_bent(self):
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.PARTIALLY_BENT,
            index_pos=FingerPosition.EXTENDED,
            middle_pos=FingerPosition.EXTENDED,
            ring_pos=FingerPosition.EXTENDED,
            pinky_pos=FingerPosition.EXTENDED,
            confidence=0.9,
        )
        res = self.gesture.recognize(hand)
        self.assertTrue(res.detected)
        self.assertGreater(res.confidence, 0.70)

    def test_nearly_open_palm_index_partially_bent(self):
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.EXTENDED,
            index_pos=FingerPosition.PARTIALLY_BENT,
            middle_pos=FingerPosition.EXTENDED,
            ring_pos=FingerPosition.EXTENDED,
            pinky_pos=FingerPosition.EXTENDED,
            confidence=0.9,
        )
        res = self.gesture.recognize(hand)
        self.assertTrue(res.detected)
        self.assertGreater(res.confidence, 0.70)

    def test_closed_fist_must_fail(self):
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

    def test_point_gesture_must_fail(self):
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.CURLED,
            index_pos=FingerPosition.EXTENDED,
            middle_pos=FingerPosition.CURLED,
            ring_pos=FingerPosition.CURLED,
            pinky_pos=FingerPosition.CURLED,
        )
        res = self.gesture.recognize(hand)
        self.assertFalse(res.detected)
        self.assertEqual(res.confidence, 0.0)

    def test_peace_gesture_must_fail(self):
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
