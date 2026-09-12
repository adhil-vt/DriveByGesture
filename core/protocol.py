"""
gesturedrive.core.protocol
==========================
Windows Custom URL Protocol Handler & Single-Instance Mutex.

Registers and manages the per-user Windows URL protocol:
    rageware-gesture-drive://launch

Architecture & Security:
- Per-user registration under HKEY_CURRENT_USER (no admin privileges required).
- Dynamic detection of executable path (distinguishes PyInstaller frozen bundle from source).
- Strict whitelist URL validation (only 'launch' action allowed, arbitrary execution prevented).
- Idempotent registration: updates registry only when the target path changes.
- Safe single-instance enforcement via named Windows Mutex (brings existing instance to focus).
- Clean unregistration utility for protocol removal.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

PROTOCOL_NAME: str = "rageware-gesture-drive"
PROTOCOL_DESCRIPTION: str = "URL:DriveByGesture Protocol"
REGISTRY_SUBKEY: str = rf"Software\Classes\{PROTOCOL_NAME}"
MUTEX_NAME: str = r"Local\DriveByGesture_SingleInstance_Mutex"

# Global reference to hold mutex handle open for application lifetime
_SINGLE_INSTANCE_MUTEX: Any = None


def get_target_executable_path() -> Path:
    """
    Dynamically determine the absolute path to the target executable.

    When frozen by PyInstaller, sys.executable points directly to the running
    DriveByGesture.exe, regardless of the folder it was extracted to or run from.
    When running from Python source, searches for the built dist executable first,
    or returns sys.executable as fallback.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()

    # Source development mode: check if packaged EXE exists in dist
    project_root = Path(__file__).resolve().parent.parent
    dist_exe = project_root / "dist" / "DriveByGesture" / "DriveByGesture.exe"
    if dist_exe.is_file():
        return dist_exe.resolve()

    return Path(sys.executable).resolve()


def get_expected_command(target_path: Optional[Path] = None) -> str:
    """
    Construct the command line string registered in the Windows registry.
    Handles quoting to properly support paths with spaces.
    """
    resolved_path = target_path or get_target_executable_path()

    if getattr(sys, "frozen", False) or resolved_path.suffix.lower() == ".exe":
        return f'"{resolved_path}" "%1"'

    # When running raw python without an exe, point to app.py
    project_root = Path(__file__).resolve().parent.parent
    app_py = project_root / "app.py"
    return f'"{resolved_path}" "{app_py}" "%1"'


def is_url_protocol_registered(expected_cmd: Optional[str] = None) -> bool:
    """
    Check if rageware-gesture-drive protocol is already registered
    in HKEY_CURRENT_USER pointing to the expected command.
    """
    if sys.platform != "win32":
        return False

    import winreg

    if expected_cmd is None:
        expected_cmd = get_expected_command()

    try:
        command_key_path = rf"{REGISTRY_SUBKEY}\shell\open\command"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, command_key_path, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, "")
            return val.strip().lower() == expected_cmd.strip().lower()
    except OSError:
        return False


def register_url_protocol(target_path: Optional[Path] = None) -> bool:
    """
    Register the rageware-gesture-drive custom URL protocol in HKEY_CURRENT_USER.

    This function is:
    - Silent: Does not trigger UAC or popup dialogs.
    - Per-user: Operates strictly in HKEY_CURRENT_USER, requiring no administrator elevation.
    - Idempotent: If already registered to the current target path, does nothing.
    - Relocation-safe: If the app was moved, seamlessly updates the registration.
    """
    if sys.platform != "win32":
        logger.debug("Skipping URL protocol registration: platform is not win32")
        return False

    import winreg

    target = target_path or get_target_executable_path()
    expected_cmd = get_expected_command(target)

    # Check if already registered correctly
    if is_url_protocol_registered(expected_cmd):
        logger.debug("Protocol '%s' already registered with current executable.", PROTOCOL_NAME)
        return True

    try:
        # Base key: HKCU\Software\Classes\rageware-gesture-drive
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_SUBKEY) as base_key:
            winreg.SetValueEx(base_key, "", 0, winreg.REG_SZ, PROTOCOL_DESCRIPTION)
            winreg.SetValueEx(base_key, "URL Protocol", 0, winreg.REG_SZ, "")

        # DefaultIcon (if pointing to an executable)
        if target.suffix.lower() == ".exe":
            icon_key_path = rf"{REGISTRY_SUBKEY}\DefaultIcon"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, icon_key_path) as icon_key:
                winreg.SetValueEx(icon_key, "", 0, winreg.REG_SZ, f'"{target}",0')

        # Shell command: HKCU\Software\Classes\rageware-gesture-drive\shell\open\command
        command_key_path = rf"{REGISTRY_SUBKEY}\shell\open\command"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, command_key_path) as cmd_key:
            winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, expected_cmd)

        logger.info(
            "Successfully registered URL protocol '%s' -> %s",
            PROTOCOL_NAME,
            expected_cmd,
        )
        return True
    except OSError as err:
        logger.warning("Failed to register Windows URL protocol '%s': %s", PROTOCOL_NAME, err)
        return False


