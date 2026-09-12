"""
gesturedrive.desktop.executor
==============================
OS-level Desktop Executor abstraction and implementations.

Provides Windows-native hardware execution via ctypes win32 API
and a Null executor for safe fallback on unsupported OS environments.
"""

from __future__ import annotations

import logging
import sys
import time
from abc import ABC, abstractmethod
from typing import Tuple

logger = logging.getLogger(__name__)


class IOSDesktopExecutor(ABC):
    """
    Abstract interface for executing OS desktop actions.
    """

    @abstractmethod
    def get_screen_size(self) -> Tuple[int, int]:
        """Return (width, height) of primary screen in pixels."""

    @abstractmethod
    def set_cursor_pos(self, x: int, y: int) -> None:
        """Set absolute mouse cursor position."""

    @abstractmethod
    def left_click(self) -> None:
        """Trigger left mouse click."""

    @abstractmethod
    def right_click(self) -> None:
        """Trigger right mouse click."""

    @abstractmethod
    def double_click(self) -> None:
        """Trigger double left mouse click."""

    @abstractmethod
    def mouse_down(self) -> None:
        """Press and hold left mouse button (start drag)."""

    @abstractmethod
    def mouse_up(self) -> None:
        """Release left mouse button (end drag)."""

    @abstractmethod
    def scroll(self, delta: int) -> None:
        """Scroll mouse wheel (positive = up, negative = down)."""

    @abstractmethod
    def volume_up(self) -> None:
        """Increase system master volume."""

    @abstractmethod
    def volume_down(self) -> None:
        """Decrease system master volume."""

    @abstractmethod
    def mute(self) -> None:
        """Toggle system volume mute."""

    @abstractmethod
    def play_pause(self) -> None:
        """Toggle media playback (play/pause)."""

    @abstractmethod
    def next_track(self) -> None:
        """Skip to next media track."""

    @abstractmethod
    def prev_track(self) -> None:
        """Skip to previous media track."""

    @abstractmethod
    def show_desktop(self) -> None:
        """Toggle show desktop (Win+D)."""

    @abstractmethod
    def task_view(self) -> None:
        """Open Task View (Win+Tab)."""

    @abstractmethod
    def execute_shortcut(self, shortcut: str) -> None:
        """Execute custom key combination string (e.g. 'ctrl+c')."""


class NullDesktopExecutor(IOSDesktopExecutor):
    """
    No-op stub executor for testing and non-supported operating systems.
    """

    def get_screen_size(self) -> Tuple[int, int]:
        return (1920, 1080)

    def set_cursor_pos(self, x: int, y: int) -> None:
        pass

    def left_click(self) -> None:
        logger.debug("NullDesktopExecutor: left_click")

    def right_click(self) -> None:
        logger.debug("NullDesktopExecutor: right_click")

    def double_click(self) -> None:
        logger.debug("NullDesktopExecutor: double_click")

    def mouse_down(self) -> None:
        logger.debug("NullDesktopExecutor: mouse_down")

    def mouse_up(self) -> None:
        logger.debug("NullDesktopExecutor: mouse_up")

    def scroll(self, delta: int) -> None:
        logger.debug("NullDesktopExecutor: scroll(%d)", delta)

    def volume_up(self) -> None:
        logger.debug("NullDesktopExecutor: volume_up")

    def volume_down(self) -> None:
        logger.debug("NullDesktopExecutor: volume_down")

    def mute(self) -> None:
        logger.debug("NullDesktopExecutor: mute")

    def play_pause(self) -> None:
        logger.debug("NullDesktopExecutor: play_pause")

    def next_track(self) -> None:
        logger.debug("NullDesktopExecutor: next_track")

    def prev_track(self) -> None:
        logger.debug("NullDesktopExecutor: prev_track")

    def show_desktop(self) -> None:
        logger.debug("NullDesktopExecutor: show_desktop")

    def task_view(self) -> None:
        logger.debug("NullDesktopExecutor: task_view")

    def execute_shortcut(self, shortcut: str) -> None:
        logger.debug("NullDesktopExecutor: execute_shortcut(%s)", shortcut)


