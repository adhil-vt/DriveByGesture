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
from calibration.calibration_session import CalibrationSession, CalibrationStep, StepSnapshot
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

        # Event / Callback hook for live calibration updates
        self.on_calibration_updated: Optional[Callable[[Optional[CalibrationData]], None]] = None

        # Auto-load existing calibration profile on startup
        self.load_calibration()

    def bind_steering_pipeline(self, pipeline: Any) -> None:
        """
        Bind SteeringPipeline (or ActionEngine) to receive automatic live calibration updates.
        """
        target_pipe = getattr(pipeline, "steering_pipeline", pipeline)

        def _update(data: Optional[CalibrationData]) -> None:
            if hasattr(target_pipe, "set_calibration"):
                target_pipe.set_calibration(data)

        self.on_calibration_updated = _update
        if hasattr(target_pipe, "set_calibration"):
            target_pipe.set_calibration(self._active_calibration)

    @property
    def active_calibration(self) -> Optional[CalibrationData]:
        """Returns the currently active CalibrationData profile, if loaded."""
        return self._active_calibration

    @property
    def session(self) -> CalibrationSession:
        """Returns the active CalibrationSession instance."""
        return self._session

    @property
    def is_session_active(self) -> bool:
        """Return True if a calibration session is currently running."""
        return self._session.current_step in (
            CalibrationStep.CENTER,
            CalibrationStep.LEFT,
            CalibrationStep.RIGHT,
            CalibrationStep.SUMMARY,
            CalibrationStep.FAILED,
        )

    def load_calibration(self, filepath: Optional[Union[str, Path]] = None) -> Optional[CalibrationData]:
        """
        Load calibration profile from storage file.

        If file does not exist, logs "Calibration Not Found \n Using Default Configuration".
        If file exists but is corrupted or invalid, logs "Calibration File Invalid \n Using Default Calibration".
        If file exists and is valid, logs "Calibration Loaded".
        """
        file_exists = self.storage.exists(filepath)
        data = self.storage.load(filepath)

        if file_exists:
            if data is not None and data.is_valid(self.config.min_steering_range):
                self._active_calibration = data
                logger.info("Calibration Loaded")
            else:
                self._active_calibration = None
                logger.warning("Calibration File Invalid")
                logger.warning("Using Default Calibration")
        else:
            self._active_calibration = None
            logger.info("Calibration Not Found")
            logger.info("Using Default Configuration")

        if self.on_calibration_updated:
            self.on_calibration_updated(self._active_calibration)

        return self._active_calibration

    def save_calibration(
        self, data: Optional[CalibrationData] = None, filepath: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Save calibration data to JSON file and immediately replace active calibration in memory.
        """
        target_data = data or self._active_calibration
        if target_data is None:
            raise ValueError("No calibration data to save.")

        saved_path = self.storage.save(target_data, filepath)
        self._active_calibration = target_data

        if self.on_calibration_updated:
            self.on_calibration_updated(self._active_calibration)

        return saved_path

    def start_session(self) -> None:
        """Start a new interactive calibration session."""
        self._session.start()

    def recalibrate(self) -> None:
        """Restart calibration session from Step 1 (Center)."""
        logger.info("Recalibrating session from Step 1.")
        self._session.start()

    def cancel_session(self) -> str:
        """
        Cancel active calibration session and restore previously loaded calibration profile.

        Does NOT overwrite saved calibration file on disk.
        """
        self._session._step = CalibrationStep.NOT_STARTED
        self.load_calibration()
        logger.info("Calibration Cancelled")
        return "Calibration Cancelled"

    def reset_calibration(self) -> str:
        """
        Reset calibration: clear active calibration memory, delete saved file, and return to default steering values.
        """
        self._session._step = CalibrationStep.NOT_STARTED
        self._active_calibration = None
        self.storage.delete()

        if self.on_calibration_updated:
            self.on_calibration_updated(None)

        logger.info("Calibration Reset")
        return "Calibration Reset"

    def accept_and_save_session(self) -> Optional[CalibrationData]:
        """Accept summary step and persist captured calibration profile."""
        if self._session.accept_summary():
            data = self._session.result_data
            if data is not None:
                self.save_calibration(data)
                return data
        return None
