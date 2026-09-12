"""
gesturedrive.core.resources
============================
Centralized Resource and Icon Manager.

Handles PyInstaller sys._MEIPASS resource paths, icon loading, branding assets,
and window icon application across all Qt dialogs and main windows.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


def get_base_dir() -> Path:
    """Return base directory (handles PyInstaller _MEIPASS bundle directory)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_resource_path(relative_path: str) -> Path:
    """Return resolved absolute path to a read-only bundled resource file."""
    return get_base_dir() / relative_path


# ── User Writable Data Locations (%LOCALAPPDATA%\DriveByGesture) ─────────────

def get_user_data_dir() -> Path:
    r"""
    Return the writable per-user application data directory.
    On Windows: %LOCALAPPDATA%\DriveByGesture (e.g. C:\Users\<User>\AppData\Local\DriveByGesture)
    Fallback: ~/.drivebygesture or APPDATA.
    """
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base = Path(local_app_data)
        else:
            app_data = os.environ.get("APPDATA")
            base = Path(app_data) if app_data else Path.home()
        data_dir = base / "DriveByGesture"
    else:
        data_dir = Path.home() / ".local" / "share" / "DriveByGesture"

    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        logger.warning("Could not create user data directory '%s': %s", data_dir, err)
    return data_dir


def get_user_profiles_dir() -> Path:
    r"""Return Path to writable profiles directory in %LOCALAPPDATA%\DriveByGesture\profiles."""
    p = get_user_data_dir() / "profiles"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_user_profile_storage_dir() -> Path:
    r"""Return Path to user profile JSON storage directory (%LOCALAPPDATA%\DriveByGesture\profiles\user)."""
    p = get_user_profiles_dir() / "user"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_active_profile_path() -> Path:
    r"""Return Path to active_profile.txt state file in %LOCALAPPDATA%\DriveByGesture\profiles."""
    return get_user_profiles_dir() / "active_profile.txt"


def get_active_mode_path() -> Path:
    r"""Return Path to active_mode.txt state file in %LOCALAPPDATA%\DriveByGesture\profiles."""
    return get_user_profiles_dir() / "active_mode.txt"


def get_default_calibration_path() -> Path:
    r"""Return Path to default_calibration.json in %LOCALAPPDATA%\DriveByGesture\profiles."""
    return get_user_profiles_dir() / "default_calibration.json"


def get_user_logs_dir() -> Path:
    r"""Return Path to logs directory in %LOCALAPPDATA%\DriveByGesture\logs."""
    p = get_user_data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_user_crash_reports_dir() -> Path:
    r"""Return Path to crash_reports directory in %LOCALAPPDATA%\DriveByGesture\crash_reports."""
    p = get_user_data_dir() / "crash_reports"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_game_prefs_path() -> Path:
    r"""Return Path to detection_prefs.json in %LOCALAPPDATA%\DriveByGesture\games."""
    p = get_user_data_dir() / "games"
    p.mkdir(parents=True, exist_ok=True)
    return p / "detection_prefs.json"


def ensure_user_data_migrated() -> None:
    r"""
    Safely seed / migrate initial user data into %LOCALAPPDATA%\DriveByGesture\profiles
    from bundled templates or existing legacy workspace directories.

    Guarantees:
    - Does NOT overwrite existing files in %LOCALAPPDATA%\DriveByGesture.
    - Does NOT delete old files.
    - Operates completely independent of the process working directory (CWD).
    """
    profiles_dest = get_user_profiles_dir()
    user_storage_dest = get_user_profile_storage_dir()

    source_candidates = [
        get_resource_path("profiles"),
        Path(__file__).resolve().parent.parent / "profiles",
    ]

    for src_dir in source_candidates:
        if not src_dir.is_dir():
            continue

        # 1. default_calibration.json
        cal_dest = profiles_dest / "default_calibration.json"
        cal_src = src_dir / "default_calibration.json"
        if not cal_dest.exists() and cal_src.is_file():
            try:
                shutil.copy2(cal_src, cal_dest)
                logger.info("Migrated default calibration to %s", cal_dest)
            except OSError:
                pass

        # 2. active_mode.txt
        mode_dest = profiles_dest / "active_mode.txt"
        mode_src = src_dir / "active_mode.txt"
        if not mode_dest.exists() and mode_src.is_file():
            try:
                shutil.copy2(mode_src, mode_dest)
            except OSError:
                pass

        # 3. active_profile.txt
        act_dest = profiles_dest / "active_profile.txt"
        act_src = src_dir / "active_profile.txt"
        if not act_dest.exists() and act_src.is_file():
            try:
                shutil.copy2(act_src, act_dest)
            except OSError:
                pass

        # 4. User profiles (profiles/user/*.json)
        src_user = src_dir / "user"
        if src_user.is_dir():
            for json_file in src_user.glob("*.json"):
                dest_file = user_storage_dest / json_file.name
                if not dest_file.exists():
                    try:
                        shutil.copy2(json_file, dest_file)
                        logger.info("Migrated profile '%s' to %s", json_file.name, dest_file)
                    except OSError:
                        pass


def ensure_resource_directories() -> None:
    """Ensure standard resources directory structure exists in development mode."""
    if getattr(sys, "frozen", False):
        return  # Frozen bundled resources are read-only
    try:
        base_res = get_base_dir() / "resources"
        subdirs = [
            "icons",
            "icons/toolbar",
            "icons/menu",
            "icons/status",
            "branding",
            "images",
            "logos",
        ]
        for sub in subdirs:
            (base_res / sub).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


# Initialize resource directories in dev mode
ensure_resource_directories()

_CACHED_APP_ICON: Optional[QIcon] = None


def create_fallback_app_icon() -> QIcon:
    """
    Generate high-resolution dynamic application icon (Electric Cyan Steering Wheel on Dark Slate background).
    Used when physical icon file is not present on disk.
    """
    size = 128
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Outer circle background
    painter.setBrush(QColor("#121620"))
    painter.setPen(QColor("#00e5ff"))
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # Inner cyan steering wheel ring
    painter.setPen(QColor("#00e5ff"))
    pen = painter.pen()
    pen.setWidth(8)
    painter.setPen(pen)
    painter.drawEllipse(18, 18, size - 36, size - 36)

    # Center hub
    painter.setBrush(QColor("#00e5ff"))
    painter.drawEllipse(size // 2 - 10, size // 2 - 10, 20, 20)

    # Steering spokes
    painter.drawLine(18, size // 2, size // 2 - 10, size // 2)
    painter.drawLine(size - 18, size // 2, size // 2 + 10, size // 2)
    painter.drawLine(size // 2, size // 2 + 10, size // 2, size - 18)

    painter.end()

    return QIcon(pixmap)


def get_app_icon() -> QIcon:
    """Return centralized application icon (cached)."""
    global _CACHED_APP_ICON
    if _CACHED_APP_ICON is not None:
        return _CACHED_APP_ICON

    ico_path = get_resource_path("resources/icons/app.ico")
    png_path = get_resource_path("resources/icons/app.png")

    if png_path.exists():
        _CACHED_APP_ICON = QIcon(str(png_path))
    elif ico_path.exists():
        _CACHED_APP_ICON = QIcon(str(ico_path))
    else:
        _CACHED_APP_ICON = create_fallback_app_icon()

    return _CACHED_APP_ICON


def apply_app_icon(widget: QWidget) -> None:
    """Apply standard application icon to a Qt window/dialog."""
    if widget is not None:
        widget.setWindowIcon(get_app_icon())
