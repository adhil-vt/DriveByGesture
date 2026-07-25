"""
tests.unit.test_gesture_manager
================================
Unit tests for GestureManager, ActiveGesture, and Conflict Resolution system.
"""

import unittest
from unittest.mock import MagicMock

from config.schema import GestureConfig
from analysis.finger_state import HandAnalysis
from core.models import Handedness
from gestures.base import Gesture
from gestures.gesture_result import GestureResult
from gestures.manager import ActiveGesture, GestureManager
from gestures.registry import GestureRegistry


class DummyGesture(Gesture):
    """Concrete test implementation of Gesture."""

    def __init__(
        self,
        name: str = "TestGesture",
        priority: int = 10,
        enabled: bool = True,
        detected: bool = True,
        confidence: float = 0.9,
    ) -> None:
        super().__init__(name=name, priority=priority, enabled=enabled)
        self.detected = detected
        self.confidence = confidence

    def recognize(self, hand_analysis: HandAnalysis) -> GestureResult:
        handedness = "RIGHT"
        if hasattr(hand_analysis, "hand_state") and hasattr(
            hand_analysis.hand_state, "handedness"
        ):
            h = hand_analysis.hand_state.handedness
            handedness = h.name if hasattr(h, "name") else str(h)

        return GestureResult(
            gesture_name=self.name,
            detected=self.detected,
            confidence=self.confidence,
            timestamp=getattr(hand_analysis, "timestamp", 100.0),
            handedness=handedness,
        )


def make_hand_analysis(handedness=Handedness.RIGHT, timestamp=100.0):
    analysis = MagicMock(spec=HandAnalysis)
    analysis.timestamp = timestamp
    analysis.hand_state = MagicMock()
    analysis.hand_state.handedness = handedness
    return analysis


