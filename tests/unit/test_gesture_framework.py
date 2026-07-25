"""
tests.unit.test_gesture_framework
==================================
Unit tests for the modular Gesture Recognition Framework (gestures package).
Uses standard library unittest for execution compatibility without external dependencies.
"""

import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

from analysis.finger_state import HandAnalysis
from core.models import Handedness
from gestures.base import Gesture
from gestures.gesture_result import GestureResult
from gestures.recognizer import GestureRecognizer
from gestures.registry import GestureRegistry


class DummyGesture(Gesture):
    """Concrete test implementation of Gesture."""

    def __init__(
        self,
        name: str = "TestGesture",
        priority: int = 1,
        enabled: bool = True,
        detected: bool = True,
        confidence: float = 0.9,
    ) -> None:
        super().__init__(name=name, priority=priority, enabled=enabled)
        self.detected = detected
        self.confidence = confidence

    def recognize(self, hand_analysis: HandAnalysis) -> GestureResult:
        handedness = GestureRecognizer._extract_handedness(hand_analysis) or "RIGHT"
        return GestureResult(
            gesture_name=self.name,
            detected=self.detected,
            confidence=self.confidence,
            timestamp=getattr(hand_analysis, "timestamp", 100.0),
            handedness=handedness,
        )


class TestGestureBase(unittest.TestCase):
    def test_abc_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            Gesture(name="Abstract")  # type: ignore

    def test_gesture_properties_and_setters(self):
        g = DummyGesture(name="Fist", priority=5, enabled=True)
        self.assertEqual(g.name, "Fist")
        self.assertEqual(g.priority, 5)
        self.assertTrue(g.enabled)

        g.priority = 10
        g.enabled = False
        self.assertEqual(g.priority, 10)
        self.assertFalse(g.enabled)


class TestGestureResult(unittest.TestCase):
    def test_immutability(self):
        res = GestureResult(
            gesture_name="Peace",
            detected=True,
            confidence=0.95,
            timestamp=1.0,
            handedness="LEFT",
        )
        self.assertEqual(res.gesture_name, "Peace")
        self.assertTrue(res.detected)
        self.assertEqual(res.confidence, 0.95)
        self.assertEqual(res.timestamp, 1.0)
        self.assertEqual(res.handedness, "LEFT")

        with self.assertRaises(FrozenInstanceError):
            res.confidence = 0.5  # type: ignore

    def test_default_handedness_is_none(self):
        res = GestureResult(
            gesture_name="Point",
            detected=False,
            confidence=0.0,
            timestamp=2.0,
        )
        self.assertIsNone(res.handedness)


class TestGestureRegistry(unittest.TestCase):
    def test_register_and_get(self):
        registry = GestureRegistry()
        g1 = DummyGesture(name="G1")
        registry.register(g1)

        self.assertIn("G1", registry)
        self.assertEqual(len(registry), 1)
        self.assertIs(registry.get("G1"), g1)
        self.assertEqual(registry.get_all(), [g1])

    def test_duplicate_registration_raises(self):
        registry = GestureRegistry()
        g1 = DummyGesture(name="G1")
        g1_dup = DummyGesture(name="G1")

        registry.register(g1)
        with self.assertRaises(ValueError):
            registry.register(g1_dup)

    def test_unregister(self):
        registry = GestureRegistry()
        g1 = DummyGesture(name="G1")
        registry.register(g1)

        registry.unregister("G1")
        self.assertNotIn("G1", registry)
        self.assertEqual(len(registry), 0)

        # Unregister by instance
        registry.register(g1)
        registry.unregister(g1)
        self.assertNotIn("G1", registry)

    def test_unregister_non_existent_raises(self):
        registry = GestureRegistry()
        with self.assertRaises(KeyError):
            registry.unregister("Unknown")

    def test_enable_disable(self):
        registry = GestureRegistry()
        g1 = DummyGesture(name="G1", enabled=True)
        g2 = DummyGesture(name="G2", enabled=True)
        registry.register(g1)
        registry.register(g2)

        registry.disable("G1")
        self.assertFalse(g1.enabled)
        self.assertTrue(g2.enabled)

        registry.enable("G1")
        self.assertTrue(g1.enabled)

        registry.disable_all()
        self.assertFalse(g1.enabled)
        self.assertFalse(g2.enabled)

        registry.enable_all()
        self.assertTrue(g1.enabled)
        self.assertTrue(g2.enabled)


