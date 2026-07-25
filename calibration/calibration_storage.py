"""
gesturedrive.calibration.calibration_storage
==============================================
CalibrationStorage: JSON persistence for CalibrationData profiles.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Union

from calibration.calibration_data import CalibrationData

logger = logging.getLogger(__name__)

DEFAULT_CALIBRATION_PATH = Path("profiles/default_calibration.json")


class CalibrationStorage:
    """
    Handles saving and loading CalibrationData to/from JSON files.

    Parameters
    ----------
    default_filepath: Optional[Union[str, Path]]
        Default path used if no specific path is passed to save/load.
    """

    def __init__(self, default_filepath: Optional[Union[str, Path]] = None) -> None:
        self.default_filepath = Path(default_filepath) if default_filepath else DEFAULT_CALIBRATION_PATH

    def save(
        self, data: CalibrationData, filepath: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Save CalibrationData object to JSON file.

        Parameters
        ----------
        data: CalibrationData
            Calibration instance to serialize.
        filepath: Optional[Union[str, Path]]
            Target JSON file path. Defaults to self.default_filepath.

        Returns
        -------
        Path
            Path to the saved JSON file.
        """
        target = Path(filepath) if filepath else self.default_filepath
        target.parent.mkdir(parents=True, exist_ok=True)

        dict_data = data.to_dict()
        with open(target, "w", encoding="utf-8") as f:
            json.dump(dict_data, f, indent=2)

        logger.info("Saved calibration profile to %s", target)
        return target

    def load(
        self, filepath: Optional[Union[str, Path]] = None
    ) -> Optional[CalibrationData]:
        """
        Load CalibrationData object from JSON file.

        Parameters
        ----------
        filepath: Optional[Union[str, Path]]
            File path to load. Defaults to self.default_filepath.

        Returns
        -------
        Optional[CalibrationData]
            Loaded CalibrationData instance, or None if file missing or corrupted.
        """
        target = Path(filepath) if filepath else self.default_filepath

        if not target.exists() or not target.is_file():
            logger.info("Calibration file not found at %s. Using default settings.", target)
            return None

        try:
            with open(target, "r", encoding="utf-8") as f:
                content = json.load(f)

            if not isinstance(content, dict):
                logger.warning("Invalid JSON format in %s (expected dictionary).", target)
                return None

            data = CalibrationData.from_dict(content)
            logger.info("Successfully loaded calibration profile from %s", target)
            return data
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.error("Failed to load calibration profile from %s: %s", target, exc)
            return None

    def exists(self, filepath: Optional[Union[str, Path]] = None) -> bool:
        """Return True if calibration file exists on disk."""
        target = Path(filepath) if filepath else self.default_filepath
        return target.exists() and target.is_file()

    def delete(self, filepath: Optional[Union[str, Path]] = None) -> bool:
        """
        Delete saved calibration JSON file from disk.

        Returns True if file was deleted, False if file did not exist.
        """
        target = Path(filepath) if filepath else self.default_filepath
        if target.exists() and target.is_file():
            try:
                target.unlink()
                logger.info("Deleted calibration file at %s", target)
                return True
            except OSError as exc:
                logger.error("Failed to delete calibration file at %s: %s", target, exc)
                return False
        return False

