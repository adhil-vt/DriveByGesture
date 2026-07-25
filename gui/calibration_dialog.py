"""
gesturedrive.gui.calibration_dialog
===================================
CalibrationDialog: Professional graphical setup wizard dialog for steering calibration.
"""

from __future__ import annotations

import logging
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from calibration.calibration_manager import CalibrationManager
from calibration.calibration_session import CalibrationStep, StepSnapshot
from gui.calibration_progress import CalibrationProgressWidget
from gui.calibration_review import ReviewWidget
from gui.camera_widget import CameraWidget
from gui.styles import DARK_THEME_QSS

logger = logging.getLogger(__name__)


class CalibrationDialog(QDialog):
    """
    Graphical Setup Wizard for Intelligent Steering Calibration.
    """

    def __init__(self, calibration_manager: CalibrationManager, parent=None) -> None:
        super().__init__(parent)
        self.manager = calibration_manager
        self.last_snapshot: StepSnapshot | None = None
        self._countdown_val: int = 3

        self.setWindowTitle("DriveByGesture — Calibration Wizard")
        self.resize(900, 650)
        self.setMinimumSize(850, 600)
        self.setModal(True)
        self.setStyleSheet(DARK_THEME_QSS)

        # Root Layout
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # 1. Header & Step Progress Bar
        self.progress_bar_widget = CalibrationProgressWidget()
        root_layout.addWidget(self.progress_bar_widget)

        # 2. Main Content Stack Container
        self.content_stack = QFrame()
        self.content_stack.setObjectName("statusCard")
        stack_layout = QVBoxLayout(self.content_stack)
        stack_layout.setContentsMargins(16, 14, 16, 14)
        stack_layout.setSpacing(10)

        # ----------------------------------------------------
        # PAGE 1: Welcome View
        # ----------------------------------------------------
        self.welcome_view = QWidget()
        welc_layout = QVBoxLayout(self.welcome_view)
        welc_layout.setContentsMargins(20, 20, 20, 20)
        welc_layout.setSpacing(16)
        welc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_w_title = QLabel("🎯   STEERING CALIBRATION WIZARD")
        lbl_w_title.setStyleSheet("color: #00e5ff; font-size: 22px; font-weight: 800;")
        lbl_w_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_w_desc = QLabel(
            "This wizard will calibrate your hand steering range for optimal, precise control.\n\n"
            "Steps:\n"
            "● Center Position    →    ● Maximum Left    →    ● Maximum Right    →    ● Review\n\n"
            "⏱  Estimated Time: 20–30 Seconds\n"
            "• Hold your hand comfortably in front of the camera during setup."
        )
        lbl_w_desc.setStyleSheet(
            "color: #d1d5db; font-size: 14px; line-height: 1.6; background: #11131a; "
            "padding: 20px; border-radius: 10px; border: 1px solid #282c3c;"
        )
        lbl_w_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        welc_layout.addWidget(lbl_w_title)
        welc_layout.addWidget(lbl_w_desc)

        # ----------------------------------------------------
        # PAGE 2: Pre-Calibration Countdown View
        # ----------------------------------------------------
        self.countdown_view = QWidget()
        count_layout = QVBoxLayout(self.countdown_view)
        count_layout.setContentsMargins(20, 20, 20, 20)
        count_layout.setSpacing(16)
        count_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_c_title = QLabel("GET READY")
        lbl_c_title.setStyleSheet("color: #ffb300; font-size: 24px; font-weight: 800;")
        lbl_c_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_c_sub = QLabel("Place your hand comfortably in front of the camera.")
        lbl_c_sub.setStyleSheet("color: #8f96a3; font-size: 15px;")
        lbl_c_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_countdown_big = QLabel("3")
        self.lbl_countdown_big.setStyleSheet("color: #00e5ff; font-size: 72px; font-weight: 900;")
        self.lbl_countdown_big.setAlignment(Qt.AlignmentFlag.AlignCenter)

        count_layout.addWidget(lbl_c_title)
        count_layout.addWidget(lbl_c_sub)
        count_layout.addWidget(self.lbl_countdown_big)

        # ----------------------------------------------------
        # PAGE 3: Active Wizard View (Camera Preview + Guidance)
        # ----------------------------------------------------
        self.wizard_view = QWidget()
        wiz_layout = QVBoxLayout(self.wizard_view)
        wiz_layout.setContentsMargins(0, 0, 0, 0)
        wiz_layout.setSpacing(10)

        self.lbl_instruction = QLabel("Hold your hand naturally in center position...")
        self.lbl_instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_instruction.setStyleSheet(
            "color: #00e5ff; font-size: 18px; font-weight: 700; background: #11131a; "
            "padding: 10px 16px; border-radius: 8px; border: 1px solid #282c3c;"
        )
        wiz_layout.addWidget(self.lbl_instruction)

        self.camera_widget = CameraWidget()
        self.camera_widget.overlay_enabled = False  # Keep preview feed clean (landmarks only)
        wiz_layout.addWidget(self.camera_widget, stretch=1)

        val_box = QHBoxLayout()
        val_box.setSpacing(12)

        self.lbl_hand_status = QLabel("🟢  Hand Detected")
        self.lbl_hand_status.setObjectName("statusChip")
        self.lbl_hand_status.setStyleSheet(
            "background-color: #11131a; color: #00e676; font-size: 12px; font-weight: 600; "
            "padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
        )

        self.lbl_status = QLabel("🟢  Tracking Stable")
        self.lbl_status.setObjectName("statusChip")
        self.lbl_status.setStyleSheet(
            "background-color: #11131a; color: #00e676; font-size: 12px; font-weight: 600; "
            "padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
        )

        self.pb_stability = QProgressBar()
        self.pb_stability.setRange(0, 100)
        self.pb_stability.setValue(0)
        self.pb_stability.setFormat("Hold Position: 0.0 / 2.0s (0%)")

        val_box.addWidget(self.lbl_hand_status)
        val_box.addWidget(self.lbl_status)
        val_box.addWidget(self.pb_stability, stretch=1)
        wiz_layout.addLayout(val_box)

        # ----------------------------------------------------
        # PAGE 4: Review View
        # ----------------------------------------------------
        self.review_widget = ReviewWidget()

        stack_layout.addWidget(self.welcome_view)
        stack_layout.addWidget(self.countdown_view)
        stack_layout.addWidget(self.wizard_view)
        stack_layout.addWidget(self.review_widget)
        root_layout.addWidget(self.content_stack, stretch=1)

        # 3. Bottom Controls
        self.control_box_widget = QWidget()
        control_box = QHBoxLayout(self.control_box_widget)
        control_box.setContentsMargins(0, 0, 0, 0)
        control_box.setSpacing(12)

        self.btn_start = QPushButton("▶   Start Calibration")
        self.btn_start.setObjectName("btnStart")

        self.btn_recalibrate = QPushButton("🔄   Recalibrate")
        self.btn_recalibrate.setObjectName("btnCalibrate")
        self.btn_recalibrate.setVisible(False)

        self.btn_cancel = QPushButton("✕   Cancel")
        self.btn_cancel.setObjectName("btnExit")

        control_box.addWidget(self.btn_start)
        control_box.addWidget(self.btn_recalibrate)
        control_box.addStretch()
        control_box.addWidget(self.btn_cancel)
        root_layout.addWidget(self.control_box_widget)

        # Connections
        self.btn_start.clicked.connect(self._on_start_calibration_clicked)
        self.btn_recalibrate.clicked.connect(self._on_recalibrate)
        self.btn_cancel.clicked.connect(self.reject)

        self.review_widget.save_requested.connect(self._on_save)
        self.review_widget.recalibrate_requested.connect(self._on_recalibrate)
        self.review_widget.cancel_requested.connect(self.reject)

        # Countdown Timer
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

        self._show_welcome_screen()

    def _show_welcome_screen(self) -> None:
        """Display clean Welcome screen without starting calibration session."""
        self.welcome_view.setVisible(True)
        self.countdown_view.setVisible(False)
        self.wizard_view.setVisible(False)
        self.review_widget.setVisible(False)

        self.btn_start.setVisible(True)
        self.btn_recalibrate.setVisible(False)
        self.control_box_widget.setVisible(True)
        self.progress_bar_widget.set_step(CalibrationStep.CENTER)

    def _on_start_calibration_clicked(self) -> None:
        """User clicked Start Calibration button on Welcome screen."""
        self.welcome_view.setVisible(False)
        self.countdown_view.setVisible(True)

        self._countdown_val = 3
        self.lbl_countdown_big.setText(str(self._countdown_val))
        self._countdown_timer.start()

    def _on_countdown_tick(self) -> None:
        """Tick pre-calibration countdown (3.. 2.. 1..)."""
        self._countdown_val -= 1
        if self._countdown_val > 0:
            self.lbl_countdown_big.setText(str(self._countdown_val))
        else:
            self._countdown_timer.stop()
            self._start_calibration_session()

    def _start_calibration_session(self) -> None:
        """Start actual calibration session with backend CalibrationManager."""
        try:
            self.manager.start_session()
            self.countdown_view.setVisible(False)
            self.wizard_view.setVisible(True)
            self.review_widget.setVisible(False)
            self.btn_start.setVisible(False)
            self.btn_recalibrate.setVisible(True)
            self.progress_bar_widget.set_step(CalibrationStep.CENTER)
            logger.info("CalibrationDialog: Calibration session started.")
        except Exception as exc:
            logger.error("Failed to start calibration session: %s", exc)
            QMessageBox.critical(self, "Calibration Error", f"Could not start calibration session: {exc}")

    def update_telemetry_frame(self, frame: np.ndarray, snapshot: StepSnapshot | None) -> None:
        """
        Real-time update slot called by MainWindow for each camera frame during calibration.
        """
        if frame is not None:
            self.camera_widget.update_frame(frame)

        if not snapshot or not self.wizard_view.isVisible():
            return

        self.last_snapshot = snapshot
        step = getattr(snapshot, "step", CalibrationStep.CENTER)

        # Update Step Indicator
        self.progress_bar_widget.set_step(step)

        # Instruction & Transition Countdown Banner (Top Panel is the ONLY instruction source)
        count_sec = getattr(snapshot, "countdown_seconds", 0)
        disp_instr = getattr(snapshot, "displayed_instruction", getattr(snapshot, "instruction", ""))
        err_msg = getattr(snapshot, "error_message", None)

        if count_sec > 0:
            banner_text = disp_instr or f"Prepare for next step in {count_sec}s..."
            self.lbl_instruction.setText(f"⏳   {banner_text}")
            self.lbl_instruction.setStyleSheet(
                "color: #ffb300; font-size: 20px; font-weight: 800; background: #1a160d; "
                "padding: 12px 16px; border-radius: 8px; border: 1px solid #ffb300;"
            )
        else:
            s_msg = getattr(snapshot, "status_message", "")
            if step == CalibrationStep.CENTER:
                if "Holding natural center" in s_msg or "Center Captured" in s_msg or "Holding stable" in s_msg:
                    user_msg = "✔ Natural Center — Hold position still"
                else:
                    user_msg = "✋ Place your hand in your natural, comfortable CENTER position"
            elif step == CalibrationStep.LEFT:
                user_msg = "↺ Rotate your hand fully LEFT to maximum lock"
            elif step == CalibrationStep.RIGHT:
                user_msg = "↻ Rotate your hand fully RIGHT to maximum lock"
            else:
                user_msg = disp_instr or "Follow calibration guidance..."

            self.lbl_instruction.setText(user_msg)
            self.lbl_instruction.setStyleSheet(
                "color: #00e5ff; font-size: 19px; font-weight: 800; background: #11131a; "
                "padding: 12px 16px; border-radius: 8px; border: 1px solid #282c3c;"
            )

        # Passive Hand Status Indicator Chip
        if err_msg == "Hand Lost":
            self.lbl_hand_status.setText("🔴  Hand Lost")
            self.lbl_hand_status.setStyleSheet(
                "background-color: #1a0b0e; color: #ff1744; font-size: 12px; font-weight: 700; "
                "padding: 6px 14px; border-radius: 14px; border: 1px solid #ff1744;"
            )
        else:
            self.lbl_hand_status.setText("🟢  Hand Detected")
            self.lbl_hand_status.setStyleSheet(
                "background-color: #11131a; color: #00e676; font-size: 12px; font-weight: 600; "
                "padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
            )

        # Hold Stability Ratio (e.g. 1.4 / 2.0s) & Progress Bar
        ratio = getattr(snapshot, "completion_ratio", 0.0)
        stab_pct = int(round(ratio * 100))
        hold_sec = ratio * 2.0
        self.pb_stability.setValue(stab_pct)
        self.pb_stability.setFormat(f"Hold Position: {hold_sec:.1f} / 2.0s ({stab_pct}%)")

        # Passive Tracking Stability Chip
        s_msg = getattr(snapshot, "status_message", "Processing...")
        if "Captured" in s_msg or "✔" in s_msg or "Stable" in s_msg or "Valid" in s_msg:
            badge_text = "🟢  Tracking Stable"
            color_hex = "#00e676"  # Green
        elif "Wrong" in s_msg or "✖" in s_msg:
            badge_text = "🔴  Wrong Direction"
            color_hex = "#ff1744"  # Red
        else:
            badge_text = "🟡  Hold Still..."
            color_hex = "#ffb300"  # Yellow

        self.lbl_status.setText(badge_text)
        self.lbl_status.setStyleSheet(
            f"background-color: #11131a; color: {color_hex}; font-size: 12px; font-weight: 600; "
            f"padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
        )

        # Summary / Complete Step transition
        if step in (CalibrationStep.SUMMARY, CalibrationStep.COMPLETE):
            if not self.review_widget.isVisible():
                self.wizard_view.setVisible(False)
                self.review_widget.setVisible(True)
                self.control_box_widget.setVisible(False)

                cal_data = getattr(self.manager.session, "summary_data", getattr(self.manager, "active_calibration", None))
                if cal_data:
                    self.review_widget.set_calibration_data(cal_data)

    def _on_save(self) -> None:
        """Save captured calibration profile to disk and update steering pipeline live."""
        try:
            self.manager.save_calibration()
            logger.info("Calibration saved successfully via CalibrationDialog.")
            self.accept()
        except Exception as exc:
            logger.error("Failed to save calibration: %s", exc)
            QMessageBox.warning(self, "Save Error", f"Could not save calibration: {exc}")

    def _on_recalibrate(self) -> None:
        """Restart calibration workflow from Pre-Calibration countdown."""
        self._on_start_calibration_clicked()

    def reject(self) -> None:
        """Cancel calibration session without modifying disk files or active calibration."""
        try:
            if self._countdown_timer.isActive():
                self._countdown_timer.stop()
            self.manager.cancel_session()
            logger.info("Calibration cancelled via CalibrationDialog.")
        except Exception as exc:
            logger.warning("Error cancelling calibration session: %s", exc)
        super().reject()
