"""
tests.unit.test_calibration
============================
Unit tests for Phase 8 Calibration Wizard: data model, JSON storage, session state machine,
retry logic, manager orchestrator, and steering pipeline normalization using calibration.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from actions.steering_pipeline import SteeringPipeline
from calibration.calibration_data import CalibrationData
from calibration.calibration_manager import CalibrationManager
from calibration.calibration_session import CalibrationSession, CalibrationStep
from calibration.calibration_storage import CalibrationStorage
from calibration.config import CalibrationConfig
from tracking.hand_state import HandState, Landmark


def make_mock_hand_analysis(dx: float = 0.0, dy: float = -0.20):
    """Helper to generate a mock HandAnalysis with given wrist -> middle MCP displacement."""
    hand = MagicMock()
    hand.hand_state = MagicMock(spec=HandState)
    hand.hand_state.landmarks = [
        Landmark(id=0, x=0.5, y=0.8, z=0.0),
    ] + [Landmark(id=i, x=0.5, y=0.5, z=0.0) for i in range(1, 9)] + [
        Landmark(id=9, x=0.5 + dx, y=0.8 + dy, z=0.0)
    ] + [Landmark(id=i, x=0.5, y=0.5, z=0.0) for i in range(10, 21)]
    return hand


class TestCalibrationData(unittest.TestCase):
    """Test CalibrationData dataclass model and serialization methods."""

    def test_calibration_data_serialization(self):
        data = CalibrationData(
            center_angle=2.5,
            left_limit=-25.0,
            right_limit=35.0,
            maximum_left=-40.0,
            maximum_right=50.0,
            calibration_date="2026-07-25T12:00:00Z",
            version="1.0",
        )

        self.assertEqual(data.left_range, 27.5)
        self.assertEqual(data.right_range, 32.5)
        self.assertEqual(data.total_range, 60.0)
        self.assertTrue(data.is_valid(min_range=10.0))

        dict_repr = data.to_dict()
        self.assertEqual(dict_repr["center_angle"], 2.5)
        self.assertEqual(dict_repr["left_limit"], -25.0)

        restored = CalibrationData.from_dict(dict_repr)
        self.assertEqual(restored.center_angle, 2.5)
        self.assertEqual(restored.left_limit, -25.0)
        self.assertEqual(restored.right_limit, 35.0)


class TestCalibrationStorage(unittest.TestCase):
    """Test JSON persistence for calibration profiles."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name) / "test_calibration.json"
        self.storage = CalibrationStorage(self.temp_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_load_valid_file(self):
        original_data = CalibrationData(
            center_angle=1.0,
            left_limit=-30.0,
            right_limit=30.0,
        )

        saved_path = self.storage.save(original_data)
        self.assertTrue(saved_path.exists())

        loaded_data = self.storage.load()
        self.assertIsNotNone(loaded_data)
        self.assertEqual(loaded_data.center_angle, 1.0)
        self.assertEqual(loaded_data.left_limit, -30.0)

    def test_missing_file_returns_none(self):
        missing_path = Path(self.temp_dir.name) / "non_existent_file.json"
        storage = CalibrationStorage(missing_path)
        self.assertIsNone(storage.load())

    def test_corrupted_json_returns_none(self):
        bad_file = Path(self.temp_dir.name) / "corrupted.json"
        with open(bad_file, "w") as f:
            f.write("{ invalid_json ... ")

        storage = CalibrationStorage(bad_file)
        self.assertIsNone(storage.load())


class TestCalibrationSession(unittest.TestCase):
    """Test CalibrationSession state machine, frame processing, and retry logic."""

    def test_session_step_flow(self):
        cfg = CalibrationConfig(countdown_duration=0.1, required_frames_per_step=1, min_steering_range=5.0)
        session = CalibrationSession(cfg)

        self.assertEqual(session.current_step, CalibrationStep.NOT_STARTED)
        session.start()
        self.assertEqual(session.current_step, CalibrationStep.CENTER)

        # Step 1: Center (dx=0.0 -> angle 0.0)
        hand_center = make_mock_hand_analysis(dx=0.0, dy=-0.20)
        snap1 = session.process_frame([hand_center])
        self.assertEqual(session.center_angle, 0.0)
        self.assertEqual(session.current_step, CalibrationStep.LEFT)

        # Step 2: Left (dx=-0.10, dy=-0.20 -> angle ~ -26.56)
        hand_left = make_mock_hand_analysis(dx=-0.10, dy=-0.20)
        snap2 = session.process_frame([hand_left])
        self.assertIsNotNone(session.left_limit)
        self.assertLess(session.left_limit, -20.0)
        self.assertEqual(session.current_step, CalibrationStep.RIGHT)

        # Step 3: Right (dx=0.10, dy=-0.20 -> angle ~ +26.56)
        hand_right = make_mock_hand_analysis(dx=0.10, dy=-0.20)
        snap3 = session.process_frame([hand_right])
        self.assertIsNotNone(session.right_limit)
        self.assertGreater(session.right_limit, 20.0)
        self.assertEqual(session.current_step, CalibrationStep.SUMMARY)

        # Step 4: Accept Summary
        result = session.result_data
        self.assertIsNotNone(result)
        self.assertTrue(session.accept_summary())
        self.assertEqual(session.current_step, CalibrationStep.COMPLETE)
        self.assertTrue(session.is_complete)

    def test_error_handling_and_retry(self):
        cfg = CalibrationConfig(countdown_duration=0.1, required_frames_per_step=1, min_steering_range=30.0)
        session = CalibrationSession(cfg)
        session.start()

        # Test no hand visible
        snap_no_hand = session.process_frame([])
        self.assertIn("No hand visible", snap_no_hand.error_message)

        # Test multiple hands
        hand1 = make_mock_hand_analysis()
        hand2 = make_mock_hand_analysis()
        snap_multi = session.process_frame([hand1, hand2])
        self.assertIn("Multiple hands detected", snap_multi.error_message)

        # Capture center = 0.0
        session.process_frame([hand1])

        # Try small left angle displacement (dx=-0.01 -> ~ -2.8 deg, smaller than min_steering_range=30.0)
        hand_small_left = make_mock_hand_analysis(dx=-0.01, dy=-0.20)
        snap_fail = session.process_frame([hand_small_left])
        self.assertEqual(session.current_step, CalibrationStep.FAILED)
        self.assertIn("Steering range too small", snap_fail.error_message)

        # Test retry_step restarts calibration
        session.retry_step()
        self.assertEqual(session.current_step, CalibrationStep.CENTER)


class TestCalibrationManager(unittest.TestCase):
    """Test CalibrationManager startup auto-loading and session save."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name) / "default_calibration.json"
        self.config = CalibrationConfig(
            calibration_file_location=str(self.temp_path),
            countdown_duration=0.001,
            required_frames_per_step=1,
        )
        self.manager = CalibrationManager(self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_startup_missing_calibration(self):
        self.assertIsNone(self.manager.active_calibration)

    def test_start_session_and_save(self):
        self.manager.start_session()
        session = self.manager.session

        hand_center = make_mock_hand_analysis(dx=0.0, dy=-0.20)
        hand_left = make_mock_hand_analysis(dx=-0.12, dy=-0.20)
        hand_right = make_mock_hand_analysis(dx=0.12, dy=-0.20)

        session.process_frame([hand_center])
        session.process_frame([hand_left])
        session.process_frame([hand_right])

        saved = self.manager.accept_and_save_session()
        self.assertIsNotNone(saved)
        self.assertTrue(self.temp_path.exists())
        self.assertIsNotNone(self.manager.active_calibration)


class TestSteeringPipelineCalibrationIntegration(unittest.TestCase):
    """Test SteeringPipeline normalization using personalized CalibrationData range."""

    def test_calibrated_steering_normalization(self):
        # User calibrated: center=5.0 deg, left=-20.0 deg (span 25), right=35.0 deg (span 30)
        cal = CalibrationData(
            center_angle=5.0,
            left_limit=-20.0,
            right_limit=35.0,
        )

        pipeline = SteeringPipeline(
            steering_deadzone=0.0,
            steering_sensitivity=1.0,
            steering_curve_exponent=1.0,
            steering_ema_alpha=1.0,
            calibration_data=cal,
        )

        # Center angle (5.0 deg) -> 0.0 steering
        out_center, diag_center = pipeline.process_angle(5.0)
        self.assertEqual(out_center, 0.0)
        self.assertEqual(diag_center.raw_steering, 0.0)

        # Full Left limit (-20.0 deg) -> -1.0 steering
        out_left, diag_left = pipeline.process_angle(-20.0)
        self.assertEqual(out_left, -1.0)
        self.assertEqual(diag_left.raw_steering, -1.0)

        # Full Right limit (35.0 deg) -> +1.0 steering
        out_right, diag_right = pipeline.process_angle(35.0)
        self.assertEqual(out_right, 1.0)
        self.assertEqual(diag_right.raw_steering, 1.0)

        # Beyond Left limit (-32.5 deg) -> clamped to -1.0
        out_over_left, _ = pipeline.process_angle(-32.5)
        self.assertEqual(out_over_left, -1.0)

        # Beyond Right limit (50.0 deg) -> clamped to +1.0
        out_over_right, _ = pipeline.process_angle(50.0)
        self.assertEqual(out_over_right, 1.0)


if __name__ == "__main__":
    unittest.main()
