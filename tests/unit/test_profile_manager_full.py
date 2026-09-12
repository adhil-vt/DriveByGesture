"""
tests.unit.test_profile_manager_full
======================================
Comprehensive unit test suite for complete Profile Management lifecycle:
Create, Rename, Duplicate, Delete, Import, Export, Set Active, Restore Default, and Persistence.
"""

import json
import tempfile
import unittest
from pathlib import Path

from calibration.calibration_data import CalibrationData
from profiles.profile import DriveProfile
from profiles.profile_manager import ProfileManager


class TestProfileManagerFull(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.temp_dir.name)
        self.pm = ProfileManager(storage_dir=self.storage_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initial_default_profile_exists(self):
        names = self.pm.list_names()
        self.assertIn("Default", names)
        self.assertEqual(self.pm.active_name, "Default")

    def test_create_profile(self):
        p = self.pm.create("Forza 5", description="Racing setup", game_name="Forza Horizon 5")
        self.assertEqual(p.name, "Forza 5")
        self.assertIn("Forza 5", self.pm.list_names())
        self.assertEqual(p.metadata.description, "Racing setup")

    def test_create_duplicate_name_fails(self):
        self.pm.create("Drift")
        with self.assertRaises(ValueError):
            self.pm.create("Drift")

    def test_rename_profile(self):
        self.pm.create("OldName")
        renamed = self.pm.rename("OldName", "NewName")
        self.assertEqual(renamed.name, "NewName")
        self.assertNotIn("OldName", self.pm.list_names())
        self.assertIn("NewName", self.pm.list_names())

    def test_duplicate_profile(self):
        self.pm.create("Original")
        p = self.pm.set_active("Original")
        p.steering["max_steering_angle"] = 45.0
        cal_data = CalibrationData(center_angle=2.0, left_limit=-20.0, right_limit=22.0)
        p.set_calibration_data(cal_data)
        self.pm.save_active()

        dup = self.pm.duplicate("Original", "Original Copy")
        self.assertEqual(dup.name, "Original Copy")
        self.assertEqual(dup.steering["max_steering_angle"], 45.0)
        self.assertTrue(dup.is_calibrated)
        self.assertIn("Original Copy", self.pm.list_names())

    def test_delete_profile(self):
        self.pm.create("Extra")
        self.assertIn("Extra", self.pm.list_names())
        self.pm.delete("Extra")
        self.assertNotIn("Extra", self.pm.list_names())

    def test_delete_active_profile_fallback(self):
        p2 = self.pm.create("Profile2")
        self.pm.set_active("Profile2")
        self.assertEqual(self.pm.active_name, "Profile2")

        self.pm.delete("Profile2")
        self.assertNotIn("Profile2", self.pm.list_names())
        self.assertEqual(self.pm.active_name, "Default")

    def test_delete_last_remaining_profile_fails(self):
        # Default is the only profile left
        for name in list(self.pm.list_names()):
            if name != "Default":
                self.pm.delete(name)

        with self.assertRaises(ValueError):
            self.pm.delete("Default")

    def test_export_and_import_profile_valid(self):
        self.pm.create("ExportTest")
        p = self.pm.set_active("ExportTest")
        p.steering["steering_sensitivity"] = 2.5
        self.pm.save_active()

        export_path = self.storage_dir / "exported_test.json"
        self.pm.export_profile("ExportTest", export_path)
        self.assertTrue(export_path.exists())

        imported = self.pm.import_profile(export_path)
        self.assertIn("ExportTest (Imported)", self.pm.list_names())
        self.assertEqual(imported.steering["steering_sensitivity"], 2.5)

    def test_import_invalid_json_fails(self):
        invalid_path = self.storage_dir / "corrupted.json"
        invalid_path.write_text("{ corrupt json data ...", encoding="utf-8")

        with self.assertRaises(ValueError):
            self.pm.import_profile(invalid_path)

    def test_import_missing_name_fails(self):
        bad_schema_path = self.storage_dir / "bad_schema.json"
        bad_schema_path.write_text(json.dumps({"description": "No name key"}), encoding="utf-8")

        with self.assertRaises(ValueError):
            self.pm.import_profile(bad_schema_path)

    def test_restore_default_profile(self):
        p = self.pm.create("CustomProfile")
        p.steering["max_steering_angle"] = 60.0
        p.set_calibration_data(CalibrationData(center_angle=1.0, left_limit=-15.0, right_limit=15.0))
        self.pm.save_active()
        self.assertTrue(p.is_calibrated)

        restored = self.pm.restore_default("CustomProfile")
        self.assertEqual(restored.name, "CustomProfile")
        self.assertEqual(restored.steering["max_steering_angle"], 30.0)  # Factory default 30.0
        self.assertFalse(restored.is_calibrated)

    def test_active_profile_persistence(self):
        self.pm.create("PersistentProfile")
        self.pm.set_active("PersistentProfile")

        # Instantiate a new ProfileManager pointing to same directory
        pm2 = ProfileManager(storage_dir=self.storage_dir)
        self.assertEqual(pm2.active_name, "PersistentProfile")


if __name__ == "__main__":
    unittest.main()
