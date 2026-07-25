"""
gesturedrive.calibration.calibration_manager
=============================================
CalibrationManager: High-level orchestrator for loading, running, and applying calibration.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from calibration.calibration_data import CalibrationData
from calibration.calibration_session import CalibrationSession, StepSnapshot
from calibration.calibration_storage import CalibrationStorage
from calibration.config import CalibrationConfig

logger = logging.getLogger(__name__)


class CalibrationManager:
    """
    Manager for user calibration loading, session execution, and persistence.

    Parameters
    ----------
    config: Optional[CalibrationConfig]
        Calibration configuration parameters.
    storage: Optional[CalibrationStorage]
        Calibration JSON storage handler.
    """

    def __init__(
        self,
        config: Optional[CalibrationConfig] = None,
        storage: Optional[CalibrationStorage] = None,
    ) -> None:
        self.config = config or CalibrationConfig()
        self.storage = storage or CalibrationStorage(self.config.calibration_file_location)

        self._session: CalibrationSession = CalibrationSession(self.config)
        self._active_calibration: Optional[CalibrationData] = None

        # Auto-load existing calibration profile on startup
        self.load_calibration()

    @property
    def active_calibration(self) -> Optional[CalibrationData]:
        """Returns the currently active CalibrationData profile, if loaded."""
        return self._active_calibration

    @property
    def session(self) -> CalibrationSession:
        """Returns the active CalibrationSession instance."""
        return self._session

    def load_calibration(self, filepath: Optional[Union[str, Path]] = None) -> Optional[CalibrationData]:
        """
        Load calibration profile from storage file.

        If file does not exist or is invalid, returns None (falls back to default settings).
        """
        data = self.storage.load(filepath)
        if data is not None and data.is_valid(self.config.min_steering_range):
            self._active_calibration = data
            logger.info("CalibrationManager: Active calibration profile loaded successfully.")
        else:
            self._active_calibration = None
            logger.info("CalibrationManager: No valid calibration profile loaded. Using defaults.")

        return self._active_calibration

    def save_calibration(
        self, data: Optional[CalibrationData] = None, filepath: Optional[Union[str, Path]] = None
    ) -> Path:
        """Save calibration data to JSON file."""
        target_data = data or self._active_calibration
        if target_data is None:
            raise ValueError("No calibration data to save.")

        saved_path = self.storage.save(target_data, filepath)
        self._active_calibration = target_data
        return saved_path

    def start_session(self) -> None:
        """Start a new interactive calibration session."""
        self._session.start()

    def accept_and_save_session(self) -> Optional[CalibrationData]:
        """Accept summary step and persist captured calibration profile."""
        if self._session.accept_summary():
            data = self._session.result_data
            if data is not None:
                self.save_calibration(data)
                return data
        return None
