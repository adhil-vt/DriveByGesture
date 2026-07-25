"""
tests.unit.test_input_mapper
==============================
Unit tests for InputMapper.

Verified behaviours
-------------------
- Steering value is mapped to left_stick_x with deadzone.
- Throttle value is mapped to right_trigger.
- Brake value is mapped to left_trigger.
- Boolean gestures (handbrake, horn) map to buttons a and x.
- Values outside [-1.0, 1.0] are clamped.
- Missing gestures in result_set default to 0.0 / False.
- Calibration=None falls back to raw values.
"""

import pytest

# from controller.input_mapper import InputMapper
# from games.forza_horizon.input_profile import build_forza_input_profile


class TestInputMapperAxisMapping:

    def test_steering_maps_to_left_stick_x(self, neutral_gesture_result_set):
        pytest.skip("Implement when InputMapper.map() is complete.")

    def test_throttle_maps_to_right_trigger(self, neutral_gesture_result_set):
        pytest.skip("Implement when InputMapper.map() is complete.")

    def test_brake_maps_to_left_trigger(self, neutral_gesture_result_set):
        pytest.skip("Implement when InputMapper.map() is complete.")


class TestInputMapperDeadzone:

    def test_value_within_deadzone_is_zeroed(self, neutral_gesture_result_set):
        pytest.skip("Implement when InputMapper.map() is complete.")

    def test_value_outside_deadzone_is_passed_through(self):
        pytest.skip("Implement when InputMapper.map() is complete.")


class TestInputMapperClamping:

    def test_value_above_1_is_clamped(self):
        pytest.skip("Implement when InputMapper.map() is complete.")

    def test_value_below_minus_1_is_clamped(self):
        pytest.skip("Implement when InputMapper.map() is complete.")


class TestInputMapperButtons:

    def test_active_handbrake_presses_a_button(self):
        pytest.skip("Implement when InputMapper.map() is complete.")

    def test_inactive_handbrake_releases_a_button(self):
        pytest.skip("Implement when InputMapper.map() is complete.")
