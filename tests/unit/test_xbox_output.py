"""
tests.unit.test_xbox_output
============================
Unit tests for XboxOutputPlugin translating ActionState to XboxController commands.
"""

import unittest

from actions.action import Action, ActionType
from actions.action_state import ActionState
from config.schema import XboxOutputConfig
from controller.xbox_controller import XboxController
from controller.xbox_output import XboxOutputPlugin


class TestXboxOutputPlugin(unittest.TestCase):
    def setUp(self):
        self.controller = XboxController()
        self.config = XboxOutputConfig(
            rt_max=255,
            lt_max=255,
            steering_sensitivity=1.0,
            steering_inversion=False,
            handbrake_button="A",
        )
        self.plugin = XboxOutputPlugin(controller=self.controller, config=self.config)

    def test_accelerator_mapping(self):
        state_accel = ActionState(
            accelerator=True,
            active_actions=[Action(ActionType.ACCELERATOR, value=1.0, confidence=0.9)]
        )
        self.plugin.process(state_accel)
        self.assertEqual(self.controller._rt, 255)
        self.assertEqual(self.controller._lt, 0)

        state_none = ActionState(accelerator=False)
        self.plugin.process(state_none)
        self.assertEqual(self.controller._rt, 0)

    def test_brake_mapping(self):
        state_brake = ActionState(
            brake=True,
            active_actions=[Action(ActionType.BRAKE, value=1.0, confidence=0.9)]
        )
        self.plugin.process(state_brake)
        self.assertEqual(self.controller._lt, 255)
        self.assertEqual(self.controller._rt, 0)

        state_none = ActionState(brake=False)
        self.plugin.process(state_none)
        self.assertEqual(self.controller._lt, 0)

    def test_handbrake_mapping(self):
        state_hb = ActionState(
            handbrake=True,
            active_actions=[Action(ActionType.HANDBRAKE, value=1.0, confidence=0.9)]
        )
        self.plugin.process(state_hb)
        self.assertIn("A", self.controller._buttons)

        state_none = ActionState(handbrake=False)
        self.plugin.process(state_none)
        self.assertNotIn("A", self.controller._buttons)

    def test_steering_mapping_center_left_right(self):
        # Center (0.0) -> LX = 0
        self.plugin.process(ActionState(steering=0.0))
        self.assertEqual(self.controller._lx, 0)

        # Full Right (+1.0) -> LX = 32767
        self.plugin.process(ActionState(steering=1.0))
        self.assertEqual(self.controller._lx, 32767)

        # Full Left (-1.0) -> LX = -32768
        self.plugin.process(ActionState(steering=-1.0))
        self.assertEqual(self.controller._lx, -32768)

    def test_steering_sensitivity_and_inversion(self):
        # Steering Inversion = True
        cfg_inv = XboxOutputConfig(steering_inversion=True, steering_sensitivity=1.0)
        plugin_inv = XboxOutputPlugin(controller=self.controller, config=cfg_inv)

        plugin_inv.process(ActionState(steering=1.0))
        self.assertEqual(self.controller._lx, -32768)

        # Steering Sensitivity = 0.50
        cfg_sens = XboxOutputConfig(steering_inversion=False, steering_sensitivity=0.50)
        plugin_sens = XboxOutputPlugin(controller=self.controller, config=cfg_sens)

        plugin_sens.process(ActionState(steering=1.0))
        self.assertEqual(self.controller._lx, 16384)

    def test_neutral_and_out_of_bounds_values(self):
        # Out-of-bounds steering clamped safely
        self.plugin.process(ActionState(steering=5.0))
        self.assertEqual(self.controller._lx, 32767)

        self.plugin.process(ActionState(steering=-5.0))
        self.assertEqual(self.controller._lx, -32768)

        # Empty / neutral ActionState
        self.plugin.process(ActionState())
        self.assertEqual(self.controller._lt, 0)
        self.assertEqual(self.controller._rt, 0)
        self.assertEqual(self.controller._lx, 0)
        self.assertEqual(len(self.controller._buttons), 0)


if __name__ == "__main__":
    unittest.main()
