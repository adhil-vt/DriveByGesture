"""
tests.unit.test_thumbs_down
===========================
Unit tests for ThumbsDownGesture implementation.
"""

import unittest
from unittest.mock import MagicMock

from analysis.finger_state import FingerName, FingerPosition, FingerState, HandAnalysis
from core.models import Handedness
from gestures.builtins.thumbs_down import ThumbsDownGesture


def make_hand_analysis(
    thumb_pos=FingerPosition.EXTENDED,
    index_pos=FingerPosition.CURLED,
    middle_pos=FingerPosition.CURLED,
    ring_pos=FingerPosition.CURLED,
    pinky_pos=FingerPosition.CURLED,
    confidence=0.9,
    handedness=Handedness.RIGHT,
    timestamp=100.0,
    thumb_vertical="DOWN",
):
    analysis = MagicMock(spec=HandAnalysis)
    analysis.timestamp = timestamp
    analysis.hand_state = MagicMock()
    analysis.hand_state.handedness = handedness

    # Mock 21 landmarks
    lms = [MagicMock(x=0.5, y=0.5, z=0.0) for _ in range(21)]
    lms[2].y = 0.5
    lms[4].y = 0.9 if thumb_vertical == "DOWN" else (0.1 if thumb_vertical == "UP" else 0.5)
    analysis.hand_state.landmarks = lms

    analysis.thumb = FingerState(name=FingerName.THUMB, position=thumb_pos, confidence=confidence)
    analysis.index = FingerState(name=FingerName.INDEX, position=index_pos, confidence=confidence)
    analysis.middle = FingerState(name=FingerName.MIDDLE, position=middle_pos, confidence=confidence)
    analysis.ring = FingerState(name=FingerName.RING, position=ring_pos, confidence=confidence)
    analysis.pinky = FingerState(name=FingerName.PINKY, position=pinky_pos, confidence=confidence)
    return analysis


class TestThumbsDownGesture(unittest.TestCase):
    def setUp(self):
        self.gesture = ThumbsDownGesture()

    def test_thumbs_down_gesture(self):
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.EXTENDED,
            index_pos=FingerPosition.CURLED,
            middle_pos=FingerPosition.CURLED,
            ring_pos=FingerPosition.CURLED,
            pinky_pos=FingerPosition.CURLED,
            confidence=0.95,
        )
        res = self.gesture.recognize(hand)
        self.assertEqual(res.gesture_name, "Thumbs Down")
        self.assertTrue(res.detected)
        self.assertGreaterEqual(res.confidence, 0.90)

    def test_thumbs_up_orientation_fails(self):
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.EXTENDED,
            index_pos=FingerPosition.CURLED,
            middle_pos=FingerPosition.CURLED,
            ring_pos=FingerPosition.CURLED,
            pinky_pos=FingerPosition.CURLED,
            thumb_vertical="UP",
        )
        res = self.gesture.recognize(hand)
        self.assertFalse(res.detected)
        self.assertEqual(res.rejection_reason, "Thumb not pointing down")


if __name__ == "__main__":
    unittest.main()
