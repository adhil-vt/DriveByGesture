"""
Unit tests for Phase 14.5: Desktop Drag Cursor Anchor Stabilization.
Verifies zero-jump Point -> Drag transitions, relative drag movement,
zero-jump Drag -> Point release re-anchoring, and mouse-button safety.
"""

import unittest
from unittest.mock import MagicMock

from core.models import Handedness
from tracking.hand_state import HandState, Landmark, BoundingBox
from analysis.finger_state import FingerPosition, FingerName, FingerState, HandAnalysis
from desktop.bindings import GestureBindingManager
from desktop.enums import DesktopActionType, DesktopState
from desktop.controller import DesktopController
from gestures.gesture_result import GestureResult


def _make_mock_landmarks(index_tip=(0.45, 0.35, 0.0), index_mcp=(0.45, 0.55, 0.0)):
    lms = []
    for i in range(21):
        if i == 5:
            lms.append(Landmark(id=5, x=index_mcp[0], y=index_mcp[1], z=index_mcp[2]))
        elif i == 8:
            lms.append(Landmark(id=8, x=index_tip[0], y=index_tip[1], z=index_tip[2]))
        elif i == 4:
            # Thumb far from index tip by default (no pinch)
            lms.append(Landmark(id=4, x=0.30, y=0.55, z=0.0))
        elif i == 0:
            lms.append(Landmark(id=0, x=0.50, y=0.70, z=0.0))
        elif i == 9:
            lms.append(Landmark(id=9, x=0.50, y=0.53, z=0.0))
        elif i == 17:
            lms.append(Landmark(id=17, x=0.60, y=0.58, z=0.0))
        else:
            lms.append(Landmark(id=i, x=0.50, y=0.50, z=0.0))
    return lms


def _make_mock_hand_state(index_tip=(0.45, 0.35, 0.0), index_mcp=(0.45, 0.55, 0.0)):
    lms = _make_mock_landmarks(index_tip, index_mcp)
    bbox = BoundingBox(0.2, 0.2, 0.8, 0.8, 0.6, 0.6)
    return HandState(Handedness.RIGHT, 0.95, lms, bbox, (0.5, 0.6, 0.0), (0.5, 0.5, 0.0), 1.0, 0)


def _make_mock_analysis(index_pos=FingerPosition.EXTENDED, middle_pos=FingerPosition.CURLED, hand_state=None):
    thumb = FingerState(FingerName.THUMB, FingerPosition.CURLED, 0.9)
    index = FingerState(FingerName.INDEX, index_pos, 0.95)
    middle = FingerState(FingerName.MIDDLE, middle_pos, 0.9)
    ring = FingerState(FingerName.RING, FingerPosition.CURLED, 0.9)
    pinky = FingerState(FingerName.PINKY, FingerPosition.CURLED, 0.9)
    hs = hand_state or _make_mock_hand_state()
    return HandAnalysis(hs, thumb, index, middle, ring, pinky, 1.0)


