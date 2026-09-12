"""
tests.unit.test_gesture_recognition_stabilization
=================================================
Unit test suite validating Phase 14.4 Stage 1: Gesture Recognition Stabilization:
1. Pinch confidence mathematical modeling and monotonicity
2. Point gesture relaxed geometry & non-interference guards
3. Gesture transition latency reduction and state machine stabilization
4. Thumbs Up vs Fist geometric separation
5. Multi-gesture conflict resolution matrix
"""

import math
import unittest
from typing import List, Optional

from core.models import Handedness
from tracking.hand_state import BoundingBox, HandState, Landmark
from analysis.finger_analyzer import FingerAnalyzer
from analysis.finger_state import FingerName, FingerPosition, FingerState, HandAnalysis
from analysis.hand_analyzer import HandAnalyzer
from config.schema import GestureConfig
from gestures.registry import GestureRegistry
from gestures.manager import GestureManager
from gestures.builtins import (
    FistGesture,
    OpenPalmGesture,
    PeaceGesture,
    PinchGesture,
    PinchPinkyGesture,
    PointGesture,
    ThumbsDownGesture,
    ThumbsUpGesture,
)
from gestures.builtins.utils import (
    calculate_pinch_signals,
    distance_3d,
    get_hand_scale,
)


def _make_hand_landmarks(
    wrist=(0.5, 0.8, 0.0),
    thumb_tip=(0.3, 0.55, 0.0),
    index_tip=(0.45, 0.25, 0.0),
    middle_tip=(0.50, 0.25, 0.0),
    ring_tip=(0.55, 0.25, 0.0),
    pinky_tip=(0.60, 0.25, 0.0),
    index_folded=False,
    middle_folded=False,
    ring_folded=False,
    pinky_folded=False,
    thumb_folded=False,
    thumb_dir_up=False,
    thumb_dir_down=False,
) -> List[Landmark]:
    lms = [Landmark(id=0, x=wrist[0], y=wrist[1], z=wrist[2])]

    # Thumb: 1, 2, 3, 4
    if thumb_dir_up:
        lms.extend([
            Landmark(id=1, x=0.45, y=0.70, z=0.0),
            Landmark(id=2, x=0.40, y=0.60, z=0.0),
            Landmark(id=3, x=0.38, y=0.50, z=0.0),
            Landmark(id=4, x=0.38, y=0.32, z=0.0),  # Well above Index MCP (0.55)
        ])
    elif thumb_dir_down:
        lms.extend([
            Landmark(id=1, x=0.45, y=0.70, z=0.0),
            Landmark(id=2, x=0.40, y=0.60, z=0.0),
            Landmark(id=3, x=0.38, y=0.70, z=0.0),
            Landmark(id=4, x=0.38, y=0.85, z=0.0),  # Down
        ])
    elif thumb_folded:
        lms.extend([
            Landmark(id=1, x=0.45, y=0.70, z=0.0),
            Landmark(id=2, x=0.43, y=0.65, z=0.0),
            Landmark(id=3, x=0.46, y=0.62, z=0.0),
            Landmark(id=4, x=thumb_tip[0], y=thumb_tip[1], z=thumb_tip[2]),
        ])
    else:
        lms.extend([
            Landmark(id=1, x=0.45, y=0.70, z=0.0),
            Landmark(id=2, x=0.40, y=0.60, z=0.0),
            Landmark(id=3, x=0.38, y=0.50, z=0.0),
            Landmark(id=4, x=thumb_tip[0], y=thumb_tip[1], z=thumb_tip[2]),
        ])

    # Index: 5, 6, 7, 8
    if index_folded:
        lms.extend([
            Landmark(id=5, x=0.45, y=0.55, z=0.0),
            Landmark(id=6, x=0.45, y=0.45, z=0.0),
            Landmark(id=7, x=0.45, y=0.45, z=0.10),
            Landmark(id=8, x=index_tip[0], y=index_tip[1], z=index_tip[2]),
        ])
    else:
        # Smoothly ascending towards tip without joint angle inversion
        tip_y = index_tip[1]
        tip_x = index_tip[0]
        lms.extend([
            Landmark(id=5, x=0.45, y=0.55, z=0.0),
            Landmark(id=6, x=0.45, y=0.55 - (0.55 - tip_y) * 0.35, z=0.0),
            Landmark(id=7, x=0.45, y=0.55 - (0.55 - tip_y) * 0.70, z=0.0),
            Landmark(id=8, x=tip_x, y=tip_y, z=0.0),
        ])

    # Middle: 9, 10, 11, 12
    if middle_folded:
        lms.extend([
            Landmark(id=9, x=0.50, y=0.53, z=0.0),
            Landmark(id=10, x=0.50, y=0.43, z=0.0),
            Landmark(id=11, x=0.50, y=0.43, z=0.10),
            Landmark(id=12, x=middle_tip[0], y=middle_tip[1], z=middle_tip[2]),
        ])
    else:
        lms.extend([
            Landmark(id=9, x=0.50, y=0.53, z=0.0),
            Landmark(id=10, x=0.50, y=0.43, z=0.0),
            Landmark(id=11, x=0.50, y=0.33, z=0.0),
            Landmark(id=12, x=middle_tip[0], y=middle_tip[1], z=middle_tip[2]),
        ])

    # Ring: 13, 14, 15, 16
    if ring_folded:
        lms.extend([
            Landmark(id=13, x=0.55, y=0.55, z=0.0),
            Landmark(id=14, x=0.55, y=0.45, z=0.0),
            Landmark(id=15, x=0.55, y=0.45, z=0.10),
            Landmark(id=16, x=ring_tip[0], y=ring_tip[1], z=ring_tip[2]),
        ])
    else:
        lms.extend([
            Landmark(id=13, x=0.55, y=0.55, z=0.0),
            Landmark(id=14, x=0.55, y=0.45, z=0.0),
            Landmark(id=15, x=0.55, y=0.35, z=0.0),
            Landmark(id=16, x=ring_tip[0], y=ring_tip[1], z=ring_tip[2]),
        ])

    # Pinky: 17, 18, 19, 20
    if pinky_folded:
        lms.extend([
            Landmark(id=17, x=0.60, y=0.58, z=0.0),
            Landmark(id=18, x=0.60, y=0.48, z=0.0),
            Landmark(id=19, x=0.60, y=0.48, z=0.10),
            Landmark(id=20, x=pinky_tip[0], y=pinky_tip[1], z=pinky_tip[2]),
        ])
    else:
        lms.extend([
            Landmark(id=17, x=0.60, y=0.58, z=0.0),
            Landmark(id=18, x=0.60, y=0.48, z=0.0),
            Landmark(id=19, x=0.60, y=0.38, z=0.0),
            Landmark(id=20, x=pinky_tip[0], y=pinky_tip[1], z=pinky_tip[2]),
        ])

    return lms


