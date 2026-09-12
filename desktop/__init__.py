"""
gesturedrive.desktop
=====================
Desktop gesture control subsystem.
"""

from desktop.actions import DesktopAction
from desktop.bindings import GestureBindingManager
from desktop.controller import DesktopController
from desktop.enums import AppMode, DesktopActionType
from desktop.executor import IOSDesktopExecutor, NullDesktopExecutor, WindowsDesktopExecutor, get_desktop_executor
from desktop.manager import ModeManager

__all__ = [
    "AppMode",
    "DesktopActionType",
    "DesktopAction",
    "IOSDesktopExecutor",
    "WindowsDesktopExecutor",
    "NullDesktopExecutor",
    "get_desktop_executor",
    "GestureBindingManager",
    "DesktopController",
    "ModeManager",
]
