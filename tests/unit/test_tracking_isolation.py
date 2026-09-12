"""
Unit tests for Phase 14.2 Tracking Identity & State Isolation Fix.

Verifies:
A. One hand remains RIGHT.
B. One hand remains LEFT.
C. Two simultaneous hands (RIGHT + LEFT) maintain independent handedness.
D. Handedness histories do not cross-contaminate.
E. Landmark filters do not cross-contaminate (no coordinate jumping).
F. Persistent hand_id across MediaPipe detection order swaps.
G. Temporary hand loss (track survives short dropout).
H. Long hand loss (track expires and all state is purged).
I. Fresh hand after expiration receives a clean state.
"""

from __future__ import annotations

import unittest
from typing import List

from core.models import Handedness
from tracking.hand_state import BoundingBox, Landmark
from tracking.landmark_normalizer import LandmarkNormalizer
from tracking.temporal_tracker import RawHandCandidate, TemporalHandTracker, TrackState


def _make_candidate(
    cx: float,
    cy: float,
    handedness: Handedness,
    confidence: float = 0.95,
) -> RawHandCandidate:
    """Helper to generate a synthetic RawHandCandidate around center (cx, cy)."""
    # Create 21 synthetic landmarks offset from (cx, cy)
    landmarks = [
        Landmark(id=i, x=max(0.0, min(1.0, cx + (i - 10) * 0.002)), y=max(0.0, min(1.0, cy + (i - 10) * 0.002)), z=0.0)
        for i in range(21)
    ]
    bbox = BoundingBox(left=cx - 0.05, top=cy - 0.05, right=cx + 0.05, bottom=cy + 0.05, width=0.10, height=0.10)
    return RawHandCandidate(
        raw_landmarks=landmarks,
        raw_handedness=handedness,
        raw_confidence=confidence,
        bounding_box=bbox,
        palm_center=(cx, cy, 0.0),
        hand_center=(cx, cy, 0.0),
    )


