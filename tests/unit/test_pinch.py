"""
tests.unit.test_pinch
=====================
Unit tests for natural PinchGesture implementation.
"""

import unittest
from unittest.mock import MagicMock

from config.schema import GestureConfig
from analysis.finger_state import FingerName, FingerPosition, FingerState, HandAnalysis
from core.models import Handedness
from gestures.builtins.pinch import PinchGesture
from tracking.hand_state import Landmark


def make_landmark(id_, x, y, z=0.0):
    return Landmark(id=id_, x=x, y=y, z=z)


def make_21_landmarks(scale=1.0, thumb_index_sep=0.02):
    """
    Generate 21 MediaPipe landmark points.
    scale controls camera distance / hand size.
    thumb_index_sep controls distance between thumb tip (4) and index tip (8).
    """
    landmarks = []
    # 0: Wrist
    landmarks.append(make_landmark(0, 0.5 * scale, 0.8 * scale, 0.0))

    # 1-4: Thumb (4 is tip)
    landmarks.append(make_landmark(1, 0.45 * scale, 0.75 * scale, 0.0))
    landmarks.append(make_landmark(2, 0.42 * scale, 0.70 * scale, 0.0))
    landmarks.append(make_landmark(3, 0.40 * scale, 0.65 * scale, 0.0))
    landmarks.append(make_landmark(4, 0.42 * scale, 0.50 * scale, 0.0))

    # 5-8: Index (5 is MCP, 7 is DIP, 8 is tip)
    landmarks.append(make_landmark(5, 0.45 * scale, 0.60 * scale, 0.0))
    landmarks.append(make_landmark(6, 0.44 * scale, 0.55 * scale, 0.0))
    landmarks.append(make_landmark(7, 0.43 * scale, 0.52 * scale, 0.0))
    landmarks.append(make_landmark(8, 0.42 * scale, (0.50 + thumb_index_sep) * scale, 0.0))

    # 9-12: Middle (9 is MCP)
    landmarks.append(make_landmark(9, 0.50 * scale, 0.60 * scale, 0.0))
    landmarks.append(make_landmark(10, 0.50 * scale, 0.65 * scale, 0.0))
    landmarks.append(make_landmark(11, 0.50 * scale, 0.70 * scale, 0.0))
    landmarks.append(make_landmark(12, 0.50 * scale, 0.75 * scale, 0.0))

    # 13-16: Ring
    landmarks.append(make_landmark(13, 0.55 * scale, 0.60 * scale, 0.0))
    landmarks.append(make_landmark(14, 0.55 * scale, 0.65 * scale, 0.0))
    landmarks.append(make_landmark(15, 0.55 * scale, 0.70 * scale, 0.0))
    landmarks.append(make_landmark(16, 0.55 * scale, 0.75 * scale, 0.0))

    # 17-20: Pinky (17 is MCP)
    landmarks.append(make_landmark(17, 0.60 * scale, 0.60 * scale, 0.0))
    landmarks.append(make_landmark(18, 0.60 * scale, 0.65 * scale, 0.0))
    landmarks.append(make_landmark(19, 0.60 * scale, 0.70 * scale, 0.0))
    landmarks.append(make_landmark(20, 0.60 * scale, 0.75 * scale, 0.0))

    return landmarks


def make_hand_analysis(
    thumb_pos=FingerPosition.PARTIALLY_BENT,
    index_pos=FingerPosition.PARTIALLY_BENT,
    middle_pos=FingerPosition.CURLED,
    ring_pos=FingerPosition.CURLED,
    pinky_pos=FingerPosition.CURLED,
    confidence=0.9,
    handedness=Handedness.RIGHT,
    timestamp=100.0,
    landmarks=None,
):
    analysis = MagicMock(spec=HandAnalysis)
    analysis.timestamp = timestamp
    analysis.hand_state = MagicMock()
    analysis.hand_state.handedness = handedness
    analysis.hand_state.landmarks = landmarks

    analysis.thumb = FingerState(name=FingerName.THUMB, position=thumb_pos, confidence=confidence)
    analysis.index = FingerState(name=FingerName.INDEX, position=index_pos, confidence=confidence)
    analysis.middle = FingerState(name=FingerName.MIDDLE, position=middle_pos, confidence=confidence)
    analysis.ring = FingerState(name=FingerName.RING, position=ring_pos, confidence=confidence)
    analysis.pinky = FingerState(name=FingerName.PINKY, position=pinky_pos, confidence=confidence)
    return analysis


