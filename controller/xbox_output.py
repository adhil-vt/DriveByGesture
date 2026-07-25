"""
gesturedrive.controller.xbox_output
===================================
XboxOutputPlugin: Translates abstract ActionState snapshots into VirtualXboxController input commands.
"""

from __future__ import annotations

import logging
from typing import Optional

from actions.action import ActionType
from actions.action_state import ActionState
from config.schema import XboxOutputConfig
from controller.controller_base import IVirtualController
from controller.xbox_controller import XboxController

logger = logging.getLogger(__name__)


class XboxOutputPlugin:
    """
    Xbox Output Plugin: translates abstract ActionState snapshots into Xbox controller hardware inputs.

    Parameters
    ----------
    controller: Optional[IVirtualController]
        Virtual controller instance. If None, a default XboxController is instantiated.
    config: Optional[XboxOutputConfig]
        Configuration options for trigger limits, steering sensitivity/inversion, and button bindings.
    """

    def __init__(
        self,
        controller: Optional[IVirtualController] = None,
        config: Optional[XboxOutputConfig] = None,
    ) -> None:
        self.controller = controller if controller is not None else XboxController()
        self.config = config or XboxOutputConfig()

    def process(self, action_state: ActionState) -> None:
        """
        Consume an ActionState snapshot, map abstract actions to Xbox controller controls,
        and update the VirtualXboxController.

        Parameters
        ----------
        action_state: ActionState
            Snapshot of active abstract actions for the current frame.
        """
        if not action_state:
            self._apply_neutral()
            return

        # 1. Accelerator -> Right Trigger (RT)
        if action_state.accelerator or action_state.has_action(ActionType.ACCELERATOR):
            accel_act = action_state.get_action(ActionType.ACCELERATOR)
            scale = accel_act.value if accel_act is not None else 1.0
            target_rt = int(round(self.config.rt_max * max(0.0, min(1.0, scale))))
            self.controller.set_right_trigger(target_rt)
        else:
            self.controller.set_right_trigger(0)

        # 2. Brake -> Left Trigger (LT)
        if action_state.brake or action_state.has_action(ActionType.BRAKE):
            brake_act = action_state.get_action(ActionType.BRAKE)
            scale = brake_act.value if brake_act is not None else 1.0
            target_lt = int(round(self.config.lt_max * max(0.0, min(1.0, scale))))
            self.controller.set_left_trigger(target_lt)
        else:
            self.controller.set_left_trigger(0)

        # 3. Steering -> Left Stick X
        steering = action_state.steering
        if self.config.steering_inversion:
            steering = -steering

        scaled_steering = steering * self.config.steering_sensitivity
        if scaled_steering < 0.0:
            lx_val = int(round(scaled_steering * 32768.0))
        else:
            lx_val = int(round(scaled_steering * 32767.0))
        lx_clamped = max(-32768, min(32767, lx_val))
        self.controller.set_left_stick(lx_clamped, 0)

        # 4. Handbrake -> Configured Button (default "A")
        handbrake_btn = self.config.handbrake_button
        if action_state.handbrake or action_state.has_action(ActionType.HANDBRAKE):
            self.controller.press_button(handbrake_btn)
        else:
            self.controller.release_button(handbrake_btn)

        # 5. Send batched update packet to controller backend
        self.controller.update()

    def _apply_neutral(self) -> None:
        """Reset controller to neutral state and send update."""
        self.controller.reset()
        self.controller.update()
