"""
gesturedrive.desktop.enums
===========================
Operating modes and desktop action enumerations.
"""

from __future__ import annotations

from enum import Enum, auto


class AppMode(Enum):
    """
    Primary application operating mode.
    """
    DRIVING = "driving"
    DESKTOP = "desktop"

    @classmethod
    def from_str(cls, val: str) -> AppMode:
        s = str(val).lower().strip()
        if s == "desktop":
            return cls.DESKTOP
        return cls.DRIVING


class DesktopActionType(Enum):
    """
    Supported desktop interaction action types.
    """
    NONE = auto()
    MOVE_CURSOR = auto()
    LEFT_CLICK = auto()
    RIGHT_CLICK = auto()
    DOUBLE_CLICK = auto()
    DRAG = auto()
    SCROLL_UP = auto()
    SCROLL_DOWN = auto()
    VOLUME_UP = auto()
    VOLUME_DOWN = auto()
    MUTE = auto()
    PLAY_PAUSE = auto()
    NEXT_TRACK = auto()
    PREV_TRACK = auto()
    SHOW_DESKTOP = auto()
    TASK_VIEW = auto()
    CUSTOM_SHORTCUT = auto()

    @classmethod
    def from_str(cls, name: str) -> DesktopActionType:
        key = str(name).upper().strip().replace(" ", "_")
        try:
            return cls[key]
        except KeyError:
            return cls.NONE


class DesktopState(Enum):
    """
    Internal desktop controller gesture execution state.
    """
    IDLE = auto()
    MOVING = auto()
    ARTICULATION_LOCK = auto()
    DRAG_PENDING = auto()
    DRAG_START = auto()
    DRAGGING = auto()
    DRAG_END = auto()
