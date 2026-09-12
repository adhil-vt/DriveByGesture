"""
gesturedrive.core.version
==========================
Single Source of Truth for Application Versioning, Metadata, and Branding Identity.

No version string or application branding metadata should be duplicated anywhere
else in the project codebase.
"""

from __future__ import annotations

from typing import Dict

# ── Application Branding & Version Information ────────────────────────────────
APP_NAME: str = "DriveByGesture"
VERSION: str = "1.0.0"
BUILD_NUMBER: str = "2026.08.03-RC1"
RELEASE_CHANNEL: str = "Release Candidate"
BUILD_DATE: str = "2026-08-03"

DEVELOPER: str = "Google Deepmind / DriveByGesture Team"
COMPANY: str = "DriveByGesture Open Source Project"
COPYRIGHT: str = "© 2026 DriveByGesture Project. All Rights Reserved."
LICENSE: str = "MIT License"
WEBSITE: str = "https://github.com/adhil-vt/DriveByGesture"
REPOSITORY_URL: str = "https://github.com/adhil-vt/DriveByGesture"


def get_window_title(subtitle: str = "") -> str:
    """
    Standardize window titles across all windows and dialogs.

    Examples
    --------
    >>> get_window_title()
    'DriveByGesture'
    >>> get_window_title("Settings")
    'Settings — DriveByGesture'
    >>> get_window_title("Calibration Wizard")
    'Calibration Wizard — DriveByGesture'
    """
    subtitle_str = subtitle.strip()
    if not subtitle_str or subtitle_str == APP_NAME:
        return APP_NAME
    return f"{subtitle_str} — {APP_NAME}"


def get_version_info() -> Dict[str, str]:
    """Return dictionary of all application version metadata."""
    return {
        "app_name": APP_NAME,
        "version": VERSION,
        "build_number": BUILD_NUMBER,
        "release_channel": RELEASE_CHANNEL,
        "build_date": BUILD_DATE,
        "developer": DEVELOPER,
        "company": COMPANY,
        "copyright": COPYRIGHT,
        "license": LICENSE,
        "website": WEBSITE,
        "repository_url": REPOSITORY_URL,
    }
