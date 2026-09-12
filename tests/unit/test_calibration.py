"""
tests.unit.test_calibration
============================
Unit tests for Phase 8 Calibration Wizard: data model, JSON storage, session state machine,
retry logic, manager orchestrator, and steering pipeline normalization using calibration.
"""

import json
import tempfile
import time
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
        Landmark(id=9, x=0.5 - dx, y=0.8 + dy, z=0.0)
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
    """Test CalibrationSession state machine, frame processing, validation, and audio hooks."""

    def setUp(self):
        self.config = CalibrationConfig(
            countdown_duration=0.001,
            stable_hold_duration=0.0,
            success_message_duration=0.0,
            transition_pause_duration=0.0,
            transition_countdown_duration=0.0,
            min_movement_threshold=5.0,
            min_steering_range=5.0,
            required_frames_per_step=1,
        )

    def test_session_step_flow_and_review_screen(self):
        session = CalibrationSession(self.config)

        self.assertEqual(session.current_step, CalibrationStep.NOT_STARTED)
        session.start()
        self.assertEqual(session.current_step, CalibrationStep.CENTER)

        # Step 1: Center (dx=0.0 -> angle 0.0)
        hand_center = make_mock_hand_analysis(dx=0.0, dy=-0.20)
        session.process_frame([hand_center])
        # Success pause frame
        session.process_frame([hand_center])
        self.assertEqual(session.center_angle, 0.0)
        self.assertEqual(session.current_step, CalibrationStep.LEFT)

        # Step 2: Left (dx=-0.10, dy=-0.20 -> angle ~ -26.56)
        hand_left = make_mock_hand_analysis(dx=-0.10, dy=-0.20)
        session.process_frame([hand_left])
        session.process_frame([hand_left])
        self.assertIsNotNone(session.left_limit)
        self.assertLess(session.left_limit, -20.0)
        self.assertEqual(session.current_step, CalibrationStep.RIGHT)

        # Step 3: Right (dx=0.10, dy=-0.20 -> angle ~ +26.56)
        hand_right = make_mock_hand_analysis(dx=0.10, dy=-0.20)
        session.process_frame([hand_right])
        session.process_frame([hand_right])
        self.assertIsNotNone(session.right_limit)
        self.assertGreater(session.right_limit, 20.0)

        # Review Screen (SUMMARY)
        self.assertEqual(session.current_step, CalibrationStep.SUMMARY)
        snap = session.process_frame([hand_right])
        self.assertEqual(snap.target_direction, "REVIEW")
        self.assertIsNotNone(snap.total_steering_range)

        # Accept Review Screen -> Save
        self.assertTrue(session.accept_summary())
        self.assertEqual(session.current_step, CalibrationStep.COMPLETE)

    def test_natural_center_offset_sampling(self):
        """User's natural comfortable center angle (e.g. -0.2 deg) is sampled and saved as center_angle."""
        cfg = CalibrationConfig(
            countdown_duration=0.001,
            stable_hold_duration=0.05,
            success_message_duration=0.0,
            transition_pause_duration=0.0,
            transition_countdown_duration=0.0,
            camera_mirrored=False,
            required_frames_per_step=1,
        )
        session = CalibrationSession(cfg)
        session.start()

        # Natural hand posture (dx=-0.001, ~ -0.2 deg tilt) -> Sampled and accepted after 0.05s hold
        hand_natural = make_mock_hand_analysis(dx=-0.001, dy=-0.20)
        session.process_frame([hand_natural])
        time.sleep(0.06)
        session.process_frame([hand_natural])
        self.assertEqual(session.current_step, CalibrationStep.LEFT)
        self.assertAlmostEqual(session.center_angle, -0.29, delta=0.5)

    def test_step_transition_delay_and_evaluation_suppression(self):
        """Test step transition delay suppresses steering direction evaluation until countdown completes."""
        cfg_trans = CalibrationConfig(
            countdown_duration=0.001,
            stable_hold_duration=0.0,
            success_message_duration=0.0,
            transition_pause_duration=1.0,
            transition_countdown_duration=2.0,
            camera_mirrored=False,
            min_movement_threshold=5.0,
            required_frames_per_step=1,
        )
        session = CalibrationSession(cfg_trans)
        session.start()

        # Step 1: Center
        hand_center = make_mock_hand_analysis(dx=0.0, dy=-0.20)
        session.process_frame([hand_center])
        session.process_frame([hand_center])

        # Captured Center -> Transitioning to LEFT
        self.assertEqual(session.current_step, CalibrationStep.LEFT)

        # During Transition Pause phase (pause_duration = 1.0s):
        hand_right = make_mock_hand_analysis(dx=0.10, dy=-0.20)  # Wrong direction input
        snap_pause = session.process_frame([hand_right])

        # Wrong direction warning must NOT be shown!
        self.assertNotIn("Wrong direction detected", snap_pause.status_message)
        self.assertIn("Prepare for the next step", snap_pause.status_message)

        # Fast-forward past pause duration to Countdown phase (countdown_duration = 2.0s)
        session._phase_start_time = time.monotonic() - 1.2
        snap_cd = session.process_frame([hand_right])
        self.assertNotIn("Wrong direction detected", snap_cd.status_message)
        self.assertIn("Starting in", snap_cd.status_message)

        # Fast-forward past countdown duration -> Enter MONITORING phase
        session._phase_start_time = time.monotonic() - 3.5
        snap_mon = session.process_frame([hand_right])

        # Now in MONITORING phase, wrong direction input IS evaluated!
        self.assertIn("Wrong direction detected. Rotate LEFT", snap_mon.status_message)

    def test_wrong_direction_rejection(self):
        cfg_normal = CalibrationConfig(
            countdown_duration=0.001,
            stable_hold_duration=0.0,
            success_message_duration=0.0,
            transition_pause_duration=0.0,
            transition_countdown_duration=0.0,
            camera_mirrored=False,
            min_movement_threshold=5.0,
            required_frames_per_step=1,
        )
        session = CalibrationSession(cfg_normal)
        session.start()

        # Pass Center step
        hand_center = make_mock_hand_analysis(dx=0.0, dy=-0.20)
        session.process_frame([hand_center])
        session.process_frame([hand_center])
        self.assertEqual(session.current_step, CalibrationStep.LEFT)

        # On LEFT step, user rotates RIGHT (dx=+0.10)
        hand_right = make_mock_hand_analysis(dx=0.10, dy=-0.20)
        snap = session.process_frame([hand_right])
        self.assertEqual(session.current_step, CalibrationStep.LEFT)
        self.assertIn("Wrong direction detected. Rotate LEFT", snap.status_message)

    def test_insufficient_movement_rejection(self):
        cfg_normal = CalibrationConfig(
            countdown_duration=0.001,
            stable_hold_duration=0.0,
            success_message_duration=0.0,
            transition_pause_duration=0.0,
            transition_countdown_duration=0.0,
            camera_mirrored=False,
            min_movement_threshold=5.0,
            required_frames_per_step=1,
        )
        session = CalibrationSession(cfg_normal)
        session.start()

        hand_center = make_mock_hand_analysis(dx=0.0, dy=-0.20)
        session.process_frame([hand_center])
        session.process_frame([hand_center])

        # Small left rotation (dx=-0.005 -> ~ -1.4 deg, less than min_movement_threshold=5.0)
        hand_tiny_left = make_mock_hand_analysis(dx=-0.005, dy=-0.20)
        snap = session.process_frame([hand_tiny_left])
        self.assertEqual(session.current_step, CalibrationStep.LEFT)
        self.assertIn("Rotate further LEFT", snap.status_message)

    def test_hand_lost_and_multiple_hands_pause(self):
        session = CalibrationSession(self.config)
        session.start()

        # No hand visible
        snap_no_hand = session.process_frame([])
        self.assertEqual(snap_no_hand.error_message, "Hand Lost")
        self.assertIn("Hand Lost", snap_no_hand.status_message)

        # Multiple hands
        h1 = make_mock_hand_analysis()
        h2 = make_mock_hand_analysis()
        snap_multi = session.process_frame([h1, h2])
        self.assertEqual(snap_multi.error_message, "Multiple hands detected")
        self.assertIn("Multiple hands detected", snap_multi.status_message)

    def test_audio_event_callbacks(self):
        session = CalibrationSession(self.config)
        started_steps = []
        captured_steps = []

        session.on_step_started = lambda s: started_steps.append(s)
        session.on_step_captured = lambda s, val: captured_steps.append((s, val))

        session.start()
        self.assertIn(CalibrationStep.CENTER, started_steps)

        hand_center = make_mock_hand_analysis(dx=0.0, dy=-0.20)
        session.process_frame([hand_center])
        self.assertTrue(len(captured_steps) > 0)
        self.assertEqual(captured_steps[0][0], CalibrationStep.CENTER)

    def test_mirrored_camera_instruction_swapping(self):
        """When camera_mirrored=True, snapshot camera_mode is 'Mirrored' and instruction is 'Rotate your hand fully LEFT.'."""
        cfg_mirrored = CalibrationConfig(
            countdown_duration=0.001,
            stable_hold_duration=0.0,
            success_message_duration=0.0,
            transition_pause_duration=0.0,
            transition_countdown_duration=0.0,
            camera_mirrored=True,
            min_movement_threshold=5.0,
            required_frames_per_step=1,
        )
        session = CalibrationSession(cfg_mirrored)
        session.start()

        # Step 1 Center -> transition to Left
        hand_center = make_mock_hand_analysis(dx=0.0, dy=-0.20)
        session.process_frame([hand_center])
        session.process_frame([hand_center])

        self.assertEqual(session.current_step, CalibrationStep.LEFT)
        snap_left = session.process_frame([hand_center])
        self.assertEqual(snap_left.camera_mode, "Mirrored")
        self.assertEqual(snap_left.displayed_instruction, "Rotate your hand fully LEFT.")

    def test_normal_camera_instruction_behavior(self):
        """When camera_mirrored=False, internal LEFT displays 'Rotate your hand fully LEFT.'."""
        cfg_normal = CalibrationConfig(
            countdown_duration=0.001,
            stable_hold_duration=0.0,
            success_message_duration=0.0,
            transition_pause_duration=0.0,
            transition_countdown_duration=0.0,
            camera_mirrored=False,
            min_movement_threshold=5.0,
            required_frames_per_step=1,
        )
        session = CalibrationSession(cfg_normal)
        session.start()

        # Step 1 Center -> transition to Left
        hand_center = make_mock_hand_analysis(dx=0.0, dy=-0.20)
        session.process_frame([hand_center])
        session.process_frame([hand_center])

        self.assertEqual(session.current_step, CalibrationStep.LEFT)
        snap_left = session.process_frame([hand_center])
        self.assertEqual(snap_left.camera_mode, "Normal")
        self.assertEqual(snap_left.displayed_instruction, "Rotate your hand fully LEFT.")


