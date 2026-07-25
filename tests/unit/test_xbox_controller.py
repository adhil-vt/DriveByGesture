"""
tests.unit.test_xbox_controller
================================
Unit tests for VirtualXboxController / XboxController backend.
"""

import unittest
from unittest.mock import MagicMock, patch

from config.schema import ControllerConfig
from core.exceptions import ControllerError
from controller.xbox_controller import VirtualXboxController, XboxController


class TestXboxController(unittest.TestCase):
    def setUp(self):
        self.config = ControllerConfig(deadzone=0.05)
        self.controller = XboxController(config=self.config)

    def test_standalone_usage_without_gestures(self):
        # Verify controller API works independently without importing gesture modules
        c = XboxController()
        c.press_button("A")
        c.set_right_trigger(255)
        c.set_left_stick(0, -12000)

        debug = c.get_debug_info()
        self.assertIn("A", debug)
        self.assertIn("RT: 255", debug)
        self.assertIn("LY: -12000", debug)

    def test_connection_failure_when_vgamepad_missing(self):
        # When vgamepad or ViGEmBus driver is unavailable, connect() raises ControllerError gracefully
        with patch("controller.xbox_controller._VGAMEPAD_AVAILABLE", False):
            controller = XboxController()
            with self.assertRaises(ControllerError):
                controller.connect()

    def test_button_press_and_release(self):
        self.controller.press_button("A")
        self.controller.press_button("RB")
        self.assertIn("A", self.controller._buttons)
        self.assertIn("RB", self.controller._buttons)
        self.assertTrue(self.controller._dirty)

        self.controller.release_button("A")
        self.assertNotIn("A", self.controller._buttons)
        self.assertIn("RB", self.controller._buttons)

    def test_invalid_button_handling(self):
        # Never crash on invalid button inputs
        self.controller.press_button("INVALID_BUTTON_99")
        self.controller.release_button("NON_EXISTENT")
        self.assertEqual(len(self.controller._buttons), 0)

    def test_trigger_normalization_and_clamping(self):
        # Int in range [0, 255]
        self.controller.set_left_trigger(180)
        self.assertEqual(self.controller._lt, 180)

        # Float in normalized range [0.0, 1.0]
        self.controller.set_right_trigger(0.50)
        self.assertEqual(self.controller._rt, 128)

        # Out-of-bounds inputs clamped safely
        self.controller.set_left_trigger(-50)
        self.assertEqual(self.controller._lt, 0)

        self.controller.set_right_trigger(999)
        self.assertEqual(self.controller._rt, 255)

    def test_stick_deadzone_and_clamping(self):
        # Inside deadzone (deadzone=0.05 * 32767 = 1638)
        self.controller.set_left_stick(500, -1000)
        self.assertEqual(self.controller._lx, 0)
        self.assertEqual(self.controller._ly, 0)

        # Outside deadzone
        self.controller.set_left_stick(0, -12000)
        self.assertEqual(self.controller._lx, 0)
        self.assertEqual(self.controller._ly, -12000)

        # Float normalized [-1.0, 1.0]
        self.controller.set_right_stick(1.0, -0.5)
        self.assertEqual(self.controller._rx, 32767)
        self.assertEqual(self.controller._ry, -16384)

        # Out-of-bounds clamped
        self.controller.set_left_stick(50000, -90000)
        self.assertEqual(self.controller._lx, 32767)
        self.assertEqual(self.controller._ly, -32768)

    def test_dpad_press_and_release(self):
        self.controller.press_dpad("UP")
        self.assertEqual(self.controller._dpad, "UP")

        self.controller.press_dpad("DPAD_RIGHT")
        self.assertEqual(self.controller._dpad, "RIGHT")

        self.controller.release_dpad()
        self.assertEqual(self.controller._dpad, "OFF")

    def test_reset(self):
        self.controller.press_button("X")
        self.controller.set_left_trigger(200)
        self.controller.set_left_stick(15000, -15000)
        self.controller.press_dpad("LEFT")

        self.controller.reset()
        self.assertEqual(len(self.controller._buttons), 0)
        self.assertEqual(self.controller._lt, 0)
        self.assertEqual(self.controller._rt, 0)
        self.assertEqual(self.controller._lx, 0)
        self.assertEqual(self.controller._ly, 0)
        self.assertEqual(self.controller._dpad, "OFF")

    def test_state_caching_and_dirty_flag(self):
        self.assertFalse(self.controller._dirty)
        self.controller.set_left_trigger(100)
        self.assertTrue(self.controller._dirty)

        # Setting identical value does not trigger dirty flag
        self.controller._dirty = False
        self.controller.set_left_trigger(100)
        self.assertFalse(self.controller._dirty)

    def test_debug_info(self):
        self.controller.press_button("A")
        self.controller.press_button("RB")
        self.controller.set_right_trigger(180)
        self.controller.set_left_stick(0, -12000)

        debug = self.controller.get_debug_info()
        self.assertIn("Controller Disconnected", debug)
        self.assertIn("A", debug)
        self.assertIn("RB", debug)
        self.assertIn("RT: 180", debug)
        self.assertIn("LY: -12000", debug)


if __name__ == "__main__":
    unittest.main()
