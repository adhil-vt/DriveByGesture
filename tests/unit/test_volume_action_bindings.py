"""
Unit tests for Phase 14.4.3: Thumbs Down Volume-Down Keybind and Action Resolution.
"""

import os
import unittest
from unittest.mock import MagicMock

from desktop.bindings import GestureBindingManager, default_gesture_bindings
from desktop.enums import DesktopActionType
from desktop.controller import DesktopController
from profiles.storage import ProfileStorage
from gestures.gesture_result import GestureResult
from core.models import Handedness


class TestVolumeActionBindings(unittest.TestCase):
    def setUp(self):
        self.binding_mgr = GestureBindingManager()
        self.mock_executor = MagicMock()
        self.mock_executor.get_screen_size.return_value = (1920, 1080)
        self.mock_executor.get_cursor_pos.return_value = (960, 540)
        self.controller = DesktopController(
            binding_manager=self.binding_mgr,
            executor=self.mock_executor,
        )

    def test_01_thumbs_up_resolves_to_volume_up(self):
        action = self.binding_mgr.resolve_action("Thumbs Up")
        self.assertEqual(action, DesktopActionType.VOLUME_UP)

    def test_02_thumbs_down_resolves_to_volume_down(self):
        action = self.binding_mgr.resolve_action("Thumbs Down")
        self.assertEqual(action, DesktopActionType.VOLUME_DOWN)

    def test_03_thumbs_up_does_not_resolve_to_volume_down(self):
        action = self.binding_mgr.resolve_action("Thumbs Up")
        self.assertNotEqual(action, DesktopActionType.VOLUME_DOWN)

    def test_04_thumbs_down_does_not_resolve_to_volume_up(self):
        action = self.binding_mgr.resolve_action("Thumbs Down")
        self.assertNotEqual(action, DesktopActionType.VOLUME_UP)

    def test_05_existing_gesture_bindings_remain_unchanged(self):
        self.assertEqual(self.binding_mgr.resolve_action("Open Palm"), DesktopActionType.MOVE_CURSOR)
        self.assertEqual(self.binding_mgr.resolve_action("Pinch"), DesktopActionType.LEFT_CLICK)
        self.assertEqual(self.binding_mgr.resolve_action("Pinch Pinky"), DesktopActionType.RIGHT_CLICK)
        self.assertEqual(self.binding_mgr.resolve_action("Fist"), DesktopActionType.DRAG)

    def test_06_controller_executes_volume_up_action(self):
        g_res = GestureResult(
            gesture_name="Thumbs Up",
            detected=True,
            confidence=0.95,
            timestamp=1.0,
            handedness=Handedness.RIGHT,
        )
        mock_hand = MagicMock()
        mock_hand.landmarks = []
        self.controller.process(hands=[mock_hand], hand_analyses=None, gesture_results=[g_res])
        self.mock_executor.volume_up.assert_called_once()
        self.mock_executor.volume_down.assert_not_called()

    def test_07_controller_executes_volume_down_action(self):
        g_res = GestureResult(
            gesture_name="Thumbs Down",
            detected=True,
            confidence=0.95,
            timestamp=1.0,
            handedness=Handedness.RIGHT,
        )
        mock_hand = MagicMock()
        mock_hand.landmarks = []
        self.controller.process(hands=[mock_hand], hand_analyses=None, gesture_results=[g_res])
        self.mock_executor.volume_down.assert_called_once()
        self.mock_executor.volume_up.assert_not_called()

    def test_08_default_profile_contains_thumbs_down_binding(self):
        storage = ProfileStorage()
        profile = storage.load("Default")
        self.assertIsNotNone(profile)
        bindings = profile.desktop["bindings"]
        self.assertIn("Thumbs Down", bindings)
        self.assertEqual(bindings["Thumbs Down"], "VOLUME_DOWN")
        self.assertIn("Thumbs Up", bindings)
        self.assertEqual(bindings["Thumbs Up"], "VOLUME_UP")


if __name__ == "__main__":
    unittest.main()