class TestCalibrationManager(unittest.TestCase):
    """Test CalibrationManager startup auto-loading, session save, and recalibrate."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name) / "default_calibration.json"
        self.config = CalibrationConfig(
            calibration_file_location=str(self.temp_path),
            countdown_duration=0.001,
            stable_hold_duration=0.0,
            success_message_duration=0.0,
            transition_pause_duration=0.0,
            transition_countdown_duration=0.0,
            min_movement_threshold=5.0,
            min_steering_range=5.0,
            required_frames_per_step=1,
        )
        self.manager = CalibrationManager(self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_startup_missing_calibration(self):
        self.assertIsNone(self.manager.active_calibration)

    def test_start_session_recalibrate_and_save(self):
        self.manager.start_session()
        session = self.manager.session

        hand_center = make_mock_hand_analysis(dx=0.0, dy=-0.20)
        hand_left = make_mock_hand_analysis(dx=-0.12, dy=-0.20)
        hand_right = make_mock_hand_analysis(dx=0.12, dy=-0.20)

        # Step 1 Center
        session.process_frame([hand_center])
        session.process_frame([hand_center])
        # Step 2 Left
        session.process_frame([hand_left])
        session.process_frame([hand_left])
        # Step 3 Right
        session.process_frame([hand_right])
        session.process_frame([hand_right])

        self.assertEqual(session.current_step, CalibrationStep.SUMMARY)

        # Test recalibrate
        self.manager.recalibrate()
        self.assertEqual(self.manager.session.current_step, CalibrationStep.CENTER)

        # Complete steps again
        session.process_frame([hand_center])
        session.process_frame([hand_center])
        session.process_frame([hand_left])
        session.process_frame([hand_left])
        session.process_frame([hand_right])
        session.process_frame([hand_right])

        saved = self.manager.accept_and_save_session()
        self.assertIsNotNone(saved)
        self.assertTrue(self.temp_path.exists())
        self.assertIsNotNone(self.manager.active_calibration)

    def test_cancel_calibration_does_not_overwrite_file(self):
        """[ESC]: Cancel calibration must restore original calibration without overwriting disk file."""
        original_data = CalibrationData(center_angle=2.0, left_limit=-25.0, right_limit=25.0)
        self.manager.save_calibration(original_data)
        self.assertTrue(self.temp_path.exists())

        # Start a new session and process 1 frame
        self.manager.start_session()
        self.assertTrue(self.manager.is_session_active)
        hand_center = make_mock_hand_analysis(dx=0.05, dy=-0.20)
        self.manager.session.process_frame([hand_center])

        # Cancel session via [ESC]
        msg = self.manager.cancel_session()
        self.assertEqual(msg, "Calibration Cancelled")
        self.assertFalse(self.manager.is_session_active)

        # File content on disk must remain un-overwritten
        reloaded = self.manager.storage.load()
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.center_angle, 2.0)
        self.assertEqual(self.manager.active_calibration.center_angle, 2.0)

    def test_reset_calibration_deletes_file_and_resets_memory(self):
        """[R]: Reset calibration clears memory, deletes saved file, and reverts to default."""
        original_data = CalibrationData(center_angle=3.0, left_limit=-30.0, right_limit=30.0)
        self.manager.save_calibration(original_data)
        self.assertTrue(self.temp_path.exists())

        # Reset via [R]
        msg = self.manager.reset_calibration()
        self.assertEqual(msg, "Calibration Reset")

        self.assertIsNone(self.manager.active_calibration)
        self.assertFalse(self.temp_path.exists())
        self.assertFalse(self.manager.is_session_active)

    def test_press_c_starts_session(self):
        """[C]: Pressing C starts calibration session."""
        self.assertFalse(self.manager.is_session_active)
        self.manager.start_session()
        self.assertTrue(self.manager.is_session_active)
        self.assertEqual(self.manager.session.current_step, CalibrationStep.CENTER)

    def test_startup_auto_load(self):
        """Startup automatically loads valid calibration profile when file exists."""
        data = CalibrationData(center_angle=1.5, left_limit=-25.0, right_limit=25.0)
        self.manager.save_calibration(data)

        # New manager instance reading same path
        new_mgr = CalibrationManager(self.config)
        self.assertIsNotNone(new_mgr.active_calibration)
        self.assertEqual(new_mgr.active_calibration.center_angle, 1.5)

    def test_load_missing_calibration_file(self):
        """When calibration file is missing, load_calibration returns None and uses defaults."""
        missing_path = Path(self.temp_dir.name) / "non_existent.json"
        mgr = CalibrationManager(CalibrationConfig(calibration_file_location=str(missing_path)))
        self.assertIsNone(mgr.active_calibration)

    def test_load_corrupted_calibration_file(self):
        """When calibration file is corrupted JSON, load_calibration returns None and uses defaults."""
        bad_path = Path(self.temp_dir.name) / "corrupted.json"
        with open(bad_path, "w") as f:
            f.write("{ invalid json syntax ... ")

        mgr = CalibrationManager(CalibrationConfig(calibration_file_location=str(bad_path)))
        self.assertIsNone(mgr.active_calibration)

    def test_live_calibration_update_without_restart(self):
        """Saving calibration immediately updates active calibration and bound SteeringPipeline in memory live."""
        pipeline = SteeringPipeline(steering_deadzone=0.0, steering_sensitivity=1.0, steering_curve_exponent=1.0, steering_ema_alpha=1.0)
        self.manager.bind_steering_pipeline(pipeline)

        # Before calibration save, pipeline has no custom calibration
        self.assertIsNone(pipeline.calibration_data)

        # Save new calibration profile
        new_cal = CalibrationData(center_angle=2.0, left_limit=-20.0, right_limit=30.0)
        self.manager.save_calibration(new_cal)

        # Verify active calibration in manager and bound pipeline are immediately updated in memory
        self.assertIsNotNone(self.manager.active_calibration)
        self.assertEqual(self.manager.active_calibration.center_angle, 2.0)
        self.assertIsNotNone(pipeline.calibration_data)
        self.assertEqual(pipeline.calibration_data.center_angle, 2.0)

        # Process angle live: center (2.0 deg) -> 0.0 steering immediately!
        out, _ = pipeline.process_angle(2.0)
        self.assertEqual(out, 0.0)

        # Reset calibration: live pipeline immediately reverts to default
        self.manager.reset_calibration()
        self.assertIsNone(pipeline.calibration_data)


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
