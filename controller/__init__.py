"""
gesturedrive.controller
========================
Virtual controller output layer.

Responsibility
--------------
- Translate ActionState into VirtualXboxController input commands.
- Send ControllerInput / actions to IVirtualController (XboxController or NullController).
- Publish ControllerInputSentEvent after each successful send.
"""

from controller.controller_base import IVirtualController
from controller.null_controller import NullController
from controller.xbox_controller import VirtualXboxController, XboxController
from controller.xbox_output import XboxOutputPlugin

__all__ = [
    "IVirtualController",
    "XboxController",
    "VirtualXboxController",
    "NullController",
    "XboxOutputPlugin",
]