def _delete_registry_tree(root_key: Any, subkey_path: str) -> None:
    """Recursively delete a Windows registry key and all subkeys."""
    import winreg

    try:
        with winreg.OpenKey(root_key, subkey_path, 0, winreg.KEY_ALL_ACCESS) as key:
            while True:
                try:
                    child_name = winreg.EnumKey(key, 0)
                    _delete_registry_tree(key, child_name)
                except OSError:
                    break
        winreg.DeleteKey(root_key, subkey_path)
    except FileNotFoundError:
        pass


def unregister_url_protocol() -> bool:
    """
    Remove the rageware-gesture-drive protocol from HKEY_CURRENT_USER.
    Used for uninstallation / cleanup.
    """
    if sys.platform != "win32":
        return False

    import winreg

    try:
        _delete_registry_tree(winreg.HKEY_CURRENT_USER, REGISTRY_SUBKEY)
        logger.info("Successfully unregistered URL protocol '%s'.", PROTOCOL_NAME)
        return True
    except OSError as err:
        logger.warning("Failed to unregister URL protocol '%s': %s", PROTOCOL_NAME, err)
        return False


def validate_protocol_url(url_string: str) -> bool:
    """
    Strict security validation for incoming protocol URLs.

    Rules:
    - Scheme must match PROTOCOL_NAME ('rageware-gesture-drive').
    - Action/path must strictly match 'launch' (case-insensitive).
    - Arbitrary executables, commands, arguments, or paths are rejected.
    """
    if not url_string or not isinstance(url_string, str):
        return False

    clean_url = url_string.strip().rstrip("/")
    try:
        parsed = urlparse(clean_url)
    except Exception as err:
        logger.warning("Failed to parse URL '%s': %s", url_string, err)
        return False

    scheme = (parsed.scheme or "").lower()
    if scheme != PROTOCOL_NAME:
        return False

    netloc = (parsed.netloc or "").lower()
    path = (parsed.path or "").strip("/").lower()

    # Must be either:
    # 1. netloc == "launch" and path is empty (e.g. rageware-gesture-drive://launch)
    # 2. netloc is empty and path == "launch" (e.g. rageware-gesture-drive:launch or rageware-gesture-drive:///launch)
    is_launch = (netloc == "launch" and not path) or (not netloc and path == "launch")

    # Reject unknown actions, extra subpaths, query strings, or fragments
    if is_launch and not parsed.query and not parsed.fragment:
        return True

    logger.warning("Security rejected unauthorized protocol URL action or parameters: '%s'", clean_url)
    return False


def check_or_create_single_instance(window_title: str = "DriveByGesture") -> Tuple[bool, Any]:
    """
    Enforces single-instance behavior on Windows using a named Win32 mutex.

    If another instance is already running:
    - Finds the existing application window.
    - Restores and brings it to the foreground.
    - Returns (False, None).

    If this is the first instance:
    - Keeps the mutex handle open for the lifetime of the process.
    - Returns (True, mutex_handle).
    """
    global _SINGLE_INSTANCE_MUTEX

    if sys.platform != "win32":
        return True, None

    import ctypes
    from ctypes import wintypes

    ERROR_ALREADY_EXISTS = 183
    SW_RESTORE = 9

    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = kernel32.GetLastError()

    if last_error == ERROR_ALREADY_EXISTS:
        logger.info("Another instance of DriveByGesture is already running.")
        # Activate existing window
        try:
            hwnd = user32.FindWindowW(None, window_title)
            if hwnd:
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.SetForegroundWindow(hwnd)
        except Exception as err:
            logger.debug("Could not bring existing window to foreground: %s", err)
        return False, None

    _SINGLE_INSTANCE_MUTEX = mutex
    return True, mutex