class TestPinchGesture(unittest.TestCase):
    def setUp(self):
        self.gesture = PinchGesture()

    def test_natural_light_pinch_activates(self):
        # Light touch (thumb tip and index tip close together, relaxed fingers)
        lms = make_21_landmarks(scale=1.0, thumb_index_sep=0.03)
        hand = make_hand_analysis(landmarks=lms)

        res = self.gesture.recognize(hand)
        self.assertEqual(res.gesture_name, "Pinch")
        self.assertTrue(res.detected)
        self.assertGreaterEqual(res.confidence, 0.80)
        self.assertEqual(res.handedness, "RIGHT")

    def test_relaxed_remaining_fingers(self):
        # Middle finger EXTENDED, Ring & Pinky PARTIALLY_BENT (relaxed pose, not tight fist)
        lms = make_21_landmarks(scale=1.0, thumb_index_sep=0.04)
        hand = make_hand_analysis(
            middle_pos=FingerPosition.EXTENDED,
            ring_pos=FingerPosition.PARTIALLY_BENT,
            pinky_pos=FingerPosition.PARTIALLY_BENT,
            landmarks=lms,
        )
        res = self.gesture.recognize(hand)
        self.assertTrue(res.detected)

    def test_pinch_distance_scale_invariance(self):
        lms_far = make_21_landmarks(scale=0.5, thumb_index_sep=0.02)
        lms_close = make_21_landmarks(scale=2.0, thumb_index_sep=0.02)

        res_far = self.gesture.recognize(make_hand_analysis(landmarks=lms_far))
        res_close = self.gesture.recognize(make_hand_analysis(landmarks=lms_close))

        self.assertTrue(res_far.detected)
        self.assertTrue(res_close.detected)

    def test_open_palm_must_fail(self):
        # Ring and Pinky are EXTENDED
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.EXTENDED,
            index_pos=FingerPosition.EXTENDED,
            middle_pos=FingerPosition.EXTENDED,
            ring_pos=FingerPosition.EXTENDED,
            pinky_pos=FingerPosition.EXTENDED,
            landmarks=make_21_landmarks(scale=1.0, thumb_index_sep=0.35),
        )
        res = self.gesture.recognize(hand)
        self.assertFalse(res.detected)
        self.assertEqual(res.confidence, 0.0)

    def test_fist_must_fail(self):
        # Index is CURLED
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
        # Index and Middle EXTENDED, but tips far apart
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.CURLED,
            index_pos=FingerPosition.EXTENDED,
            middle_pos=FingerPosition.EXTENDED,
            ring_pos=FingerPosition.CURLED,
            pinky_pos=FingerPosition.CURLED,
            landmarks=make_21_landmarks(scale=1.0, thumb_index_sep=0.35),
        )
        res = self.gesture.recognize(hand)
        self.assertFalse(res.detected)
        self.assertEqual(res.confidence, 0.0)

    def test_point_must_fail(self):
        # Index EXTENDED, Thumb tip far from Index tip
        hand = make_hand_analysis(
            thumb_pos=FingerPosition.CURLED,
            index_pos=FingerPosition.EXTENDED,
            middle_pos=FingerPosition.CURLED,
            ring_pos=FingerPosition.CURLED,
            pinky_pos=FingerPosition.CURLED,
            landmarks=make_21_landmarks(scale=1.0, thumb_index_sep=0.40),
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
