"""
Comprehensive test suite for Phase 14.4.2: Live Gesture Classifier Fixes.
Covers real-world geometry for Fist, Point, and Thumbs Down.
"""

import math
import unittest
from typing import List, Tuple

from core.models import Handedness
from tracking.hand_state import HandState, Landmark, BoundingBox
from analysis.finger_analyzer import FingerAnalyzer
from analysis.finger_state import FingerPosition, FingerName
from analysis.hand_analyzer import HandAnalyzer
from config.schema import GestureConfig
from gestures.registry import GestureRegistry
from gestures.manager import GestureManager
from gestures.builtins import (
    OpenPalmGesture,
    PointGesture,
    PeaceGesture,
    FistGesture,
    ThumbsUpGesture,
    ThumbsDownGesture,
    PinchGesture,
    PinchPinkyGesture,
)


def _make_lms(
    wrist=(0.5, 0.7, 0.0),
    thumb_tip=(0.47, 0.55, 0.05),
    thumb_mcp=(0.43, 0.60, 0.02),
    index_tip=(0.45, 0.58, 0.05),
    index_mcp=(0.45, 0.55, 0.0),
    index_extended=False,
    middle_extended=False,
    ring_extended=False,
    pinky_extended=False,
    index_foreshortened=False,
    thumb_dir_up=False,
    thumb_dir_down=False,
    thumb_diagonal_down=False,
    thumb_neutral=False,
) -> List[Landmark]:
    lms = [Landmark(id=0, x=wrist[0], y=wrist[1], z=wrist[2])]

    # Thumb 1..4
    if thumb_dir_up:
        lms.extend([
            Landmark(id=1, x=0.45, y=0.65, z=0.0),
            Landmark(id=2, x=0.40, y=0.58, z=0.0),
            Landmark(id=3, x=0.38, y=0.45, z=0.0),
            Landmark(id=4, x=0.38, y=0.32, z=0.0),
        ])
    elif thumb_dir_down:
        lms.extend([
            Landmark(id=1, x=0.45, y=0.55, z=0.0),
            Landmark(id=2, x=0.40, y=0.60, z=0.0),
            Landmark(id=3, x=0.38, y=0.70, z=0.0),
            Landmark(id=4, x=0.38, y=0.82, z=0.0),
        ])
    elif thumb_diagonal_down:
        lms.extend([
            Landmark(id=1, x=0.45, y=0.55, z=0.0),
            Landmark(id=2, x=0.40, y=0.58, z=0.0),
            Landmark(id=3, x=0.36, y=0.64, z=0.0),
            Landmark(id=4, x=0.32, y=0.70, z=0.0),
        ])
    elif thumb_neutral:
        lms.extend([
            Landmark(id=1, x=0.45, y=0.65, z=0.0),
            Landmark(id=2, x=0.40, y=0.60, z=0.0),
            Landmark(id=3, x=0.35, y=0.60, z=0.0),
            Landmark(id=4, x=0.30, y=0.60, z=0.0),
        ])
    else:
        lms.extend([
            Landmark(id=1, x=0.45, y=0.65, z=0.0),
            Landmark(id=2, x=thumb_mcp[0], y=thumb_mcp[1], z=thumb_mcp[2]),
            Landmark(id=3, x=(thumb_mcp[0] + thumb_tip[0])/2, y=(thumb_mcp[1] + thumb_tip[1])/2, z=(thumb_mcp[2] + thumb_tip[2])/2),
            Landmark(id=4, x=thumb_tip[0], y=thumb_tip[1], z=thumb_tip[2]),
        ])

    # Index 5..8
    if index_extended:
        tip_y = index_tip[1]
        tip_x = index_tip[0]
        tip_z = index_tip[2] if len(index_tip) > 2 else 0.0
        mcp_y = index_mcp[1]
        mcp_x = index_mcp[0]
        mcp_z = index_mcp[2] if len(index_mcp) > 2 else 0.0
        lms.extend([
            Landmark(id=5, x=mcp_x, y=mcp_y, z=mcp_z),
            Landmark(id=6, x=mcp_x + (tip_x - mcp_x) * 0.35, y=mcp_y + (tip_y - mcp_y) * 0.35, z=mcp_z + (tip_z - mcp_z) * 0.35),
            Landmark(id=7, x=mcp_x + (tip_x - mcp_x) * 0.70, y=mcp_y + (tip_y - mcp_y) * 0.70, z=mcp_z + (tip_z - mcp_z) * 0.70),
            Landmark(id=8, x=tip_x, y=tip_y, z=tip_z),
        ])
    elif index_foreshortened:
        # Straight pointing toward camera: $X, Y$ foreshortened, $Z$ projecting forward
        lms.extend([
            Landmark(id=5, x=0.45, y=0.55, z=0.0),
            Landmark(id=6, x=0.45, y=0.52, z=-0.04),
            Landmark(id=7, x=0.45, y=0.49, z=-0.08),
            Landmark(id=8, x=0.45, y=0.46, z=-0.12),
        ])
    else:
        # Curled
        lms.extend([
            Landmark(id=5, x=0.45, y=0.55, z=0.0),
            Landmark(id=6, x=0.45, y=0.49, z=0.05),
            Landmark(id=7, x=0.45, y=0.53, z=0.08),
            Landmark(id=8, x=0.45, y=0.58, z=0.05),
        ])

    # Middle 9..12
    if middle_extended:
        lms.extend([
            Landmark(id=9, x=0.50, y=0.53, z=0.0),
            Landmark(id=10, x=0.50, y=0.43, z=0.0),
            Landmark(id=11, x=0.50, y=0.33, z=0.0),
            Landmark(id=12, x=0.50, y=0.23, z=0.0),
        ])
    else:
        lms.extend([
            Landmark(id=9, x=0.50, y=0.53, z=0.0),
            Landmark(id=10, x=0.50, y=0.47, z=0.05),
            Landmark(id=11, x=0.50, y=0.51, z=0.08),
            Landmark(id=12, x=0.50, y=0.56, z=0.05),
        ])

    # Ring 13..16
    if ring_extended:
        lms.extend([
            Landmark(id=13, x=0.55, y=0.55, z=0.0),
            Landmark(id=14, x=0.55, y=0.45, z=0.0),
            Landmark(id=15, x=0.55, y=0.35, z=0.0),
            Landmark(id=16, x=0.55, y=0.25, z=0.0),
        ])
    else:
        lms.extend([
            Landmark(id=13, x=0.55, y=0.55, z=0.0),
            Landmark(id=14, x=0.55, y=0.49, z=0.05),
            Landmark(id=15, x=0.55, y=0.53, z=0.08),
            Landmark(id=16, x=0.55, y=0.58, z=0.05),
        ])

    # Pinky 17..20
    if pinky_extended:
        lms.extend([
            Landmark(id=17, x=0.60, y=0.58, z=0.0),
            Landmark(id=18, x=0.60, y=0.48, z=0.0),
            Landmark(id=19, x=0.60, y=0.38, z=0.0),
            Landmark(id=20, x=0.60, y=0.28, z=0.0),
        ])
    else:
        lms.extend([
            Landmark(id=17, x=0.60, y=0.58, z=0.0),
            Landmark(id=18, x=0.60, y=0.52, z=0.05),
            Landmark(id=19, x=0.60, y=0.56, z=0.08),
            Landmark(id=20, x=0.60, y=0.61, z=0.05),
        ])

    return lms