class TestDesktopDragStabilization(unittest.TestCase):
    def setUp(self):
        self.binding_mgr = GestureBindingManager({
            "Open Palm": "MOVE_CURSOR",
            "Point": "MOVE_CURSOR",
            "Fist": "DRAG",
            "Pinch": "LEFT_CLICK",
        })
        self.mock_executor = MagicMock()
        self.mock_executor.get_screen_size.return_value = (1920, 1080)
        self.mock_executor.get_cursor_pos.return_value = (960, 540)
        self.controller = DesktopController(
            binding_manager=self.binding_mgr,
            executor=self.mock_executor,
        )
        self.controller.cursor_smoothing = 1.0
        self.controller.cursor_acceleration = False
        self.controller.cursor_sensitivity = 1.0

    def test_a_point_to_drag_transition_locks_cursor(self):
        """During Point -> Fist transition frames, cursor remains frozen at stable Point location."""
        # 1. Establish stable Point at target (x=0.45, y=0.35)
        hs1 = _make_mock_hand_state(index_tip=(0.45, 0.35, 0.0), index_mcp=(0.45, 0.55, 0.0))
        an1 = _make_mock_analysis(index_pos=FingerPosition.EXTENDED)
        g_point = GestureResult("Point", detected=True, confidence=0.95, timestamp=1.0, handedness=Handedness.RIGHT)

        self.controller.process([hs1], [an1], [g_point])
        target_cursor_x, target_cursor_y = self.controller.cursor_pos

        # 2. User folds index finger into palm (Index tip moves to 0.45, 0.55) while Fist is not yet confirmed
        hs2 = _make_mock_hand_state(index_tip=(0.45, 0.55, 0.0), index_mcp=(0.45, 0.55, 0.0))
        an2 = _make_mock_analysis(index_pos=FingerPosition.PARTIALLY_BENT)
        g_none = GestureResult("None", detected=False, confidence=0.0, timestamp=1.033, handedness=Handedness.RIGHT)

        self.controller.process([hs2], [an2], [g_none])
        pending_cursor_x, pending_cursor_y = self.controller.cursor_pos

        # Cursor must NOT have moved with the collapsing index tip!
        self.assertEqual(pending_cursor_x, target_cursor_x)
        self.assertEqual(pending_cursor_y, target_cursor_y)
        self.assertEqual(self.controller._desktop_state, DesktopState.DRAG_PENDING)

    def test_b_drag_activation_anchors_and_sends_mouse_down(self):
        """When Fist/Drag becomes active, mouse_down occurs at the locked Point position."""
        # Stable Point
        hs1 = _make_mock_hand_state(index_tip=(0.45, 0.35, 0.0), index_mcp=(0.45, 0.55, 0.0))
        an1 = _make_mock_analysis(index_pos=FingerPosition.EXTENDED)
        g_point = GestureResult("Point", detected=True, confidence=0.95, timestamp=1.0, handedness=Handedness.RIGHT)
        self.controller.process([hs1], [an1], [g_point])
        point_x, point_y = self.controller.cursor_pos

        # Drag Confirmed
        hs_drag = _make_mock_hand_state(index_tip=(0.45, 0.55, 0.0), index_mcp=(0.45, 0.55, 0.0))
        an_drag = _make_mock_analysis(index_pos=FingerPosition.CURLED)
        g_fist = GestureResult("Fist", detected=True, confidence=0.95, timestamp=1.1, handedness=Handedness.RIGHT)

        self.controller.process([hs_drag], [an_drag], [g_fist])
        self.mock_executor.mouse_down.assert_called_once()
        self.assertEqual(self.controller.cursor_pos, (point_x, point_y))
        self.assertEqual(self.controller._desktop_state, DesktopState.DRAG_START)

    def test_c_drag_movement_moves_relative_to_anchor(self):
        """During dragging, cursor moves relative to reference MCP position."""
        # 1. Point at target
        hs1 = _make_mock_hand_state(index_tip=(0.45, 0.35, 0.0), index_mcp=(0.45, 0.55, 0.0))
        self.controller.process([hs1], [_make_mock_analysis(index_pos=FingerPosition.EXTENDED)], [GestureResult("Point", True, 0.95, 1.0, Handedness.RIGHT)])
        start_x, start_y = self.controller.cursor_pos

        # 2. Enter Drag
        hs2 = _make_mock_hand_state(index_tip=(0.45, 0.55, 0.0), index_mcp=(0.45, 0.55, 0.0))
        self.controller.process([hs2], [_make_mock_analysis(index_pos=FingerPosition.CURLED)], [GestureResult("Fist", True, 0.95, 1.1, Handedness.RIGHT)])

        # 3. Move Hand MCP right and up (dx = -0.10 in raw camera X -> +0.10 in inverted screen X, dy = -0.05)
        hs3 = _make_mock_hand_state(index_tip=(0.35, 0.50, 0.0), index_mcp=(0.35, 0.50, 0.0))
        self.controller.process([hs3], [_make_mock_analysis(index_pos=FingerPosition.CURLED)], [GestureResult("Fist", True, 0.95, 1.133, Handedness.RIGHT)])

        dragged_x, dragged_y = self.controller.cursor_pos
        self.assertGreater(dragged_x, start_x)
        self.assertLess(dragged_y, start_y)
        self.assertEqual(self.controller._desktop_state, DesktopState.DRAGGING)

    def test_d_drag_to_point_release_does_not_jump_cursor(self):
        """When Drag is released and Point resumes, cursor stays at drop location without jumping."""
        # 1. Point and enter drag
        hs1 = _make_mock_hand_state(index_tip=(0.45, 0.35, 0.0), index_mcp=(0.45, 0.55, 0.0))
        self.controller.process([hs1], [_make_mock_analysis(index_pos=FingerPosition.EXTENDED)], [GestureResult("Point", True, 0.95, 1.0, Handedness.RIGHT)])

        hs2 = _make_mock_hand_state(index_tip=(0.45, 0.55, 0.0), index_mcp=(0.45, 0.55, 0.0))
        self.controller.process([hs2], [_make_mock_analysis(index_pos=FingerPosition.CURLED)], [GestureResult("Fist", True, 0.95, 1.1, Handedness.RIGHT)])

        # 2. Drag to new location
        hs3 = _make_mock_hand_state(index_tip=(0.35, 0.50, 0.0), index_mcp=(0.35, 0.50, 0.0))
        self.controller.process([hs3], [_make_mock_analysis(index_pos=FingerPosition.CURLED)], [GestureResult("Fist", True, 0.95, 1.133, Handedness.RIGHT)])
        drop_x, drop_y = self.controller.cursor_pos

        # 3. Release Drag (3 frames release guard)
        hs_open = _make_mock_hand_state(index_tip=(0.35, 0.30, 0.0), index_mcp=(0.35, 0.50, 0.0))
        an_open = _make_mock_analysis(index_pos=FingerPosition.EXTENDED)
        g_point = GestureResult("Point", True, 0.95, 1.2, Handedness.RIGHT)

        for _ in range(3):
            self.controller.process([hs_open], [an_open], [g_point])

        self.mock_executor.mouse_up.assert_called_once()
        self.assertFalse(self.controller._is_dragging)

        # 4. First frame of resumed Point: Cursor must be at drop position
        resumed_x, resumed_y = self.controller.cursor_pos
        self.assertAlmostEqual(resumed_x, drop_x, delta=2.0)
        self.assertAlmostEqual(resumed_y, drop_y, delta=2.0)

    def test_e_exactly_one_mouse_down_and_mouse_up(self):
        """A full Point -> Drag -> Dragging -> Release sequence sends exactly 1 mouse_down and 1 mouse_up."""
        hs = _make_mock_hand_state()
        an_ext = _make_mock_analysis(index_pos=FingerPosition.EXTENDED)
        an_cur = _make_mock_analysis(index_pos=FingerPosition.CURLED)
        g_pt = GestureResult("Point", True, 0.95, 1.0, Handedness.RIGHT)
        g_fist = GestureResult("Fist", True, 0.95, 1.1, Handedness.RIGHT)

        # 5 Point frames
        for _ in range(5):
            self.controller.process([hs], [an_ext], [g_pt])

        # 10 Drag frames
        for _ in range(10):
            self.controller.process([hs], [an_cur], [g_fist])

        self.assertEqual(self.mock_executor.mouse_down.call_count, 1)
        self.assertEqual(self.mock_executor.mouse_up.call_count, 0)

        # 5 Release frames
        for _ in range(5):
            self.controller.process([hs], [an_ext], [g_pt])

        self.assertEqual(self.mock_executor.mouse_down.call_count, 1)
        self.assertEqual(self.mock_executor.mouse_up.call_count, 1)

    def test_f_tracking_loss_during_drag_releases_mouse(self):
        """If hands disappear while dragging, mouse_up is immediately sent."""
        hs = _make_mock_hand_state()
        an_cur = _make_mock_analysis(index_pos=FingerPosition.CURLED)
        g_fist = GestureResult("Fist", True, 0.95, 1.1, Handedness.RIGHT)

        # Start drag
        self.controller.process([hs], [an_cur], [g_fist])
        self.assertTrue(self.controller._is_dragging)

        # Hand lost
        self.controller.process([], None, [])
        self.assertFalse(self.controller._is_dragging)
        self.mock_executor.mouse_up.assert_called_once()

    def test_g_controller_reset_during_drag_releases_mouse(self):
        """Calling reset() releases mouse and resets all drag state."""
        hs = _make_mock_hand_state()
        an_cur = _make_mock_analysis(index_pos=FingerPosition.CURLED)
        g_fist = GestureResult("Fist", True, 0.95, 1.1, Handedness.RIGHT)

        self.controller.process([hs], [an_cur], [g_fist])
        self.assertTrue(self.controller._is_dragging)

        self.controller.reset()
        self.assertFalse(self.controller._is_dragging)
        self.mock_executor.mouse_up.assert_called_once()

    def test_h_rapid_point_drag_point_cycles_without_teleportation(self):
        """Rapidly cycling Point -> Drag -> Point does not cause cursor jumps or desync."""
        hs = _make_mock_hand_state()
        an_ext = _make_mock_analysis(index_pos=FingerPosition.EXTENDED)
        an_cur = _make_mock_analysis(index_pos=FingerPosition.CURLED)
        g_pt = GestureResult("Point", True, 0.95, 1.0, Handedness.RIGHT)
        g_fist = GestureResult("Fist", True, 0.95, 1.1, Handedness.RIGHT)

        for _ in range(3):
            # Point
            for _ in range(3):
                self.controller.process([hs], [an_ext], [g_pt])
            pt_x, pt_y = self.controller.cursor_pos

            # Drag
            for _ in range(4):
                self.controller.process([hs], [an_cur], [g_fist])

            # Release
            for _ in range(4):
                self.controller.process([hs], [an_ext], [g_pt])
            after_x, after_y = self.controller.cursor_pos

            self.assertAlmostEqual(pt_x, after_x, delta=5.0)
            self.assertAlmostEqual(pt_y, after_y, delta=5.0)

    def test_i_repeated_drags_recalculate_fresh_anchors(self):
        """Each new drag recalculates a fresh anchor at the current Point position."""
        hs1 = _make_mock_hand_state(index_tip=(0.30, 0.30, 0.0), index_mcp=(0.30, 0.50, 0.0))
        self.controller.process([hs1], [_make_mock_analysis(FingerPosition.EXTENDED)], [GestureResult("Point", True, 0.95, 1.0, Handedness.RIGHT)])
        pos1 = self.controller.cursor_pos

        self.controller.process([hs1], [_make_mock_analysis(FingerPosition.CURLED)], [GestureResult("Fist", True, 0.95, 1.1, Handedness.RIGHT)])
        self.assertAlmostEqual(self.controller._drag_start_cursor_pos[0], pos1[0], delta=1.0)
        self.assertAlmostEqual(self.controller._drag_start_cursor_pos[1], pos1[1], delta=1.0)

        # Resume Point at hs1
        for _ in range(4):
            self.controller.process([hs1], [_make_mock_analysis(FingerPosition.EXTENDED)], [GestureResult("Point", True, 0.95, 1.2, Handedness.RIGHT)])

        # Move hand to a completely different screen point hs2 (x=0.70, y=0.70)
        hs2 = _make_mock_hand_state(index_tip=(0.70, 0.70, 0.0), index_mcp=(0.70, 0.85, 0.0))
        for _ in range(3):
            self.controller.process([hs2], [_make_mock_analysis(FingerPosition.EXTENDED)], [GestureResult("Point", True, 0.95, 1.3, Handedness.RIGHT)])
        pos2 = self.controller.cursor_pos
        self.assertNotEqual(pos1, pos2)

        self.controller.process([hs2], [_make_mock_analysis(FingerPosition.CURLED)], [GestureResult("Fist", True, 0.95, 1.4, Handedness.RIGHT)])
        self.assertAlmostEqual(self.controller._drag_start_cursor_pos[0], pos2[0], delta=1.0)
        self.assertAlmostEqual(self.controller._drag_start_cursor_pos[1], pos2[1], delta=1.0)


if __name__ == "__main__":
    unittest.main()
