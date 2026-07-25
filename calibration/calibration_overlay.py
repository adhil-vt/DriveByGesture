"""
gesturedrive.calibration.calibration_overlay
=============================================
Overlay renderer for the interactive Calibration Wizard and Review Screen.
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
    font = cv2.FONT_HERSHEY_SIMPLEX

    white = (255, 255, 255)
    yellow = (0, 255, 255)
    green = (0, 255, 120)
    red = (0, 0, 255)
    cyan = (255, 255, 0)
    gray = (180, 180, 180)

    # 1. Review Screen overlay (SUMMARY or COMPLETE step)
    if snapshot.step in (CalibrationStep.SUMMARY, CalibrationStep.COMPLETE):
        card_w = int(w * 0.65)
        card_h = 240
        card_x = (w - card_w) // 2
        card_y = (h - card_h) // 2

        overlay = image.copy()
        cv2.rectangle(overlay, (card_x, card_y), (card_x + card_w, card_y + card_h), (15, 15, 25), -1)
        cv2.addWeighted(overlay, 0.90, image, 0.10, 0, image)
        cv2.rectangle(image, (card_x, card_y), (card_x + card_w, card_y + card_h), (0, 200, 255), 2)

        title = "CALIBRATION SAVED" if snapshot.step == CalibrationStep.COMPLETE else "CALIBRATION REVIEW"
        cv2.putText(image, title, (card_x + 30, card_y + 35), font, 0.75, green if snapshot.step == CalibrationStep.COMPLETE else yellow, 2, cv2.LINE_AA)

        y = card_y + 75
        cv2.putText(image, f"Center Angle:             {snapshot.captured_value:+.1f} deg" if snapshot.captured_value is not None else "Center Angle:             --", (card_x + 30, y), font, 0.55, white, 1, cv2.LINE_AA)
        y += 30
        cv2.putText(image, f"Estimated Steering Range: {snapshot.total_steering_range:.1f} deg" if snapshot.total_steering_range is not None else "Estimated Steering Range: --", (card_x + 30, y), font, 0.55, cyan, 1, cv2.LINE_AA)
        y += 30
        cv2.putText(image, "Saved to:                 profiles/default_calibration.json", (card_x + 30, y), font, 0.50, green, 1, cv2.LINE_AA)
        y += 40

        # Controls bar
        cv2.rectangle(image, (card_x + 15, y - 10), (card_x + card_w - 15, y + 40), (40, 40, 40), -1)
        ctrl_str = "Calibration Saved: profiles/default_calibration.json" if snapshot.step == CalibrationStep.COMPLETE else "[S] Save Calibration   [R] Recalibrate   [ESC] Cancel"
        cv2.putText(image, ctrl_str, (card_x + 30, y + 22), font, 0.50, green, 2, cv2.LINE_AA)
        return

    # 2. Main Calibration Step HUD Panel
    panel_w = int(w * 0.75)
    panel_h = 190
    panel_x = (w - panel_w) // 2
    panel_y = 25

    overlay = image.copy()
    cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.85, image, 0.15, 0, image)

    border_color = (0, 200, 255) if not snapshot.error_message else red
    cv2.rectangle(image, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), border_color, 2)

    # Header line
    header_str = f"STEERING CALIBRATION WIZARD   |   Step {snapshot.step_number} / {snapshot.total_steps}"
    cv2.putText(image, header_str, (panel_x + 20, panel_y + 30), font, 0.65, yellow, 2, cv2.LINE_AA)

    # Instruction line
    cv2.putText(image, snapshot.displayed_instruction, (panel_x + 20, panel_y + 65), font, 0.60, white, 1, cv2.LINE_AA)

    # Live telemetry
    telem_str = f"Current Angle: {snapshot.live_angle:+.1f} deg   |   Target: {snapshot.target_direction}   |   Detected: {snapshot.detected_direction}   |   Camera: {snapshot.camera_mode}"
    cv2.putText(image, telem_str, (panel_x + 20, panel_y + 98), font, 0.50, (200, 220, 255), 1, cv2.LINE_AA)

    # Status / Guidance line
    status_color = green if "✓" in snapshot.status_message or "Holding" in snapshot.status_message else (yellow if not snapshot.error_message else red)
    cv2.putText(image, f"Status: {snapshot.status_message}", (panel_x + 20, panel_y + 130), font, 0.52, status_color, 1, cv2.LINE_AA)

    # Progress bar
    bar_x = panel_x + 20
    bar_y = panel_y + 150
    bar_w = panel_w - 40
    bar_h = 12
    cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 60, 60), -1)
    fill_w = int(bar_w * snapshot.completion_ratio)
    if fill_w > 0:
        cv2.rectangle(image, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), green, -1)

    # Error alert banner at bottom if error
    if snapshot.error_message:
        cv2.putText(image, f"ALERT: {snapshot.error_message}", (panel_x + 20, panel_y + 178), font, 0.48, red, 1, cv2.LINE_AA)