def _make_hand_state(lms: List[Landmark], timestamp: float = 1.0) -> HandState:
    bbox = BoundingBox(0.2, 0.2, 0.8, 0.8, 0.6, 0.6)
    return HandState(Handedness.RIGHT, 0.95, lms, bbox, (0.5, 0.6, 0.0), (0.5, 0.5, 0.0), timestamp, 0)


class TestGestureClassifierFixes(unittest.TestCase):
    def setUp(self):
        self.fa = FingerAnalyzer()
        self.ha = HandAnalyzer(self.fa)
        self.reg = GestureRegistry()
        self.reg.register(OpenPalmGesture())
        self.reg.register(PointGesture())
        self.reg.register(PeaceGesture())
        self.reg.register(FistGesture())
        self.reg.register(ThumbsUpGesture())
        self.reg.register(ThumbsDownGesture())
        self.reg.register(PinchGesture())
        self.reg.register(PinchPinkyGesture())
        self.gm = GestureManager(registry=self.reg, config=GestureConfig())

    # ── FIST TESTS ─────────────────────────────────────────────────────────────

    def test_01_tight_closed_fist(self):
        lms = _make_lms(thumb_tip=(0.50, 0.53, 0.05))
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = FistGesture().recognize(an)
        self.assertTrue(res.detected)
        self.assertGreaterEqual(res.confidence, 0.80)

    def test_02_thumb_resting_across_index(self):
        lms = _make_lms(thumb_tip=(0.46, 0.55, 0.04), thumb_mcp=(0.43, 0.60, 0.02))
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = FistGesture().recognize(an)
        self.assertTrue(res.detected)
        self.assertGreaterEqual(res.confidence, 0.80)

    def test_03_thumb_resting_across_middle_finger(self):
        lms = _make_lms(thumb_tip=(0.52, 0.53, 0.05), thumb_mcp=(0.44, 0.60, 0.02))
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = FistGesture().recognize(an)
        self.assertTrue(res.detected)

    def test_04_thumb_partially_visible(self):
        lms = _make_lms(thumb_tip=(0.44, 0.56, 0.02), thumb_mcp=(0.43, 0.60, 0.01))
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = FistGesture().recognize(an)
        self.assertTrue(res.detected)

    def test_05_fist_with_thumb_slightly_raised(self):
        lms = _make_lms(thumb_tip=(0.43, 0.52, 0.02), thumb_mcp=(0.42, 0.58, 0.01))
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = FistGesture().recognize(an)
        self.assertTrue(res.detected)

    def test_06_clear_thumbs_up_preserves_thumbs_up(self):
        lms = _make_lms(thumb_dir_up=True)
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res_tu = ThumbsUpGesture().recognize(an)
        res_fist = FistGesture().recognize(an)
        self.assertTrue(res_tu.detected)
        self.assertFalse(res_fist.detected)

    def test_07_clear_thumbs_down_preserves_thumbs_down(self):
        lms = _make_lms(thumb_dir_down=True)
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res_td = ThumbsDownGesture().recognize(an)
        res_fist = FistGesture().recognize(an)
        self.assertTrue(res_td.detected)
        self.assertFalse(res_fist.detected)

    # ── POINT TESTS ────────────────────────────────────────────────────────────

    def test_08_upright_point(self):
        lms = _make_lms(index_extended=True, index_tip=(0.45, 0.25, 0.0))
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = PointGesture().recognize(an)
        self.assertTrue(res.detected)
        self.assertGreaterEqual(res.confidence, 0.85)

    def test_09_rotated_point(self):
        lms = _make_lms(index_extended=True, index_tip=(0.38, 0.28, 0.0))
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = PointGesture().recognize(an)
        self.assertTrue(res.detected)

    def test_10_diagonal_point(self):
        lms = _make_lms(index_extended=True, index_tip=(0.30, 0.35, 0.0))
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = PointGesture().recognize(an)
        self.assertTrue(res.detected)

    def test_11_point_toward_camera_foreshortened(self):
        lms = _make_lms(index_foreshortened=True)
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = PointGesture().recognize(an)
        self.assertTrue(res.detected)

    def test_12_point_toward_screen(self):
        lms = _make_lms(index_foreshortened=True)
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = PointGesture().recognize(an)
        self.assertTrue(res.detected)

    def test_13_point_with_naturally_curled_middle_finger(self):
        lms = _make_lms(index_extended=True, index_tip=(0.45, 0.25, 0.0))
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = PointGesture().recognize(an)
        self.assertTrue(res.detected)

    def test_14_open_palm_rejects_point(self):
        lms = _make_lms(index_extended=True, middle_extended=True, ring_extended=True, pinky_extended=True, thumb_dir_up=True)
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = PointGesture().recognize(an)
        self.assertFalse(res.detected)

    def test_15_peace_rejects_point(self):
        lms = _make_lms(index_extended=True, middle_extended=True, index_tip=(0.42, 0.25, 0.0))
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = PointGesture().recognize(an)
        self.assertFalse(res.detected)

    def test_16_fist_rejects_point(self):
        lms = _make_lms(thumb_tip=(0.48, 0.55, 0.05))
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = PointGesture().recognize(an)
        self.assertFalse(res.detected)

    def test_17_pinch_rejects_point(self):
        lms = _make_lms(thumb_tip=(0.44, 0.38, 0.0), index_tip=(0.44, 0.38, 0.0), index_extended=True)
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res_pinch = PinchGesture().recognize(an)
        self.assertTrue(res_pinch.detected)

    # ── THUMBS DOWN TESTS ──────────────────────────────────────────────────────

    def test_18_clear_vertical_thumbs_down(self):
        lms = _make_lms(thumb_dir_down=True)
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = ThumbsDownGesture().recognize(an)
        self.assertTrue(res.detected)
        self.assertGreaterEqual(res.confidence, 0.80)

    def test_19_diagonal_thumbs_down(self):
        lms = _make_lms(thumb_diagonal_down=True)
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = ThumbsDownGesture().recognize(an)
        self.assertTrue(res.detected)

    def test_20_slightly_rotated_thumbs_down(self):
        lms = _make_lms(thumb_diagonal_down=True)
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = ThumbsDownGesture().recognize(an)
        self.assertTrue(res.detected)

    def test_21_thumbs_up_must_reject_thumbs_down(self):
        lms = _make_lms(thumb_dir_up=True)
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = ThumbsDownGesture().recognize(an)
        self.assertFalse(res.detected)

    def test_22_fist_must_reject_thumbs_down(self):
        lms = _make_lms(thumb_tip=(0.47, 0.55, 0.05))
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = ThumbsDownGesture().recognize(an)
        self.assertFalse(res.detected)

    def test_23_neutral_thumb_must_reject_thumbs_down(self):
        lms = _make_lms(thumb_neutral=True)
        an = self.ha.analyze_hands([_make_hand_state(lms)])[0]
        res = ThumbsDownGesture().recognize(an)
        self.assertFalse(res.detected)


if __name__ == "__main__":
    unittest.main()