class TestGestureRecognizer(unittest.TestCase):
    def setUp(self):
        self.mock_hand_analysis = MagicMock(spec=HandAnalysis)
        self.mock_hand_analysis.timestamp = 123.456
        self.mock_hand_analysis.hand_state = MagicMock()
        self.mock_hand_analysis.hand_state.handedness = Handedness.RIGHT

    def test_no_gestures_registered_returns_unknown(self):
        recognizer = GestureRecognizer()
        results = recognizer.recognize([self.mock_hand_analysis])

        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.gesture_name, "Unknown")
        self.assertFalse(res.detected)
        self.assertEqual(res.confidence, 0.0)
        self.assertEqual(res.timestamp, self.mock_hand_analysis.timestamp)
        self.assertEqual(res.handedness, "RIGHT")

    def test_selects_detected_over_not_detected(self):
        registry = GestureRegistry()
        g_not_det = DummyGesture(name="NotDet", priority=100, detected=False, confidence=0.0)
        g_det = DummyGesture(name="Det", priority=1, detected=True, confidence=0.6)
        registry.register(g_not_det)
        registry.register(g_det)

        recognizer = GestureRecognizer(registry=registry)
        results = recognizer.recognize([self.mock_hand_analysis])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].gesture_name, "Det")
        self.assertTrue(results[0].detected)

    def test_selects_higher_confidence(self):
        registry = GestureRegistry()
        g_low_conf = DummyGesture(name="LowConf", priority=10, detected=True, confidence=0.7)
        g_high_conf = DummyGesture(name="HighConf", priority=10, detected=True, confidence=0.95)
        registry.register(g_low_conf)
        registry.register(g_high_conf)

        recognizer = GestureRecognizer(registry=registry)
        results = recognizer.recognize([self.mock_hand_analysis])

        self.assertEqual(results[0].gesture_name, "HighConf")
        self.assertEqual(results[0].confidence, 0.95)

    def test_selects_higher_priority_on_equal_confidence(self):
        registry = GestureRegistry()
        g_low_prio = DummyGesture(name="LowPrio", priority=10, detected=True, confidence=0.9)
        g_high_prio = DummyGesture(name="HighPrio", priority=50, detected=True, confidence=0.9)
        registry.register(g_low_prio)
        registry.register(g_high_prio)

        recognizer = GestureRecognizer(registry=registry)
        results = recognizer.recognize([self.mock_hand_analysis])

        self.assertEqual(results[0].gesture_name, "HighPrio")

    def test_ignores_disabled_gestures(self):
        registry = GestureRegistry()
        g_disabled = DummyGesture(name="Disabled", priority=100, enabled=False, detected=True, confidence=0.99)
        g_enabled = DummyGesture(name="Enabled", priority=10, enabled=True, detected=True, confidence=0.5)
        registry.register(g_disabled)
        registry.register(g_enabled)

        recognizer = GestureRecognizer(registry=registry)
        results = recognizer.recognize([self.mock_hand_analysis])

        self.assertEqual(results[0].gesture_name, "Enabled")

    def test_multiple_hands_returns_multiple_results(self):
        registry = GestureRegistry()
        registry.register(DummyGesture(name="Pinch", priority=1, detected=True, confidence=0.85))

        hand1 = self.mock_hand_analysis
        hand2 = MagicMock(spec=HandAnalysis)
        hand2.timestamp = 456.789
        hand2.hand_state = MagicMock()
        hand2.hand_state.handedness = Handedness.LEFT

        recognizer = GestureRecognizer(registry=registry)
        results = recognizer.recognize([hand1, hand2])

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].gesture_name, "Pinch")
        self.assertEqual(results[0].handedness, "RIGHT")
        self.assertEqual(results[1].gesture_name, "Pinch")
        self.assertEqual(results[1].handedness, "LEFT")


if __name__ == "__main__":
    unittest.main()