class TestTrackingIsolation(unittest.TestCase):
    """Test suite for per-hand handedness, landmark filter isolation, and temporal identity."""

    def setUp(self) -> None:
        self.tracker = TemporalHandTracker(
            max_lost_time=0.30,
            max_missed_frames=8,
            gating_distance=0.35,
            window_size=7,
            switch_threshold=0.65,
        )

    def test_single_hand_remains_right(self) -> None:
        """Test A: A single right hand consistently classifies as RIGHT across frames."""
        t = 1.0
        for frame in range(10):
            t += 0.033
            cand = _make_candidate(cx=0.3, cy=0.5, handedness=Handedness.RIGHT, confidence=0.95)
            states = self.tracker.update([cand], t)
            self.assertEqual(len(states), 1)
            self.assertEqual(states[0].handedness, Handedness.RIGHT)

    def test_single_hand_remains_left(self) -> None:
        """Test B: A single left hand consistently classifies as LEFT across frames."""
        t = 1.0
        for frame in range(10):
            t += 0.033
            cand = _make_candidate(cx=0.7, cy=0.5, handedness=Handedness.LEFT, confidence=0.95)
            states = self.tracker.update([cand], t)
            self.assertEqual(len(states), 1)
            self.assertEqual(states[0].handedness, Handedness.LEFT)

    def test_two_simultaneous_hands_right_and_left(self) -> None:
        """Test C: Two simultaneous hands (RIGHT at x=0.20, LEFT at x=0.80) retain their respective handedness."""
        t = 1.0
        for frame in range(15):
            t += 0.033
            cand_r = _make_candidate(cx=0.20, cy=0.5, handedness=Handedness.RIGHT, confidence=0.95)
            cand_l = _make_candidate(cx=0.80, cy=0.5, handedness=Handedness.LEFT, confidence=0.95)
            states = self.tracker.update([cand_r, cand_l], t)
            self.assertEqual(len(states), 2)
            
            # Find the state for x=0.20 and x=0.80
            state_r = next(s for s in states if s.palm_center[0] < 0.5)
            state_l = next(s for s in states if s.palm_center[0] > 0.5)

            self.assertEqual(state_r.handedness, Handedness.RIGHT)
            self.assertEqual(state_l.handedness, Handedness.LEFT)

    def test_handedness_histories_do_not_contaminate(self) -> None:
        """Test D: Voting history of Track A does not bias or corrupt voting history of Track B."""
        t = 1.0
        # Initialize Track A (RIGHT at x=0.25) and Track B (LEFT at x=0.75)
        for frame in range(5):
            t += 0.033
            cand_r = _make_candidate(cx=0.25, cy=0.5, handedness=Handedness.RIGHT, confidence=0.95)
            cand_l = _make_candidate(cx=0.75, cy=0.5, handedness=Handedness.LEFT, confidence=0.95)
            states = self.tracker.update([cand_r, cand_l], t)

        track_ids = [s.hand_id for s in states]
        track_a = self.tracker._tracks[track_ids[0]]
        track_b = self.tracker._tracks[track_ids[1]]

        # Verify each track has its own stabilizer history
        history_a = [h for h, _ in track_a.handedness_stabilizer._history]
        history_b = [h for h, _ in track_b.handedness_stabilizer._history]

        self.assertTrue(all(h == Handedness.RIGHT for h in history_a))
        self.assertTrue(all(h == Handedness.LEFT for h in history_b))

    def test_landmark_filters_do_not_cross_contaminate(self) -> None:
        """Test E: Coordinate filtering for Hand A at x=0.20 does not pull Hand B at x=0.80 toward x=0.20."""
        t = 1.0
        # Feed 10 frames of two stationary hands
        for frame in range(10):
            t += 0.033
            cand_a = _make_candidate(cx=0.20, cy=0.5, handedness=Handedness.RIGHT)
            cand_b = _make_candidate(cx=0.80, cy=0.5, handedness=Handedness.LEFT)
            states = self.tracker.update([cand_a, cand_b], t)

        state_a = next(s for s in states if s.palm_center[0] < 0.5)
        state_b = next(s for s in states if s.palm_center[0] > 0.5)

        # Hand A Index TIP (landmark 8) must remain near 0.20, Hand B Index TIP must remain near 0.80
        self.assertAlmostEqual(state_a.landmarks[8].x, 0.20, delta=0.02)
        self.assertAlmostEqual(state_b.landmarks[8].x, 0.80, delta=0.02)

    def test_detection_order_swap_preserves_physical_hand_identity(self) -> None:
        """Test F: When MediaPipe swaps candidate list order, internal hand_ids remain bound to physical hands."""
        t = 1.0
        # Frame 1: MediaPipe outputs Hand A (x=0.20) first, Hand B (x=0.80) second
        cand_a = _make_candidate(cx=0.20, cy=0.5, handedness=Handedness.RIGHT)
        cand_b = _make_candidate(cx=0.80, cy=0.5, handedness=Handedness.LEFT)
        states_1 = self.tracker.update([cand_a, cand_b], t)

        id_a = next(s.hand_id for s in states_1 if s.palm_center[0] < 0.5)
        id_b = next(s.hand_id for s in states_1 if s.palm_center[0] > 0.5)
        self.assertNotEqual(id_a, id_b)

        # Frame 2: MediaPipe SWAPS the output order: Hand B (x=0.80) first, Hand A (x=0.20) second
        t += 0.033
        cand_b_swapped = _make_candidate(cx=0.81, cy=0.5, handedness=Handedness.LEFT)
        cand_a_swapped = _make_candidate(cx=0.21, cy=0.5, handedness=Handedness.RIGHT)
        states_2 = self.tracker.update([cand_b_swapped, cand_a_swapped], t)

        id_a_swapped = next(s.hand_id for s in states_2 if s.palm_center[0] < 0.5)
        id_b_swapped = next(s.hand_id for s in states_2 if s.palm_center[0] > 0.5)

        # Hand IDs must persist with their physical locations
        self.assertEqual(id_a_swapped, id_a)
        self.assertEqual(id_b_swapped, id_b)

    def test_temporary_hand_loss_survival(self) -> None:
        """Test G: Track survives short missing interval (e.g. 2 frames) and maintains hand_id upon return."""
        t = 1.0
        cand = _make_candidate(cx=0.3, cy=0.5, handedness=Handedness.RIGHT)
        states_1 = self.tracker.update([cand], t)
        initial_id = states_1[0].hand_id

        # Missing for 2 frames
        t += 0.033
        self.tracker.update([], t)
        t += 0.033
        self.tracker.update([], t)

        # Verify track is marked TEMPORARILY_LOST
        self.assertIn(initial_id, self.tracker._tracks)
        self.assertEqual(self.tracker._tracks[initial_id].state, TrackState.TEMPORARILY_LOST)
        self.assertEqual(self.tracker._tracks[initial_id].missed_frames, 2)

        # Hand reappears near same position
        t += 0.033
        cand_return = _make_candidate(cx=0.32, cy=0.5, handedness=Handedness.RIGHT)
        states_recovered = self.tracker.update([cand_return], t)

        self.assertEqual(len(states_recovered), 1)
        self.assertEqual(states_recovered[0].hand_id, initial_id)
        self.assertEqual(self.tracker._tracks[initial_id].state, TrackState.ACTIVE)

    def test_long_hand_loss_expires_and_cleans_up(self) -> None:
        """Test H: Track expires after max_lost_time (>0.30s) and is completely purged."""
        t = 1.0
        cand = _make_candidate(cx=0.3, cy=0.5, handedness=Handedness.RIGHT)
        states = self.tracker.update([cand], t)
        initial_id = states[0].hand_id

        # Advance time by 0.5 seconds with no detections
        t += 0.50
        self.tracker.update([], t)

        # Verify track has been removed completely
        self.assertNotIn(initial_id, self.tracker._tracks)
        self.assertEqual(self.tracker.active_track_count, 0)

    def test_new_hand_appears_after_expiration_receives_fresh_state(self) -> None:
        """Test I: New hand appearing after expiration gets fresh state."""
        t = 1.0
        # Hand 1 appears at x=0.3
        cand1 = _make_candidate(cx=0.3, cy=0.5, handedness=Handedness.RIGHT)
        states1 = self.tracker.update([cand1], t)
        id1 = states1[0].hand_id

        # Hand 1 disappears and expires
        t += 0.50
        self.tracker.update([], t)
        self.assertEqual(self.tracker.active_track_count, 0)

        # New Hand appears at x=0.7 (LEFT)
        t += 0.033
        cand2 = _make_candidate(cx=0.7, cy=0.5, handedness=Handedness.LEFT)
        states2 = self.tracker.update([cand2], t)

        self.assertEqual(len(states2), 1)
        self.assertEqual(states2[0].handedness, Handedness.LEFT)
        # Verify track has fresh 1-element history
        new_track = self.tracker._tracks[states2[0].hand_id]
        self.assertEqual(len(new_track.handedness_stabilizer._history), 1)


if __name__ == "__main__":
    unittest.main()
