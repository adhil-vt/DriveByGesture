"""
gesturedrive.core.exceptions
=============================
Custom exception hierarchy for GestureDrive.

All exceptions inherit from GestureDriveError, allowing callers to catch
the entire family with a single except clause when needed.

Recovery policies are documented per class; see Architecture §9.
"""

from __future__ import annotations


class GestureDriveError(Exception):
    """Base exception for every GestureDrive-originated error."""


# ── Hardware / I/O layer ───────────────────────────────────────────────────────

class CaptureError(GestureDriveError):
    """
    Raised when the camera cannot be opened, a frame cannot be read,
    or the capture thread experiences a fatal I/O fault.

    Recovery policy: retry up to 3 times, then switch to NullController
    and publish an ErrorEvent to notify the UI.
    """


class TrackingError(GestureDriveError):
    """
    Raised when the hand-tracking model fails to initialise or process
    a frame (e.g., MediaPipe model files are missing or corrupted).

    Recovery policy: skip the offending frame; if persistent, alert the UI.
    """


# ── Gesture layer ──────────────────────────────────────────────────────────────

class GestureError(GestureDriveError):
    """
    Raised when a gesture recognizer throws an unexpected exception during
    recognition.

    Recovery policy: skip that recognizer's output for the current frame
    and log at ERROR level.
    """


# ── Controller layer ───────────────────────────────────────────────────────────

class ControllerError(GestureDriveError):
    """
    Raised when the virtual controller cannot be created or when sending
    an input fails (e.g., ViGEmBus driver not installed).

    Recovery policy: fall back to NullController; publish ErrorEvent.
    """


# ── Plugin layer ───────────────────────────────────────────────────────────────

class PluginError(GestureDriveError):
    """
    Raised when a game plugin fails to load, validate, or activate.

    Recovery policy: skip the broken plugin, warn the user, continue with
    the previous active plugin or no plugin.
    """


# ── Configuration layer ────────────────────────────────────────────────────────

class ConfigError(GestureDriveError):
    """
    Raised when a configuration file is malformed, contains an unknown key,
    or fails schema validation.

    Recovery policy: discard the bad change, retain the last known-good
    config, and warn the user via the UI status bar.
    """


# ── Calibration layer ──────────────────────────────────────────────────────────

class CalibrationError(GestureDriveError):
    """
    Raised when a calibration session cannot be completed (e.g., hand not
    visible, insufficient frames captured, validation failed).
    """
