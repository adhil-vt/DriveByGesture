"""
gesturedrive.gestures
=====================
Modular Gesture Recognition Framework & Gesture Management System for GestureDrive.
"""

from gestures.base import Gesture
from gestures.gesture_result import GestureResult
from gestures.manager import ActiveGesture, GestureManager
from gestures.recognizer import GestureRecognizer
from gestures.registry import GestureRegistry

__all__ = [
    "Gesture",
    "GestureResult",
    "GestureRecognizer",
    "GestureRegistry",
    "GestureManager",
    "ActiveGesture",
]
