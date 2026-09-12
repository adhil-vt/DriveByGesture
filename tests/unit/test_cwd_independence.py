"""
Unit tests for CWD independence and user-writable data isolation in DriveByGesture.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from calibration.calibration_storage import CalibrationStorage
from core.resources import (
    ensure_user_data_migrated,
    get_active_mode_path,
    get_active_profile_path,
    get_default_calibration_path,
    get_game_prefs_path,
    get_user_crash_reports_dir,
    get_user_data_dir,
    get_user_logs_dir,
    get_user_profiles_dir,
    get_user_profile_storage_dir,
)
from desktop.enums import AppMode
from desktop.manager import ModeManager
from games.prefs import DetectionPrefs
from profiles.profile import DriveProfile
from profiles.profile_manager import ProfileManager
from profiles.storage import ProfileStorage


class TestCWDIndependence(unittest.TestCase):
    """Test that all persistent user storage operations are absolute and CWD-independent."""

    def test_user_data_paths_are_absolute(self):
        self.assertTrue(get_user_data_dir().is_absolute())
        self.assertTrue(get_user_profiles_dir().is_absolute())
        self.assertTrue(get_user_profile_storage_dir().is_absolute())
        self.assertTrue(get_active_profile_path().is_absolute())
        self.assertTrue(get_active_mode_path().is_absolute())
        self.assertTrue(get_default_calibration_path().is_absolute())
        self.assertTrue(get_user_logs_dir().is_absolute())
        self.assertTrue(get_user_crash_reports_dir().is_absolute())
        self.assertTrue(get_game_prefs_path().is_absolute())

    def test_operations_with_different_cwd(self):
        """Simulate execution from an unrelated working directory."""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)

                # 1. Seeding / migration
                ensure_user_data_migrated()

                # 2. Profile storage
                storage = ProfileStorage()
                self.assertTrue(storage._dir.is_absolute())
                default_profile = DriveProfile.create_default()
                saved_path = storage.save(default_profile)
                self.assertTrue(saved_path.is_absolute())
                self.assertTrue(saved_path.exists())

                # Verify nothing was created in the temp CWD
                self.assertFalse((Path(temp_dir) / "profiles").exists())

                # 3. Profile Manager
                mgr = ProfileManager()
                self.assertIsNotNone(mgr.active)
                mgr.set_active(default_profile.name)
                self.assertEqual(mgr.active_name, default_profile.name)

                # 4. Mode Manager
                mode_mgr = ModeManager()
                mode_mgr.set_mode(AppMode.DRIVING)
                self.assertEqual(mode_mgr.active_mode, AppMode.DRIVING)
                self.assertFalse((Path(temp_dir) / "profiles").exists())

                # 5. Calibration Storage
                cal_storage = CalibrationStorage()
                self.assertTrue(cal_storage.default_filepath.is_absolute())

                # 6. Detection Prefs
                prefs = DetectionPrefs()
                self.assertTrue(prefs._path.is_absolute())
                prefs.save()
                self.assertFalse((Path(temp_dir) / "games").exists())

            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
