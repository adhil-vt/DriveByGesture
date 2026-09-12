"""
tests.unit.test_tracking_stability_correction
==============================================
Comprehensive validation tests for Phase 14.2 Tracking Stability & State Correction:
1. Cold-start handedness gate and confirmation
2. FingerAnalyzer per-hand state isolation by hand_id and expired track cleanup
3. Deterministic primary-hand selection policy
"""

import unittest
from collections import deque
from typing import List

from core.models import Handedness
from analysis.finger_analyzer import FingerAnalyzer
from analysis.finger_state import FingerName, FingerPosition
from tracking.hand_selection import select_primary_hand, select_primary_hand_index
from tracking.hand_state import BoundingBox, HandState, Landmark
from tracking.handedness_stabilizer import HandednessStabilizer


def _create_mock_landmarks(flexed_fingers: List[FingerName] = None) -> List[Landmark]:
    """Helper to create valid 21 3D landmarks with customizable finger curl positions."""
    flexed = flexed_fingers or []
    landmarks = []
    # 0: Wrist
    landmarks.append(Landmark(id=0, x=0.5, y=0.8, z=0.0))

    # Thumb: 1, 2, 3, 4
    if FingerName.THUMB in flexed:
        landmarks.extend([
            Landmark(id=1, x=0.45, y=0.70, z=0.0),
            Landmark(id=2, x=0.43, y=0.65, z=0.0),
            Landmark(id=3, x=0.46, y=0.62, z=0.0),
            Landmark(id=4, x=0.48, y=0.60, z=0.0),  # curled towards palm
        ])
    else:
        landmarks.extend([
            Landmark(id=1, x=0.45, y=0.70, z=0.0),
            Landmark(id=2, x=0.40, y=0.65, z=0.0),
            Landmark(id=3, x=0.35, y=0.60, z=0.0),
            Landmark(id=4, x=0.30, y=0.55, z=0.0),  # extended
        ])

    # 4 standard fingers: Index (5-8), Middle (9-12), Ring (13-16), Pinky (17-20)
    bases = [
        (FingerName.INDEX, 0.45),
        (FingerName.MIDDLE, 0.50),
        (FingerName.RING, 0.55),
        (FingerName.PINKY, 0.60),
    ]

    for finger, base_x in bases:
        if finger in flexed:
            # Curled: MCP -> PIP -> DIP -> TIP folded at 90 degrees
            landmarks.append(Landmark(id=len(landmarks), x=base_x, y=0.55, z=0.0))   # MCP
            landmarks.append(Landmark(id=len(landmarks), x=base_x, y=0.45, z=0.0))   # PIP
            landmarks.append(Landmark(id=len(landmarks), x=base_x, y=0.45, z=0.10))  # DIP (90 deg angle)
            landmarks.append(Landmark(id=len(landmarks), x=base_x, y=0.55, z=0.10))  # TIP (90 deg angle)
        else:
            # Extended: straight upwards
            landmarks.append(Landmark(id=len(landmarks), x=base_x, y=0.55, z=0.0))   # MCP
            landmarks.append(Landmark(id=len(landmarks), x=base_x, y=0.45, z=0.0))   # PIP
            landmarks.append(Landmark(id=len(landmarks), x=base_x, y=0.35, z=0.0))   # DIP
            landmarks.append(Landmark(id=len(landmarks), x=base_x, y=0.25, z=0.0))   # TIP


    return landmarks


def _create_mock_hand_state(
    hand_id: int,
    handedness: Handedness,
    flexed_fingers: List[FingerName] = None,
    palm_x: float = 0.5,
) -> HandState:
    lms = _create_mock_landmarks(flexed_fingers)
    bbox = BoundingBox(left=palm_x - 0.1, top=0.3, right=palm_x + 0.1, bottom=0.8, width=0.2, height=0.5)
    return HandState(
        handedness=handedness,
        confidence=0.95,
        landmarks=lms,
        bounding_box=bbox,
        palm_center=(palm_x, 0.6, 0.0),
        hand_center=(palm_x, 0.5, 0.0),
        timestamp=1.0,
        hand_id=hand_id,
    )


