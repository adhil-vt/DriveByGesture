"""
gesturedrive.controller.xbox_controller
==========================================
VirtualXboxController / XboxController: Production-quality IVirtualController backed by vgamepad / ViGEmBus.

Design
------
- Isolated from gesture, tracking, and game logic.
- Implements state caching & diffing to avoid duplicate USB update packets.
- Robust input validation and clamping for buttons, triggers, sticks, and D-Pad.
- Fallback/error handling when ViGEmBus or vgamepad driver is unavailable.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Set, Union

from config.schema import ControllerConfig
from core.exceptions import ControllerError
from core.interfaces import IVirtualController
from core.models import ControllerInput

logger = logging.getLogger(__name__)

# Try importing vgamepad backend
try:
    import vgamepad as vg
    _VGAMEPAD_AVAILABLE = True
except ImportError:
    vg = None
    _VGAMEPAD_AVAILABLE = False


# Standard button name mappings
_BUTTON_MAP: Dict[str, str] = {
    "A": "A",
    "B": "B",
    "X": "X",
    "Y": "Y",
    "LB": "LB",
    "LEFT_SHOULDER": "LB",
    "RB": "RB",
    "RIGHT_SHOULDER": "RB",
    "BACK": "BACK",
    "SELECT": "BACK",
    "START": "START",
    "LS": "LS",
    "LEFT_THUMB": "LS",
    "RS": "RS",
    "RIGHT_THUMB": "RS",
}

# Standard D-Pad mappings
_DPAD_MAP: Dict[str, str] = {
    "UP": "UP",
    "DPAD_UP": "UP",
    "DOWN": "DOWN",
    "DPAD_DOWN": "DOWN",
    "LEFT": "LEFT",
    "DPAD_LEFT": "LEFT",
    "RIGHT": "RIGHT",
    "DPAD_RIGHT": "RIGHT",
    "OFF": "OFF",
    "NONE": "OFF",
}


class XboxController(IVirtualController):
    """
    Virtual Xbox 360 gamepad controller backend.

    Parameters
    ----------
    config: Optional[ControllerConfig]
        Configuration options for deadzone, trigger/stick limits, and update behavior.
    rumble_enabled: bool
        Optional override for rumble feedback setting.
    """

    def __init__(
        self,
        config: Optional[ControllerConfig] = None,
        rumble_enabled: bool = False,
    ) -> None:
        self.config = config or ControllerConfig()
        self._rumble_enabled = rumble_enabled or self.config.rumble_enabled
        self._gamepad: Optional[vg.VX360Gamepad] = None if vg else None
        self._connected: bool = False

        # State caching
        self._buttons: Set[str] = set()
        self._lt: int = 0
        self._rt: int = 0
        self._lx: int = 0
        self._ly: int = 0
        self._rx: int = 0
        self._ry: int = 0
        self._dpad: str = "OFF"

        self._dirty: bool = False

    def connect(self) -> None:
        """
        Initialise the virtual gamepad backend.

        Raises
        ------
        ControllerError
            If vgamepad module or ViGEmBus driver is not available.
        """
        if self._connected:
            return

        if not _VGAMEPAD_AVAILABLE or vg is None:
            logger.error("vgamepad module is not installed or available.")
            raise ControllerError("vgamepad library or ViGEmBus driver is not installed.")

        try:
            self._gamepad = vg.VX360Gamepad()
            self._connected = True
            self._dirty = True
            self.update()
            logger.info("XboxController: Virtual gamepad connected successfully via ViGEmBus.")
        except Exception as exc:
            self._connected = False
            self._gamepad = None
            logger.error("Failed to connect virtual gamepad: %s", exc)
            raise ControllerError(f"Failed to connect virtual Xbox controller: {exc}") from exc

    def disconnect(self) -> None:
        """Unregister the virtual controller from ViGEmBus."""
        if not self._connected:
            return

        try:
            if self._gamepad is not None:
                self.reset()
                self._gamepad = None
        except Exception as exc:
            logger.warning("Error during controller disconnect: %s", exc)
        finally:
            self._connected = False
            logger.info("XboxController: Virtual gamepad disconnected.")

    @property
    def is_connected(self) -> bool:
        """Return True if the virtual device is currently connected."""
        return self._connected

    def is_connected_method(self) -> bool:
        """Method wrapper for is_connected."""
        return self._connected

    # ── Button Interface ───────────────────────────────────────────────────────

    def press_button(self, button: str) -> None:
        """Press a controller button by name ("A", "B", "X", "Y", "LB", "RB", "BACK", "START", "LS", "RS")."""
        key = _BUTTON_MAP.get(button.upper())
        if key is None:
            logger.warning("Ignored invalid button press: '%s'", button)
            return

        if key not in self._buttons:
            self._buttons.add(key)
            self._dirty = True

    def release_button(self, button: str) -> None:
        """Release a controller button by name."""
        key = _BUTTON_MAP.get(button.upper())
        if key is None:
            logger.warning("Ignored invalid button release: '%s'", button)
            return

        if key in self._buttons:
            self._buttons.remove(key)
            self._dirty = True

    # ── Trigger Interface ──────────────────────────────────────────────────────

    def set_left_trigger(self, value: Union[int, float]) -> None:
        """Set Left Trigger value in range [0, 255] or normalized [0.0, 1.0]."""
        val_int = self._normalize_trigger_value(value)
        if self._lt != val_int:
            self._lt = val_int
            self._dirty = True

    def set_right_trigger(self, value: Union[int, float]) -> None:
        """Set Right Trigger value in range [0, 255] or normalized [0.0, 1.0]."""
        val_int = self._normalize_trigger_value(value)
        if self._rt != val_int:
            self._rt = val_int
            self._dirty = True

    # ── Stick Interface ────────────────────────────────────────────────────────

    def set_left_stick(self, x: Union[int, float], y: Union[int, float]) -> None:
        """Set Left Stick coordinates in range [-32768, 32767] or normalized [-1.0, 1.0]."""
        lx = self._normalize_stick_value(x)
        ly = self._normalize_stick_value(y)
        if self._lx != lx or self._ly != ly:
            self._lx, self._ly = lx, ly
            self._dirty = True

    def set_right_stick(self, x: Union[int, float], y: Union[int, float]) -> None:
        """Set Right Stick coordinates in range [-32768, 32767] or normalized [-1.0, 1.0]."""
        rx = self._normalize_stick_value(x)
        ry = self._normalize_stick_value(y)
        if self._rx != rx or self._ry != ry:
            self._rx, self._ry = rx, ry
            self._dirty = True

    # ── D-Pad Interface ────────────────────────────────────────────────────────

    def press_dpad(self, direction: str) -> None:
        """Press D-Pad direction ("UP", "DOWN", "LEFT", "RIGHT", "OFF")."""
        key = _DPAD_MAP.get(direction.upper())
        if key is None:
            logger.warning("Ignored invalid D-Pad direction: '%s'", direction)
            return

        if self._dpad != key:
            self._dpad = key
            self._dirty = True

    def release_dpad(self) -> None:
        """Release D-Pad (reset to OFF)."""
        if self._dpad != "OFF":
            self._dpad = "OFF"
            self._dirty = True

    # ── Reset & Update ─────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset all buttons, triggers, sticks, and D-Pad to neutral state."""
        if (
            self._buttons
            or self._lt != 0
            or self._rt != 0
            or self._lx != 0
            or self._ly != 0
            or self._rx != 0
            or self._ry != 0
            or self._dpad != "OFF"
        ):
            self._buttons.clear()
            self._lt = 0
            self._rt = 0
            self._lx = 0
            self._ly = 0
            self._rx = 0
            self._ry = 0
            self._dpad = "OFF"
            self._dirty = True

        if self._connected and self._gamepad is not None and vg is not None:
            try:
                self._gamepad.reset()
                self._gamepad.update()
            except Exception as exc:
                logger.error("Error resetting virtual gamepad: %s", exc)

    def update(self) -> None:
        """
        Push queued state changes to the virtual gamepad backend.
        Skips update if no state changes occurred (avoids duplicate USB packets).
        """
        if not self._dirty:
            return

        if not self._connected or self._gamepad is None or vg is None:
            self._dirty = False
            return

        try:
            # 1. Reset hardware state prior to applying current cached state
            self._gamepad.reset()

            # 2. Apply buttons
            if "A" in self._buttons:
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
            if "B" in self._buttons:
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_B)
            if "X" in self._buttons:
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_X)
            if "Y" in self._buttons:
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_Y)
            if "LB" in self._buttons:
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
            if "RB" in self._buttons:
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)
            if "BACK" in self._buttons:
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK)
            if "START" in self._buttons:
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_START)
            if "LS" in self._buttons:
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
            if "RS" in self._buttons:
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB)

            # 3. Apply D-Pad
            if self._dpad == "UP":
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
            elif self._dpad == "DOWN":
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
            elif self._dpad == "LEFT":
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
            elif self._dpad == "RIGHT":
                self._gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

            # 4. Apply Triggers
            self._gamepad.left_trigger(value=self._lt)
            self._gamepad.right_trigger(value=self._rt)

            # 5. Apply Sticks
            self._gamepad.left_joystick(x_value=self._lx, y_value=self._ly)
            self._gamepad.right_joystick(x_value=self._rx, y_value=self._ry)

            # 6. Send USB packet
            self._gamepad.update()
            self._dirty = False

        except Exception as exc:
            logger.error("Error during controller update: %s", exc)
            raise ControllerError(f"vgamepad update failed: {exc}") from exc

    def apply(self, input_snapshot: ControllerInput) -> None:
        """
        Send a complete ControllerInput snapshot to the virtual device.
        """
        self.reset()
        if hasattr(input_snapshot, "left_trigger"):
            self.set_left_trigger(input_snapshot.left_trigger)
        if hasattr(input_snapshot, "right_trigger"):
            self.set_right_trigger(input_snapshot.right_trigger)
        if hasattr(input_snapshot, "left_stick_x") and hasattr(input_snapshot, "left_stick_y"):
            self.set_left_stick(input_snapshot.left_stick_x, input_snapshot.left_stick_y)
        if hasattr(input_snapshot, "right_stick_x") and hasattr(input_snapshot, "right_stick_y"):
            self.set_right_stick(input_snapshot.right_stick_x, input_snapshot.right_stick_y)

        # Apply buttons from snapshot
        for btn_attr in ["button_a", "button_b", "button_x", "button_y", "bumper_left", "bumper_right"]:
            if getattr(input_snapshot, btn_attr, False):
                btn_name = btn_attr.replace("button_", "").replace("bumper_", "").upper()
                if btn_name in ("LEFT", "RIGHT"):
                    btn_name = "LB" if btn_name == "LEFT" else "RB"
                self.press_button(btn_name)

        self.update()

    def get_debug_info(self) -> str:
        """Format debug text showing current controller state."""
        status = "Controller Connected" if self._connected else "Controller Disconnected"
        lines = [status, "", "Buttons:"]
        if self._buttons:
            for btn in sorted(self._buttons):
                lines.append(btn)
        else:
            lines.append("None")

        lines.extend([
            "",
            f"LT: {self._lt}",
            f"RT: {self._rt}",
            "",
            f"LX: {self._lx}",
            f"LY: {self._ly}",
            f"RX: {self._rx}",
            f"RY: {self._ry}",
            f"DPAD: {self._dpad}",
        ])
        return "\n".join(lines)

    # ── Input Helpers ──────────────────────────────────────────────────────────

    def _normalize_trigger_value(self, val: Union[int, float]) -> int:
        """Normalize and clamp trigger input value to integer [0, 255]."""
        try:
            f_val = float(val)
        except (ValueError, TypeError):
            return 0

        if 0.0 <= f_val <= 1.0 and isinstance(val, float):
            f_val *= 255.0

        return max(0, min(255, int(round(f_val))))

    def _normalize_stick_value(self, val: Union[int, float]) -> int:
        """Normalize, apply deadzone, and clamp stick value to integer [-32768, 32767]."""
        try:
            f_val = float(val)
        except (ValueError, TypeError):
            return 0

        # Normalized float [-1.0, 1.0]
        if -1.0 <= f_val <= 1.0 and isinstance(val, float):
            f_val *= 32767.0

        i_val = int(round(f_val))

        # Apply deadzone filtering
        deadzone_int = int(round(self.config.deadzone * 32767.0))
        if abs(i_val) <= deadzone_int:
            return 0

        return max(-32768, min(32767, i_val))


# Alias for explicit class name requests
VirtualXboxController = XboxController