class TestGestureManager(unittest.TestCase):
    def setUp(self):
        self.config = GestureConfig(
            activation_frames=3,
            cooldown_seconds=0.5,
            confidence_threshold=0.60,
        )
        self.registry = GestureRegistry()
        self.manager = GestureManager(registry=self.registry, config=self.config)

    def test_gesture_stabilization(self):
        # Requires 3 consecutive frames of candidate gesture to activate
        g1 = DummyGesture(name="Fist", priority=10, detected=True, confidence=0.85)
        self.registry.register(g1)

        hand = make_hand_analysis(timestamp=1.0)

        # Frame 1: Detected 1 frame, still Unknown active
        res1 = self.manager.process_hands([hand])[0]
        self.assertEqual(res1.gesture_name, "Unknown")
        active1 = self.manager.get_active_gesture("RIGHT")
        self.assertEqual(active1.current_gesture, "Unknown")
        self.assertEqual(active1.frames_stable, 0)

        # Frame 2: Detected 2 frames, still Unknown active
        res2 = self.manager.process_hands([hand])[0]
        self.assertEqual(res2.gesture_name, "Unknown")

        # Frame 3: Detected 3 frames -> ACTIVATES "Fist"!
        res3 = self.manager.process_hands([hand])[0]
        self.assertEqual(res3.gesture_name, "Fist")
        active3 = self.manager.get_active_gesture("RIGHT")
        self.assertEqual(active3.current_gesture, "Fist")
        self.assertEqual(active3.frames_stable, 3)

    def test_cooldown_enforcement(self):
        # Activation frames = 1, cooldown = 1.0s
        config = GestureConfig(activation_frames=1, cooldown_seconds=1.0, confidence_threshold=0.5)
        registry = GestureRegistry()
        g_fist = DummyGesture(name="Fist", priority=10, detected=True, confidence=0.9)
        g_point = DummyGesture(name="Point", priority=20, detected=True, confidence=0.95)
        registry.register(g_fist)

        mgr = GestureManager(registry=registry, config=config)
        hand = make_hand_analysis(timestamp=1.0)

        # Activate Fist at t=1.0s -> cooldown set until t=2.0s
        res1 = mgr.process_hands([hand])[0]
        self.assertEqual(res1.gesture_name, "Fist")

        # Now register Point (higher priority & confidence)
        registry.register(g_point)

        # Frame at t=1.2s (during cooldown of 1.0s): Point is candidate, but Fist remains active due to cooldown
        hand_t12 = make_hand_analysis(timestamp=1.2)
        res2 = mgr.process_hands([hand_t12])[0]
        self.assertEqual(res2.gesture_name, "Fist")

        # Frame at t=2.1s (after cooldown expires): Point activates!
        hand_t21 = make_hand_analysis(timestamp=2.1)
        res3 = mgr.process_hands([hand_t21])[0]
        self.assertEqual(res3.gesture_name, "Point")

    def test_confidence_threshold_filtering(self):
        # Confidence threshold = 0.70
        g_weak = DummyGesture(name="WeakPinch", priority=50, detected=True, confidence=0.50)
        self.registry.register(g_weak)

        hand = make_hand_analysis(timestamp=1.0)
        res = self.manager.process_hands([hand])[0]

        # Weak detection below 0.60 threshold must be filtered out -> Unknown
        self.assertEqual(res.gesture_name, "Unknown")
        self.assertFalse(res.detected)

    def test_conflict_resolution_determinism(self):
        # Register 3 valid gestures simultaneously:
        # G1: conf 0.85, prio 10
        # G2: conf 0.95, prio 5 (higher confidence)
        # G3: conf 0.95, prio 20 (equal confidence, higher priority)
        g1 = DummyGesture(name="G1", priority=10, detected=True, confidence=0.85)
        g2 = DummyGesture(name="G2", priority=5, detected=True, confidence=0.95)
        g3 = DummyGesture(name="G3", priority=20, detected=True, confidence=0.95)

        self.registry.register(g1)
        self.registry.register(g2)
        self.registry.register(g3)

        hand = make_hand_analysis(timestamp=1.0)
        winner = self.manager._resolve_conflict(hand)

        # Winner must be G3 (highest confidence + highest priority tie-breaker)
        self.assertEqual(winner.gesture_name, "G3")
        self.assertEqual(winner.confidence, 0.95)

    def test_multi_hand_recognition(self):
        config = GestureConfig(activation_frames=1, cooldown_seconds=0.0)
        registry = GestureRegistry()
        registry.register(DummyGesture(name="Fist", priority=10, detected=True, confidence=0.9))

        mgr = GestureManager(registry=registry, config=config)

        left_hand = make_hand_analysis(handedness=Handedness.LEFT, timestamp=1.0)
        right_hand = make_hand_analysis(handedness=Handedness.RIGHT, timestamp=1.0)

        results = mgr.process_hands([left_hand, right_hand])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].handedness, "LEFT")
        self.assertEqual(results[1].handedness, "RIGHT")

        active_left = mgr.get_active_gesture("LEFT")
        active_right = mgr.get_active_gesture("RIGHT")

        self.assertEqual(active_left.hand, "LEFT")
        self.assertEqual(active_right.hand, "RIGHT")
        self.assertEqual(active_left.current_gesture, "Fist")
        self.assertEqual(active_right.current_gesture, "Fist")

    def test_unknown_gesture_when_no_detection(self):
        hand = make_hand_analysis(timestamp=1.0)
        results = self.manager.process_hands([hand])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].gesture_name, "Unknown")
        self.assertFalse(results[0].detected)

    def test_debug_info_formatting(self):
        config = GestureConfig(activation_frames=1, cooldown_seconds=0.0)
        registry = GestureRegistry()
        registry.register(DummyGesture(name="Fist", priority=10, detected=True, confidence=0.96))

        mgr = GestureManager(registry=registry, config=config)

        left_hand = make_hand_analysis(handedness=Handedness.LEFT, timestamp=1.0)
        right_hand = make_hand_analysis(handedness=Handedness.RIGHT, timestamp=1.0)
        mgr.process_hands([left_hand, right_hand])

        debug_str = mgr.get_debug_info()
        self.assertIn("LEFT", debug_str)
        self.assertIn("RIGHT", debug_str)
        self.assertIn("Gesture: FIST", debug_str)
        self.assertIn("Confidence: 0.96", debug_str)
        self.assertIn("Frames Stable: 1", debug_str)
        self.assertIn("Cooldown: Ready", debug_str)
        self.assertIn("---------------------", debug_str)


if __name__ == "__main__":
    unittest.main()
