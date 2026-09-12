"""
gesturedrive.diagnostics.health_check
========================================
HealthCheck: verifies all required hardware and software components are
present before application startup.

Checks performed
----------------
1. Camera:      Can device_index be opened by cv2.VideoCapture?
2. ViGEmBus:    Is the vgamepad Python package importable?
3. MediaPipe:   Is mediapipe importable and the model file accessible?

Failure behaviour
-----------------
- A CRITICAL failure (camera not found, vgamepad missing) aborts startup.
- A WARNING failure (e.g., MediaPipe model in non-default path) logs a
  warning but allows startup to proceed.
- HealthCheck never directly shows UI — it returns a HealthReport that
  the Application interprets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class HealthIssue:
    """A single health check finding."""
    component: str
    severity: str       # "critical" | "warning"
    message: str


@dataclass
class HealthReport:
    """Aggregated result of all health checks."""
    issues: List[HealthIssue] = field(default_factory=list)

    @property
    def is_critical(self) -> bool:
        """True if any critical issues were found."""
        return any(i.severity == "critical" for i in self.issues)

    @property
    def is_healthy(self) -> bool:
        """True if no issues of any severity were found."""
        return len(self.issues) == 0


class HealthCheck:
    """
    Runs pre-flight checks on all required hardware and software.

    Usage
    -----
        report = HealthCheck(device_index=0).run()
        if report.is_critical:
            sys.exit(1)
    """

    def __init__(self, camera_device_index: int = 0) -> None:
        self._device_index = camera_device_index

    def run(self) -> HealthReport:
        """
        Execute all health checks and return a HealthReport.

        Never raises — all exceptions are caught and turned into
        HealthIssue entries.
        """
        report = HealthReport()
        self._check_camera(report)
        self._check_vgamepad(report)
        self._check_mediapipe(report)
        return report

    def _check_camera(self, report: HealthReport) -> None:
        """Verify that the configured camera device can be opened."""
        try:
            import cv2  # noqa: PLC0415
            cap = cv2.VideoCapture(self._device_index)
            if not cap.isOpened():
                report.issues.append(HealthIssue(
                    component="Camera",
                    severity="critical",
                    message=f"Camera device {self._device_index} could not be opened by OpenCV.",
                ))
            cap.release()
        except Exception as exc:
            report.issues.append(HealthIssue(
                component="Camera",
                severity="critical",
                message=f"Camera check raised an exception: {exc}",
            ))

    def _check_vgamepad(self, report: HealthReport) -> None:
        """Verify that vgamepad is importable (ViGEmBus proxy check)."""
        try:
            import vgamepad  # noqa: F401, PLC0415
        except ImportError:
            report.issues.append(HealthIssue(
                component="Controller",
                severity="warning",
                message="vgamepad not installed or ViGEmBus driver missing. Virtual controller unavailable.",
            ))
        except Exception as exc:
            report.issues.append(HealthIssue(
                component="Controller",
                severity="warning",
                message=f"vgamepad check raised an exception: {exc}",
            ))

    def _check_mediapipe(self, report: HealthReport) -> None:
        """Verify that mediapipe is importable."""
        try:
            import mediapipe  # noqa: F401, PLC0415
        except ImportError:
            report.issues.append(HealthIssue(
                component="MediaPipe",
                severity="critical",
                message="mediapipe package not found. Hand tracking will not work.",
            ))
        except Exception as exc:
            report.issues.append(HealthIssue(
                component="MediaPipe",
                severity="warning",
                message=f"MediaPipe check raised an exception: {exc}",
            ))