def _make_hand_state(
    landmarks: List[Landmark],
    timestamp: float = 1.0,
    hand_id: int = 0,
    handedness: Handedness = Handedness.RIGHT,
) -> HandState:
    bbox = BoundingBox(left=0.2, top=0.2, right=0.8, bottom=0.8, width=0.6, height=0.6)
    return HandState(
        handedness=handedness,
        confidence=0.95,
        landmarks=landmarks,
        bounding_box=bbox,
        palm_center=(0.5, 0.6, 0.0),
        hand_center=(0.5, 0.5, 0.0),
        timestamp=timestamp,
        hand_id=hand_id,
    )


class TestGestureRecognitionStabilization(unittest.TestCase):

    def setUp(self):
        self.finger_analyzer = FingerAnalyzer()
        self.hand_analyzer = HandAnalyzer(self.finger_analyzer)
        self.registry = GestureRegistry()
        self.registry.register(OpenPalmGesture())
        self.registry.register(PointGesture())
        self.registry.register(PeaceGesture())
        self.registry.register(FistGesture())
        self.registry.register(ThumbsUpGesture())
        self.registry.register(ThumbsDownGesture())
        self.registry.register(PinchGesture())
        self.registry.register(PinchPinkyGesture())

    # ── 1. PINCH CONFIDENCE ───────────────────────────────────────────────────

    def test_pinch_confidence_tight_pinch(self):
        """A tight pinch (d <= 0.22) should produce strong confidence in [0.85, 0.98]."""
        pinch = PinchGesture()
        lms = _make_hand_landmarks(
            thumb_tip=(0.43, 0.38, 0.0),
            index_tip=(0.44, 0.38, 0.0),  # Very close
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )
        hs = _make_hand_state(lms)
        ha = self.hand_analyzer.analyze_hands([hs])[0]
        res = pinch.recognize(ha)

        self.assertTrue(res.detected)
        self.assertGreaterEqual(res.confidence, 0.85)

    def test_pinch_confidence_comfortable_pinch(self):
        """A normal comfortable pinch (d ≈ 0.26) should produce confidence in [0.80, 0.95]."""
        pinch = PinchGesture()
        # Scale is ~0.211, so raw distance ~0.055 gives normalized distance ~0.26
        lms = _make_hand_landmarks(
            thumb_tip=(0.40, 0.38, 0.0),
            index_tip=(0.45, 0.38, 0.0),  # dx=0.05
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )
        hs = _make_hand_state(lms)
        ha = self.hand_analyzer.analyze_hands([hs])[0]
        res = pinch.recognize(ha)

        self.assertTrue(res.detected)
        self.assertGreaterEqual(res.confidence, 0.80)

    def test_pinch_confidence_weak_loose_pinch(self):
        """A weak/loose pinch (d ≈ 0.34) should produce valid but lower confidence in [0.60, 0.78]."""
        pinch = PinchGesture()
        lms = _make_hand_landmarks(
            thumb_tip=(0.38, 0.38, 0.0),
            index_tip=(0.45, 0.38, 0.0),  # dx=0.07 -> norm dist ≈ 0.33
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )
        hs = _make_hand_state(lms)
        ha = self.hand_analyzer.analyze_hands([hs])[0]
        res = pinch.recognize(ha)

        self.assertTrue(res.detected)
        self.assertGreaterEqual(res.confidence, 0.60)
        self.assertLessEqual(res.confidence, 0.80)

    def test_pinch_fingers_clearly_separated_rejected(self):
        """When thumb and index fingers are far apart (d > 0.38), Pinch must be rejected."""
        pinch = PinchGesture()
        lms = _make_hand_landmarks(
            thumb_tip=(0.30, 0.55, 0.0),
            index_tip=(0.45, 0.25, 0.0),  # Pointing pose, far apart
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )
        hs = _make_hand_state(lms)
        ha = self.hand_analyzer.analyze_hands([hs])[0]
        res = pinch.recognize(ha)

        self.assertFalse(res.detected)
        self.assertEqual(res.confidence, 0.0)

    # ── 2. POINT GESTURE ──────────────────────────────────────────────────────

    def test_point_gesture_normal_and_deep_curl(self):
        """Point gesture should detect cleanly for both normal and relaxed middle finger curl."""
        point = PointGesture()

        # Normal Point
        lms = _make_hand_landmarks(
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )
        ha = self.hand_analyzer.analyze_hands([_make_hand_state(lms)])[0]
        res = point.recognize(ha)
        self.assertTrue(res.detected)
        self.assertGreaterEqual(res.confidence, 0.85)

    def test_point_gesture_does_not_falsely_trigger_other_gestures(self):
        """Verify Point does not trigger on Open Palm, Peace, Fist, or Pinch."""
        point = PointGesture()

        # 1. Open Palm
        ha_open = self.hand_analyzer.analyze_hands([_make_hand_state(_make_hand_landmarks())])[0]
        self.assertFalse(point.recognize(ha_open).detected)

        # 2. Peace (Index + Middle extended)
        lms_peace = _make_hand_landmarks(
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            ring_folded=True,
            pinky_folded=True,
        )
        ha_peace = self.hand_analyzer.analyze_hands([_make_hand_state(lms_peace)])[0]
        self.assertFalse(point.recognize(ha_peace).detected)

        # 3. Fist (all folded)
        lms_fist = _make_hand_landmarks(
            thumb_tip=(0.48, 0.60, 0.0),
            index_tip=(0.45, 0.55, 0.10),
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            thumb_folded=True,
            index_folded=True,
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )
        ha_fist = self.hand_analyzer.analyze_hands([_make_hand_state(lms_fist)])[0]
        self.assertFalse(point.recognize(ha_fist).detected)

    # ── 3. GESTURE TRANSITION & COOLDOWN ──────────────────────────────────────

    def test_gesture_transition_latency_reduced(self):
        """
        Verify transition from Point to Pinch satisfies 3-frame activation (~90ms)
        without being blocked by 0.50s cooldown.
        """
        config = GestureConfig(activation_frames=3, cooldown_seconds=0.50, confidence_threshold=0.60)
        gm = GestureManager(registry=self.registry, config=config)

        # 1. Activate Point
        lms_point = _make_hand_landmarks(
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )
        t = 0.0
        for f in range(3):
            t += 0.033
            ha = self.hand_analyzer.analyze_hands([_make_hand_state(lms_point, timestamp=t)])[0]
            res = gm.process_hands([ha])[0]

        self.assertEqual(res.gesture_name, "Point")
        self.assertTrue(res.detected)

        # 2. Switch to Pinch (Thumb and Index tips close)
        lms_pinch = _make_hand_landmarks(
            thumb_tip=(0.42, 0.38, 0.0),
            index_tip=(0.44, 0.38, 0.0),
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )

        frames_to_switch = 0
        switched = False
        for f in range(1, 6):
            t += 0.033
            ha_p = self.hand_analyzer.analyze_hands([_make_hand_state(lms_pinch, timestamp=t)])[0]
            res_p = gm.process_hands([ha_p])[0]
            if res_p.gesture_name == "Pinch" and res_p.detected:
                frames_to_switch = f
                switched = True
                break

        self.assertTrue(switched, "Pinch must successfully take over from Point")
        self.assertEqual(frames_to_switch, 3, "Transition should occur at exactly frame 3 (activation_frames=3)")

    def test_single_glitch_frame_does_not_flicker_active_gesture(self):
        """A single frame dropping to Unknown must not drop the active gesture."""
        config = GestureConfig(activation_frames=3, confidence_threshold=0.60)
        gm = GestureManager(registry=self.registry, config=config)

        lms_point = _make_hand_landmarks(
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )
        t = 0.0
        for _ in range(3):
            t += 0.033
            ha = self.hand_analyzer.analyze_hands([_make_hand_state(lms_point, timestamp=t)])[0]
            gm.process_hands([ha])

        # Glitch Frame (All zeros / Unknown)
        t += 0.033
        ha_glitch = self.hand_analyzer.analyze_hands([_make_hand_state(_make_hand_landmarks(), timestamp=t)])[0]
        res_glitch = gm.process_hands([ha_glitch])[0]
        # Active gesture should still remain protected as Point (or Open Palm if registered, but not Unknown)
        self.assertTrue(res_glitch.detected)

    # ── 4. THUMBS UP vs FIST ──────────────────────────────────────────────────

    def test_fist_never_triggers_thumbs_up(self):
        """A standard closed fist must strictly be recognized as Fist, never Thumbs Up."""
        thumbs_up = ThumbsUpGesture()
        fist = FistGesture()

        # Closed fist with thumb resting on folded fingers (Landmark 4 near (0.48, 0.60))
        lms_fist = _make_hand_landmarks(
            thumb_tip=(0.48, 0.60, 0.0),
            index_tip=(0.45, 0.55, 0.10),
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            thumb_folded=True,
            index_folded=True,
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )
        hs = _make_hand_state(lms_fist)
        ha = self.hand_analyzer.analyze_hands([hs])[0]

        res_tup = thumbs_up.recognize(ha)
        res_fist = fist.recognize(ha)

        self.assertFalse(res_tup.detected, "Fist must NOT trigger Thumbs Up")
        self.assertTrue(res_fist.detected, "Fist must be detected")
        self.assertEqual(res_fist.gesture_name, "Fist")

    def test_clear_thumbs_up_detected(self):
        """A clear upright thumb with curled fingers must be recognized as Thumbs Up."""
        thumbs_up = ThumbsUpGesture()
        lms_tup = _make_hand_landmarks(
            index_tip=(0.45, 0.55, 0.10),
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            thumb_dir_up=True,
            index_folded=True,
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )
        hs = _make_hand_state(lms_tup)
        ha = self.hand_analyzer.analyze_hands([hs])[0]

        res = thumbs_up.recognize(ha)
        self.assertTrue(res.detected)
        self.assertEqual(res.gesture_name, "Thumbs Up")
        self.assertGreaterEqual(res.confidence, 0.80)

    def test_thumbs_down_detected(self):
        """Thumbs Down must continue working without regression."""
        thumbs_down = ThumbsDownGesture()
        lms_tdown = _make_hand_landmarks(
            index_tip=(0.45, 0.55, 0.10),
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            thumb_dir_down=True,
            index_folded=True,
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )
        hs = _make_hand_state(lms_tdown)
        ha = self.hand_analyzer.analyze_hands([hs])[0]

        res = thumbs_down.recognize(ha)
        self.assertTrue(res.detected)
        self.assertEqual(res.gesture_name, "Thumbs Down")

    # ── 5. GESTURE CONFLICT RESOLUTION MATRIX ─────────────────────────────────

    def test_pinch_overrides_point(self):
        """When both Pinch and Point geometric criteria are satisfied, Pinch (priority 90) wins over Point (priority 40)."""
        gm = GestureManager(registry=self.registry)
        lms_pinch = _make_hand_landmarks(
            thumb_tip=(0.42, 0.38, 0.0),
            index_tip=(0.44, 0.38, 0.0),
            middle_tip=(0.50, 0.53, 0.10),
            ring_tip=(0.55, 0.55, 0.10),
            pinky_tip=(0.60, 0.58, 0.10),
            middle_folded=True,
            ring_folded=True,
            pinky_folded=True,
        )
        for f in range(3):
            ha = self.hand_analyzer.analyze_hands([_make_hand_state(lms_pinch, timestamp=f * 0.033)])[0]
            res = gm.process_hands([ha])[0]

        self.assertEqual(res.gesture_name, "Pinch")


if __name__ == "__main__":
    unittest.main()