class WindowsDesktopExecutor(IOSDesktopExecutor):
    """
    Windows OS desktop executor using ctypes user32 API.
    """

    # Win32 Constants
    MOUSEEVENTF_LEFTDOWN   = 0x0002
    MOUSEEVENTF_LEFTUP     = 0x0004
    MOUSEEVENTF_RIGHTDOWN  = 0x0008
    MOUSEEVENTF_RIGHTUP    = 0x0010
    MOUSEEVENTF_WHEEL      = 0x0800

    VK_LBUTTON = 0x01
    VK_RBUTTON = 0x02
    VK_TAB     = 0x09
    VK_SHIFT   = 0x10
    VK_CONTROL = 0x11
    VK_MENU    = 0x12  # Alt
    VK_LWIN    = 0x5B

    VK_VOLUME_MUTE       = 0xAD
    VK_VOLUME_DOWN       = 0xAE
    VK_VOLUME_UP         = 0xAF
    VK_MEDIA_NEXT_TRACK  = 0xB0
    VK_MEDIA_PREV_TRACK  = 0xB1
    VK_MEDIA_PLAY_PAUSE  = 0xB3

    KEYEVENTF_KEYUP = 0x0002

    def __init__(self) -> None:
        import ctypes
        self._user32 = ctypes.windll.user32

    def get_screen_size(self) -> Tuple[int, int]:
        try:
            w = self._user32.GetSystemMetrics(0)
            h = self._user32.GetSystemMetrics(1)
            return (w if w > 0 else 1920, h if h > 0 else 1080)
        except Exception as exc:
            logger.warning("WindowsDesktopExecutor: error getting screen size: %s", exc)
            return (1920, 1080)

    def set_cursor_pos(self, x: int, y: int) -> None:
        try:
            self._user32.SetCursorPos(int(x), int(y))
        except Exception as exc:
            logger.warning("WindowsDesktopExecutor: error setting cursor pos: %s", exc)

    def left_click(self) -> None:
        try:
            self._user32.mouse_event(self.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.01)
            self._user32.mouse_event(self.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except Exception as exc:
            logger.warning("WindowsDesktopExecutor: left_click error: %s", exc)

    def right_click(self) -> None:
        try:
            self._user32.mouse_event(self.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(0.01)
            self._user32.mouse_event(self.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        except Exception as exc:
            logger.warning("WindowsDesktopExecutor: right_click error: %s", exc)

    def double_click(self) -> None:
        self.left_click()
        time.sleep(0.05)
        self.left_click()

    def mouse_down(self) -> None:
        try:
            self._user32.mouse_event(self.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        except Exception as exc:
            logger.warning("WindowsDesktopExecutor: mouse_down error: %s", exc)

    def mouse_up(self) -> None:
        try:
            self._user32.mouse_event(self.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except Exception as exc:
            logger.warning("WindowsDesktopExecutor: mouse_up error: %s", exc)

    def scroll(self, delta: int) -> None:
        try:
            # delta: positive = up, negative = down. Wheel click is 120 units
            amount = delta * 120
            self._user32.mouse_event(self.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
        except Exception as exc:
            logger.warning("WindowsDesktopExecutor: scroll error: %s", exc)

    def _send_vk(self, vk_code: int) -> None:
        try:
            self._user32.keybd_event(vk_code, 0, 0, 0)
            time.sleep(0.01)
            self._user32.keybd_event(vk_code, 0, self.KEYEVENTF_KEYUP, 0)
        except Exception as exc:
            logger.warning("WindowsDesktopExecutor: send_vk error: %s", exc)

    def volume_up(self) -> None:
        self._send_vk(self.VK_VOLUME_UP)

    def volume_down(self) -> None:
        self._send_vk(self.VK_VOLUME_DOWN)

    def mute(self) -> None:
        self._send_vk(self.VK_VOLUME_MUTE)

    def play_pause(self) -> None:
        self._send_vk(self.VK_MEDIA_PLAY_PAUSE)

    def next_track(self) -> None:
        self._send_vk(self.VK_MEDIA_NEXT_TRACK)

    def prev_track(self) -> None:
        self._send_vk(self.VK_MEDIA_PREV_TRACK)

    def show_desktop(self) -> None:
        try:
            # Win + D
            self._user32.keybd_event(self.VK_LWIN, 0, 0, 0)
            self._user32.keybd_event(ord('D'), 0, 0, 0)
            time.sleep(0.01)
            self._user32.keybd_event(ord('D'), 0, self.KEYEVENTF_KEYUP, 0)
            self._user32.keybd_event(self.VK_LWIN, 0, self.KEYEVENTF_KEYUP, 0)
        except Exception as exc:
            logger.warning("WindowsDesktopExecutor: show_desktop error: %s", exc)

    def task_view(self) -> None:
        try:
            # Win + Tab
            self._user32.keybd_event(self.VK_LWIN, 0, 0, 0)
            self._user32.keybd_event(self.VK_TAB, 0, 0, 0)
            time.sleep(0.01)
            self._user32.keybd_event(self.VK_TAB, 0, self.KEYEVENTF_KEYUP, 0)
            self._user32.keybd_event(self.VK_LWIN, 0, self.KEYEVENTF_KEYUP, 0)
        except Exception as exc:
            logger.warning("WindowsDesktopExecutor: task_view error: %s", exc)

    def execute_shortcut(self, shortcut: str) -> None:
        """Parse key string like 'ctrl+c' or 'alt+tab' and press keys."""
        if not shortcut:
            return
        keys = [k.strip().lower() for k in shortcut.split("+") if k.strip()]
        mod_vks = []
        key_vks = []

        vk_map = {
            "ctrl": self.VK_CONTROL,
            "control": self.VK_CONTROL,
            "alt": self.VK_MENU,
            "shift": self.VK_SHIFT,
            "win": self.VK_LWIN,
            "tab": self.VK_TAB,
        }

        for k in keys:
            if k in vk_map:
                mod_vks.append(vk_map[k])
            elif len(k) == 1:
                key_vks.append(ord(k.upper()))

        try:
            for m in mod_vks:
                self._user32.keybd_event(m, 0, 0, 0)
            for k in key_vks:
                self._user32.keybd_event(k, 0, 0, 0)

            time.sleep(0.02)

            for k in reversed(key_vks):
                self._user32.keybd_event(k, 0, self.KEYEVENTF_KEYUP, 0)
            for m in reversed(mod_vks):
                self._user32.keybd_event(m, 0, self.KEYEVENTF_KEYUP, 0)
        except Exception as exc:
            logger.warning("WindowsDesktopExecutor: execute_shortcut error: %s", exc)


def get_desktop_executor() -> IOSDesktopExecutor:
    """
    Factory function returning native Windows desktop executor or Null fallback.
    """
    if sys.platform.startswith("win"):
        try:
            return WindowsDesktopExecutor()
        except Exception as exc:
            logger.warning("Failed to instantiate WindowsDesktopExecutor: %s. Using NullDesktopExecutor.", exc)
            return NullDesktopExecutor()
    return NullDesktopExecutor()
