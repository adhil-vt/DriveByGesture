"""
gesturedrive.calibration.calibration_overlay
=============================================
Overlay renderer for the interactive Calibration Wizard.
"""

from __future__ import annotations

import cv2
import numpy as np

from calibration.calibration_session import CalibrationStep, StepSnapshot


def render_calibration_overlay(image: np.ndarray, snapshot: StepSnapshot) -> None:
    """
    Render visual calibration HUD overlay onto an OpenCV BGR image frame.

    Parameters
    ----------
    image: np.ndarray
        BGR image array (modified in-place).
    snapshot: StepSnapshot
        Current frame snapshot from CalibrationSession.
    """
    if snapshot.step == CalibrationStep.NOT_STARTED:
        return

    h, w = image.shape[:2]

    # Panel dimensions
    panel_w = int(w * 0.70)
    panel_h = 180
    panel_x = (w - panel_w) // 2
    panel_y = 30

    # Draw semi-transparent background box
    overlay = image.copy()
    cv2.rectangle(
        overlay,
        (panel_x, panel_y),
        (panel_x + panel_w, panel_y + panel_h),
        (20, 20, 20),
        -1,
    )
    cv2.addWeighted(overlay, 0.85, image, 0.15, 0, image)
    cv2.rectangle(
        image,
        (panel_x, panel_y),
        (panel_x + panel_w, panel_y + panel_h),
        (0, 200, 255),
        2,
    )

    font = cv2.FONT_HERSHEY_SIMPLEX
    white = (255, 255, 255)
    yellow = (0, 255, 255)
    green = (0, 255, 120)
    red = (0, 0, 255)

    # Title
    cv2.putText(
        image,
        "STEERING CALIBRATION WIZARD",
        (panel_x + 20, panel_y + 30),
        font,
        0.65,
        yellow,
        2,
        cv2.LINE_AA,
    )

    # Step instruction
    cv2.putText(
        image,
        snapshot.instruction,
        (panel_x + 20, panel_y + 65),
        font,
        0.60,
        white,
        1,
        cv2.LINE_AA,
    )

    # Live metrics line
    metrics_str = f"Live Angle: {snapshot.live_angle:+.1f} deg"
    if snapshot.captured_value is not None:
        metrics_str += f" | Captured: {snapshot.captured_value:+.1f} deg"

    cv2.putText(
        image,
        metrics_str,
        (panel_x + 20, panel_y + 100),
        font,
        0.52,
        (200, 220, 255),
        1,
        cv2.LINE_AA,
    )

    # Countdown / Badge display
    if snapshot.step in (CalibrationStep.CENTER, CalibrationStep.LEFT, CalibrationStep.RIGHT):
        cd_str = f"Countdown: {snapshot.countdown_seconds}s"
        cv2.putText(
            image,
            cd_str,
            (panel_x + panel_w - 180, panel_y + 30),
            font,
            0.65,
            (0, 255, 0) if snapshot.countdown_seconds > 0 else yellow,
            2,
            cv2.LINE_AA,
        )

        # Progress bar
        bar_x = panel_x + 20
        bar_y = panel_y + 120
        bar_w = panel_w - 40
        bar_h = 12
        cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 60, 60), -1)
        fill_w = int(bar_w * snapshot.completion_ratio)
        if fill_w > 0:
            cv2.rectangle(image, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), (0, 220, 100), -1)

    elif snapshot.step == CalibrationStep.COMPLETE:
        cv2.putText(
            image,
            "✓ Calibration Complete",
            (panel_x + panel_w - 240, panel_y + 30),
            font,
            0.65,
            green,
            2,
            cv2.LINE_AA,
        )

    # Error message warning
    if snapshot.error_message:
        cv2.putText(
            image,
            f"WARNING: {snapshot.error_message}",
            (panel_x + 20, panel_y + 155),
            font,
            0.50,
            red,
            1,
            cv2.LINE_AA,
        )
