"""
tests/unit/test_pinch_pinky.py
===============================
Unit tests for PinchPinkyGesture (Thumb + Pinky Pinch for Right Click).
"""

import pytest
from unittest.mock import MagicMock

from analysis.finger_state import FingerName, FingerPosition, FingerState, HandAnalysis
from core.models import Handedness
from gestures.builtins.pinch_pinky import PinchPinkyGesture
from tracking.hand_state import Landmark


def create_mock_hand_state(thumb_tip_pos, pinky_tip_pos, index_tip_pos=(0.8, 0.8, 0.0)):
    landmarks = [Landmark(i, 0.5, 0.5, 0.0) for i in range(21)]
    landmarks[0] = Landmark(0, 0.5, 0.7, 0.0)    # Wrist
    landmarks[4] = Landmark(4, *thumb_tip_pos)   # Thumb Tip
    landmarks[5] = Landmark(5, 0.5, 0.5, 0.0)    # Index MCP
    landmarks[8] = Landmark(8, *index_tip_pos)   # Index Tip
    landmarks[9] = Landmark(9, 0.5, 0.4, 0.0)    # Middle MCP
    landmarks[17] = Landmark(17, 0.6, 0.5, 0.0)  # Pinky MCP
    landmarks[20] = Landmark(20, *pinky_tip_pos) # Pinky Tip

    analysis = MagicMock(spec=HandAnalysis)
    analysis.timestamp = 1.0
    analysis.hand_state = MagicMock()
    analysis.hand_state.handedness = Handedness.RIGHT
    analysis.hand_state.landmarks = landmarks

    analysis.thumb = FingerState(FingerName.THUMB, FingerPosition.EXTENDED, 0.9)
    analysis.index = FingerState(FingerName.INDEX, FingerPosition.EXTENDED, 0.9)
    analysis.middle = FingerState(FingerName.MIDDLE, FingerPosition.EXTENDED, 0.9)
    analysis.ring = FingerState(FingerName.RING, FingerPosition.EXTENDED, 0.9)
    analysis.pinky = FingerState(FingerName.PINKY, FingerPosition.EXTENDED, 0.9)
    return analysis


def test_pinch_pinky_detection_success():
    # Thumb tip and Pinky tip touching (distance ~0), Index tip far away
    analysis = create_mock_hand_state(
        thumb_tip_pos=(0.50, 0.50, 0.0),
        pinky_tip_pos=(0.50, 0.50, 0.0),
        index_tip_pos=(0.80, 0.80, 0.0),
    )
    gesture = PinchPinkyGesture()
    result = gesture.recognize(analysis)

    assert result.detected, "PinchPinkyGesture should detect when thumb and pinky tips touch"
    assert result.confidence > 0.80, f"Expected high confidence, got {result.confidence}"
    assert result.gesture_name == "Pinch Pinky"


def test_pinch_pinky_rejected_when_index_pinching():
    # Thumb tip and Index tip close together (Normal Left Click Pinch active)
    analysis = create_mock_hand_state(
        thumb_tip_pos=(0.49, 0.49, 0.0),
        pinky_tip_pos=(0.51, 0.51, 0.0),
        index_tip_pos=(0.50, 0.50, 0.0),  # Index tip also close to thumb
    )
    gesture = PinchPinkyGesture()
    result = gesture.recognize(analysis)

    assert not result.detected, "PinchPinkyGesture must fail when Index Pinch is active"
    assert result.rejection_reason == "Index tip too close to thumb (Index Pinch active)"
