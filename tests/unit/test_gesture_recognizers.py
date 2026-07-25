# Unit test stubs for gesture recognizers.
# One test class per recognizer; parameterized with fixture landmark data.
"""
tests.unit.test_gesture_recognizers
=====================================
Unit tests for all IGestureRecognizer implementations.

Coverage targets
----------------
- SteeringRecognizer:  neutral, full-left, full-right, no-hand
- ThrottleRecognizer:  open-fist, closed-fist, deadzone boundary, no-hand
- BrakeRecognizer:     open-palm-near, open-palm-far, fist (no brake), no-hand
- HandbrakeRecognizer: gun-pose held, gun-pose released, debounce behaviour
- HornRecognizer:      thumbs-up held, thumbs-up released, debounce
"""

import pytest

# All imports are placeholders until recognizer implementations are complete.
# from gesture.builtin.steering import SteeringRecognizer
# from gesture.builtin.throttle import ThrottleRecognizer


class TestSteeringRecognizer:
    """Tests for SteeringRecognizer."""

    def test_neutral_hand_returns_zero(self, neutral_hand_state):
        """Expect steering value of 0.0 for the neutral pose."""
        pytest.skip("Implement when SteeringRecognizer.recognize() is complete.")

    def test_full_left_returns_negative_one(self):
        """Calibrated full-left tilt should return -1.0."""
        pytest.skip("Implement when SteeringRecognizer.recognize() is complete.")

    def test_full_right_returns_positive_one(self):
        """Calibrated full-right tilt should return +1.0."""
        pytest.skip("Implement when SteeringRecognizer.recognize() is complete.")

    def test_no_hand_returns_none(self, no_hand_state):
        """No hands in HandState should return None."""
        pytest.skip("Implement when SteeringRecognizer.recognize() is complete.")


class TestThrottleRecognizer:
    """Tests for ThrottleRecognizer."""

    def test_open_hand_returns_zero(self):
        pytest.skip("Implement when ThrottleRecognizer.recognize() is complete.")

    def test_closed_fist_returns_one(self):
        pytest.skip("Implement when ThrottleRecognizer.recognize() is complete.")

    def test_deadzone_clamps_to_zero(self):
        pytest.skip("Implement when ThrottleRecognizer.recognize() is complete.")


class TestBrakeRecognizer:
    """Tests for BrakeRecognizer."""

    def test_palm_pushed_near_activates_brake(self):
        pytest.skip("Implement when BrakeRecognizer.recognize() is complete.")

    def test_palm_pulled_back_deactivates_brake(self):
        pytest.skip("Implement when BrakeRecognizer.recognize() is complete.")


class TestHandbrakeRecognizer:
    """Tests for HandbrakeRecognizer."""

    def test_gun_pose_activates_after_hold_frames(self):
        pytest.skip("Implement when HandbrakeRecognizer.recognize() is complete.")

    def test_incomplete_hold_does_not_activate(self):
        pytest.skip("Implement when HandbrakeRecognizer.recognize() is complete.")


class TestHornRecognizer:
    """Tests for HornRecognizer."""

    def test_thumbs_up_activates_horn(self):
        pytest.skip("Implement when HornRecognizer.recognize() is complete.")

    def test_flat_palm_does_not_activate_horn(self):
        pytest.skip("Implement when HornRecognizer.recognize() is complete.")
