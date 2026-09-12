"""
gesturedrive.desktop.actions
=============================
DesktopAction data model.
"""

from __future__ import annotations

from dataclasses import dataclass
from desktop.enums import DesktopActionType


@dataclass(frozen=True)
class DesktopAction:
    """
    Represents an active desktop action event.

    Attributes
    ----------
    action_type: DesktopActionType
        The category of desktop action.
    value: float
        Magnitude/parameter for action (e.g. scroll delta or axis move).
    confidence: float
        Confidence score of recognized gesture triggering this action.
    shortcut_keys: str
        Optional custom key combination string (e.g. "ctrl+c", "alt+tab").
    """
    action_type: DesktopActionType
    value: float = 1.0
    confidence: float = 1.0
    shortcut_keys: str = ""
