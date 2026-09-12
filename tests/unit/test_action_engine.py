"""
tests.unit.test_action_engine
==============================
Unit tests for ActionEngine, ActionState, and Action models.
"""

import unittest
from unittest.mock import MagicMock

from actions.action import Action, ActionType
from actions.action_engine import ActionEngine
from actions.action_state import ActionState
from actions.config import ActionEngineConfig
from analysis.finger_state import HandAnalysis
from gestures.gesture_result import GestureResult
from tracking.hand_state import HandState, Landmark


def make_gesture_result(name: str, detected: bool = True, confidence: float = 0.90) -> GestureResult:
    return GestureResult(
        gesture_name=name,
        detected=detected,
        confidence=confidence,
        timestamp=1.0,
        handedness="RIGHT",
    )


def make_hand_analysis(dx: float = 0.0, dy: float = -0.20) -> HandAnalysis:
    hand = MagicMock(spec=HandAnalysis)
    hand.hand_state = MagicMock(spec=HandState)
    hand.hand_state.handedness = MagicMock()
    hand.hand_state.handedness.name = "RIGHT"

    wrist = Landmark(id=0, x=0.5, y=0.8, z=0.0)
    middle_mcp = Landmark(id=9, x=0.5 + dx, y=0.8 + dy, z=0.0)
    hand.hand_state.landmarks = [wrist] + [Landmark(id=i, x=0.5, y=0.5, z=0.0) for i in range(1, 9)] + [middle_mcp] + [Landmark(id=i, x=0.5, y=0.5, z=0.0) for i in range(10, 21)]

    return hand


class TestActionEngine(unittest.TestCase):
    def setUp(self):
        self.config = ActionEngineConfig(max_steering_angle=30.0, steering_deadzone=0.05)
        self.engine = ActionEngine(config=self.config)

    def test_open_palm_to_accelerator(self):
        res = make_gesture_result("Open Palm")
        state = self.engine.process([res])

        self.assertTrue(state.accelerator)
        self.assertFalse(state.brake)
        self.assertFalse(state.handbrake)
        self.assertTrue(state.has_action(ActionType.ACCELERATOR))
        self.assertEqual(state.get_action(ActionType.ACCELERATOR).value, 1.0)

    def test_fist_to_brake(self):
        res = make_gesture_result("Fist")
        state = self.engine.process([res])

        self.assertFalse(state.accelerator)
        self.assertTrue(state.brake)
        self.assertFalse(state.handbrake)
        self.assertTrue(state.has_action(ActionType.BRAKE))

    def test_pinch_to_handbrake(self):
        res = make_gesture_result("Pinch")
        state = self.engine.process([res])

        self.assertFalse(state.accelerator)
        self.assertFalse(state.brake)
        self.assertTrue(state.handbrake)
        self.assertTrue(state.has_action(ActionType.HANDBRAKE))

    def test_steering_normalization_and_center(self):
        # Upright hand (dx=0.0, dy=-0.20) -> Center steering = 0.0
        hand_center = make_hand_analysis(dx=0.0, dy=-0.20)
        state = self.engine.process([], [hand_center])
        self.assertEqual(state.steering, 0.0)

    def test_steering_right_tilt(self):
        # Physical tilt right -> hand moves to camera left (middle_mcp.x - wrist.x = -0.10 -> dx = wrist.x - middle_mcp.x = +0.10)
        hand_right = make_hand_analysis(dx=-0.10, dy=-0.20)
        state = self.engine.process([], [hand_right])
        self.assertGreater(state.steering, 0.50)
        self.assertLessEqual(state.steering, 1.0)
        self.assertTrue(state.has_action(ActionType.STEERING))

    def test_steering_left_tilt(self):
        # Physical tilt left -> hand moves to camera right (middle_mcp.x - wrist.x = +0.10 -> dx = wrist.x - middle_mcp.x = -0.10)
        hand_left = make_hand_analysis(dx=0.10, dy=-0.20)
        state = self.engine.process([], [hand_left])
        self.assertLess(state.steering, -0.50)
        self.assertGreaterEqual(state.steering, -1.0)

    def test_steering_deadzone_handling(self):
        # Slight micro-tilt within deadzone threshold -> 0.0
        hand_slight = make_hand_analysis(dx=0.005, dy=-0.20)
        state = self.engine.process([], [hand_slight])
        self.assertEqual(state.steering, 0.0)

    def test_invalid_and_unmapped_gestures(self):
        # Unknown gesture or undetected result -> empty action state
        res_unknown = make_gesture_result("Unknown", detected=False)
        res_unmapped = make_gesture_result("UnregisteredCustomGesture")

        state1 = self.engine.process([res_unknown])
        self.assertFalse(state1.accelerator)
        self.assertFalse(state1.brake)

        state2 = self.engine.process([res_unmapped])
        self.assertFalse(state2.accelerator)
        self.assertFalse(state2.brake)


if __name__ == "__main__":
    unittest.main()
