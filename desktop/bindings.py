"""
gesturedrive.desktop.bindings
==============================
GestureBindingManager: maps recognized gestures to DesktopActionType.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from desktop.enums import DesktopActionType

logger = logging.getLogger(__name__)


def default_gesture_bindings() -> Dict[str, str]:
    """Return default mapping dictionary of gesture names to DesktopActionType name string."""
    return {
        "Open Palm": "MOVE_CURSOR",
        "Pinch": "LEFT_CLICK",
        "Pinch Pinky": "RIGHT_CLICK",
        "Peace": "RIGHT_CLICK",
        "Point": "DOUBLE_CLICK",
        "Fist": "DRAG",
        "Thumbs Up": "VOLUME_UP",
        "Thumbs Down": "VOLUME_DOWN",
    }


class GestureBindingManager:
    """
    Manages custom and default gesture-to-desktop action mappings.
    """

    def __init__(self, bindings: Optional[Dict[str, str]] = None) -> None:
        self._mappings: Dict[str, DesktopActionType] = {}
        raw = bindings or default_gesture_bindings()
        self.set_bindings_dict(raw)

    def resolve_action(self, gesture_name: str) -> DesktopActionType:
        """
        Lookup DesktopActionType mapped to gesture_name.
        Case-insensitive key lookup with fallback to NONE.
        """
        if not gesture_name or gesture_name == "Unknown":
            return DesktopActionType.NONE

        # Try exact key, title case, upper case
        keys_to_try = [
            gesture_name,
            gesture_name.title(),
            gesture_name.upper(),
            gesture_name.lower(),
        ]
        for k in keys_to_try:
            if k in self._mappings:
                return self._mappings[k]

        return DesktopActionType.NONE

    def bind(self, gesture_name: str, action: DesktopActionType | str) -> None:
        """Assign an action to a gesture name."""
        if isinstance(action, str):
            act_enum = DesktopActionType.from_str(action)
        else:
            act_enum = action

        self._mappings[gesture_name] = act_enum
        logger.debug("GestureBindingManager: bound '%s' → %s", gesture_name, act_enum.name)

    def unbind(self, gesture_name: str) -> None:
        """Remove binding for a gesture name."""
        if gesture_name in self._mappings:
            del self._mappings[gesture_name]

    def set_bindings_dict(self, bindings: Dict[str, str]) -> None:
        """Replace all bindings with string-based map dict."""
        self._mappings.clear()
        for g_name, act_str in bindings.items():
            self.bind(g_name, act_str)

    def to_dict(self) -> Dict[str, str]:
        """Export current bindings dictionary for profile serialization."""
        return {g: act.name for g, act in self._mappings.items()}

    def reset_defaults(self) -> None:
        """Reset to factory default gesture bindings."""
        self.set_bindings_dict(default_gesture_bindings())
