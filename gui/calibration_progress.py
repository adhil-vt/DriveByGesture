"""
gesturedrive.gui.calibration_progress
======================================
CalibrationProgressWidget: Horizontal step indicator widget rendering progress steps
(● Center, ○ Left, ○ Right, ○ Review) for the calibration wizard.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from calibration.calibration_session import CalibrationStep


class CalibrationProgressWidget(QFrame):
    """
    Step progress indicator widget displaying the 4 wizard steps with active highlighting.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        self.chip_center = self._create_step_chip("1. Center")
        self.chip_left = self._create_step_chip("2. Left")
        self.chip_right = self._create_step_chip("3. Right")
        self.chip_review = self._create_step_chip("4. Review")

        layout.addStretch()
        layout.addWidget(self.chip_center)
        layout.addSpacing(10)
        layout.addWidget(self.chip_left)
        layout.addSpacing(10)
        layout.addWidget(self.chip_right)
        layout.addSpacing(10)
        layout.addWidget(self.chip_review)
        layout.addStretch()

        self.set_step(CalibrationStep.CENTER)

    def _create_step_chip(self, label_text: str) -> QLabel:
        lbl = QLabel(f"○  {label_text}")
        lbl.setObjectName("statusChip")
        lbl.setStyleSheet(
            "background-color: #11131a; color: #5b616e; font-size: 12px; font-weight: 600; "
            "padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
        )
        return lbl

    def set_step(self, step: CalibrationStep) -> None:
        """Update step indicators highlighting current active calibration step."""
        steps = [
            (CalibrationStep.CENTER, self.chip_center, "1. Center"),
            (CalibrationStep.LEFT, self.chip_left, "2. Left"),
            (CalibrationStep.RIGHT, self.chip_right, "3. Right"),
            (CalibrationStep.SUMMARY, self.chip_review, "4. Review"),
        ]

        active_found = False

        for s_type, chip_lbl, title in steps:
            if s_type == step or (step == CalibrationStep.COMPLETE and s_type == CalibrationStep.SUMMARY):
                chip_lbl.setText(f"●  {title}")
                chip_lbl.setStyleSheet(
                    "background-color: #14202c; color: #00e5ff; font-size: 12px; font-weight: 700; "
                    "padding: 6px 14px; border-radius: 14px; border: 1px solid #00e5ff;"
                )
                active_found = True
            elif not active_found:
                # Completed previous step
                chip_lbl.setText(f"✓  {title}")
                chip_lbl.setStyleSheet(
                    "background-color: #111a14; color: #00e676; font-size: 12px; font-weight: 600; "
                    "padding: 6px 14px; border-radius: 14px; border: 1px solid #00e676;"
                )
            else:
                # Future step
                chip_lbl.setText(f"○  {title}")
                chip_lbl.setStyleSheet(
                    "background-color: #11131a; color: #5b616e; font-size: 12px; font-weight: 600; "
                    "padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
                )