class TestTrackingStabilityCorrection(unittest.TestCase):

    # ── TEST A — Cold-Start Handedness ────────────────────────────────────────

    def test_cold_start_handedness_bad_first_frame_not_latched(self):
        """
        Verify that a single noisy/incorrect first frame does NOT lock the stabilizer,
        allowing subsequent high-confidence matching frames to establish the correct state immediately.
        """
        stabilizer = HandednessStabilizer(window_size=7, switch_threshold=0.65, min_confirm_frames=2)
        self.assertFalse(stabilizer.is_confirmed)

        # Frame 1: Glitch / bad entry frame reports LEFT (0.60)
        h1, c1 = stabilizer.update(Handedness.LEFT, 0.60)
        self.assertFalse(stabilizer.is_confirmed, "Single initial observation must remain unconfirmed")
        self.assertEqual(h1, Handedness.LEFT)

        # Frame 2: True hand classification RIGHT (0.92)
        h2, c2 = stabilizer.update(Handedness.RIGHT, 0.92)
        self.assertFalse(stabilizer.is_confirmed, "Mismatched observations must not confirm")
        self.assertEqual(h2, Handedness.RIGHT)

        # Frame 3: Second consecutive RIGHT (0.95) -> Confirms RIGHT!
        h3, c3 = stabilizer.update(Handedness.RIGHT, 0.95)
        self.assertTrue(stabilizer.is_confirmed, "Two consecutive RIGHT observations must confirm")
        self.assertEqual(h3, Handedness.RIGHT)

    # ── TEST B — Handedness Confirmation ──────────────────────────────────────

    def test_two_consecutive_matching_observations_confirm_handedness(self):
        """
        Verify two consecutive matching observations confirm the new hand.
        """
        stabilizer = HandednessStabilizer(window_size=7, switch_threshold=0.65, min_confirm_frames=2)

        # Frame 1: First RIGHT
        stabilizer.update(Handedness.RIGHT, 0.90)
        self.assertFalse(stabilizer.is_confirmed)

        # Frame 2: Second matching RIGHT
        h2, c2 = stabilizer.update(Handedness.RIGHT, 0.94)
        self.assertTrue(stabilizer.is_confirmed)
        self.assertEqual(h2, Handedness.RIGHT)
        self.assertAlmostEqual(c2, 0.92, places=2)

    # ── TEST C — Finger History Isolation ─────────────────────────────────────

    def test_finger_history_isolated_by_hand_id(self):
        """
        Create hand_id 0 and hand_id 1 with different finger flex states.
        Verify their histories never affect each other.
        """
        analyzer = FingerAnalyzer()

        # Hand 0 has extended Index finger
        hand0 = _create_mock_hand_state(hand_id=0, handedness=Handedness.RIGHT, flexed_fingers=[])
        # Hand 1 has curled Index finger
        hand1 = _create_mock_hand_state(hand_id=1, handedness=Handedness.LEFT, flexed_fingers=[FingerName.INDEX])

        # Analyze both hands over 5 frames
        for _ in range(5):
            res0 = analyzer.analyze(hand0)
            res1 = analyzer.analyze(hand1)

            self.assertEqual(res0.index.position, FingerPosition.EXTENDED)
            self.assertEqual(res1.index.position, FingerPosition.CURLED)

        # Verify internal histories are strictly keyed by (hand_id, FingerName)
        key0 = (0, FingerName.INDEX)
        key1 = (1, FingerName.INDEX)

        self.assertIn(key0, analyzer._history)
        self.assertIn(key1, analyzer._history)
        self.assertTrue(all(pos == FingerPosition.EXTENDED for pos in analyzer._history[key0]))
        self.assertTrue(all(pos == FingerPosition.CURLED for pos in analyzer._history[key1]))

    # ── TEST D — Handedness Transition with Same Hand ID ──────────────────────

    def test_handedness_transition_preserves_hand_id_finger_history(self):
        """
        If a tracked hand changes raw handedness, verify finger history remains
        attached to the same hand_id without creating ghost state or resets.
        """
        analyzer = FingerAnalyzer()

        # Initial frames: Hand ID 42 classified as RIGHT with curled Middle finger
        hand_r = _create_mock_hand_state(hand_id=42, handedness=Handedness.RIGHT, flexed_fingers=[FingerName.MIDDLE])
        for _ in range(3):
            res_r = analyzer.analyze(hand_r)
            self.assertEqual(res_r.middle.position, FingerPosition.CURLED)

        # Later frame: Hand ID 42 transitioned to LEFT (same physical hand track)
        hand_l = _create_mock_hand_state(hand_id=42, handedness=Handedness.LEFT, flexed_fingers=[FingerName.MIDDLE])
        res_l = analyzer.analyze(hand_l)
        self.assertEqual(res_l.middle.position, FingerPosition.CURLED)

        # History should still be keyed on hand_id=42
        key = (42, FingerName.MIDDLE)
        self.assertIn(key, analyzer._history)
        self.assertEqual(len(analyzer._history[key]), 4)

    # ── TEST E — Expired Hand Cleanup ─────────────────────────────────────────

    def test_expired_hand_cleanup(self):
        """
        Create a track, populate finger history, expire the track, and verify
        its finger history is completely removed.
        """
        analyzer = FingerAnalyzer()

        # Populate history for hand 10 and hand 20
        hand10 = _create_mock_hand_state(hand_id=10, handedness=Handedness.RIGHT)
        hand20 = _create_mock_hand_state(hand_id=20, handedness=Handedness.LEFT)

        analyzer.analyze(hand10)
        analyzer.analyze(hand20)

        self.assertIn((10, FingerName.INDEX), analyzer._history)
        self.assertIn((20, FingerName.INDEX), analyzer._history)

        # Expire hand 10 (only hand 20 remains active)
        analyzer.cleanup_expired_hands(active_hand_ids=[20])

        self.assertNotIn((10, FingerName.INDEX), analyzer._history)
        self.assertNotIn((10, FingerName.INDEX), analyzer._prev_state)
        self.assertIn((20, FingerName.INDEX), analyzer._history)
        self.assertIn((20, FingerName.INDEX), analyzer._prev_state)

        # Single hand cleanup
        analyzer.cleanup_hand(hand_id=20)
        self.assertNotIn((20, FingerName.INDEX), analyzer._history)
        self.assertNotIn((20, FingerName.INDEX), analyzer._prev_state)

    # ── TEST F — Primary Hand Selection Policy ────────────────────────────────

    def test_primary_hand_selection(self):
        """
        Validate primary hand selection rules:
        - 1 hand -> select that hand
        - 2 hands with preferred RIGHT -> select RIGHT
        - 2 hands with preferred LEFT -> select LEFT
        - Preferred hand absent -> deterministic fallback to lowest stable hand_id
        """
        hand_l0 = _create_mock_hand_state(hand_id=0, handedness=Handedness.LEFT)
        hand_r1 = _create_mock_hand_state(hand_id=1, handedness=Handedness.RIGHT)
        hand_l2 = _create_mock_hand_state(hand_id=2, handedness=Handedness.LEFT)
        hand_l5 = _create_mock_hand_state(hand_id=5, handedness=Handedness.LEFT)

        # 1. Single hand present -> immediately selected regardless of preference
        self.assertEqual(select_primary_hand([hand_l0], preferred_hand="right").hand_id, 0)
        self.assertEqual(select_primary_hand([hand_r1], preferred_hand="left").hand_id, 1)

        # 2. Both hands present, preferred RIGHT -> select RIGHT (hand_id 1)
        two_hands = [hand_l0, hand_r1]
        self.assertEqual(select_primary_hand(two_hands, preferred_hand="right").hand_id, 1)

        # 3. Both hands present, preferred LEFT -> select LEFT (hand_id 0)
        self.assertEqual(select_primary_hand(two_hands, preferred_hand="left").hand_id, 0)

        # 4. Preferred hand absent: two LEFT hands (hand_id 5 and hand_id 2), preferred RIGHT
        # Fallback to lowest hand_id -> hand_id 2
        two_lefts = [hand_l5, hand_l2]
        self.assertEqual(select_primary_hand(two_lefts, preferred_hand="right").hand_id, 2)

    # ── TEST G — Detection Order Independence ─────────────────────────────────

    def test_detection_order_swap_preserves_primary_selection(self):
        """
        Swap MediaPipe detection order and verify primary selection remains invariant.
        """
        hand_l0 = _create_mock_hand_state(hand_id=0, handedness=Handedness.LEFT)
        hand_r1 = _create_mock_hand_state(hand_id=1, handedness=Handedness.RIGHT)

        order_a = [hand_l0, hand_r1]
        order_b = [hand_r1, hand_l0]

        # Preferred RIGHT
        res_a = select_primary_hand(order_a, preferred_hand="right")
        res_b = select_primary_hand(order_b, preferred_hand="right")
        self.assertEqual(res_a.hand_id, 1)
        self.assertEqual(res_b.hand_id, 1)

        # Preferred LEFT
        res_a_l = select_primary_hand(order_a, preferred_hand="left")
        res_b_l = select_primary_hand(order_b, preferred_hand="left")
        self.assertEqual(res_a_l.hand_id, 0)
        self.assertEqual(res_b_l.hand_id, 0)


if __name__ == "__main__":
    unittest.main()
