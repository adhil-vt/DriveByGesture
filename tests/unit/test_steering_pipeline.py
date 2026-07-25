"""
tests.unit.test_steering_pipeline
==================================
Unit tests for SteeringPipeline: EMA, Dead Zone, Sensitivity, Steering Curve, Max Angle Clamp, and Auto Center.
"""

import unittest

from actions.steering_pipeline import SteeringPipeline, SteeringDiagnostics


class TestSteeringPipeline(unittest.TestCase):
    """Test suite covering all 6 feature components of the Intelligent Steering System."""

    def test_ema_smoothing(self):
        """Feature 1: Test Exponential Moving Average (EMA) smoothing factor."""
        # Setup pipeline with alpha=0.20, linear curve (1.0), sensitivity=1.0, deadzone=0.0
        pipeline = SteeringPipeline(
            max_steering_angle=30.0,
            steering_deadzone=0.0,
            steering_sensitivity=1.0,
            steering_curve_exponent=1.0,
            steering_ema_alpha=0.20,
        )

        # Step 1: Input raw 1.0 from initial 0.0
        # Expected step 1 = 0.0 + 0.20 * (1.0 - 0.0) = 0.20
        out1, _ = pipeline.process_raw(1.0)
        self.assertAlmostEqual(out1, 0.20, places=4)

        # Step 2: Input raw 1.0 again
        # Expected step 2 = 0.20 + 0.20 * (1.0 - 0.20) = 0.36
        out2, _ = pipeline.process_raw(1.0)
        self.assertAlmostEqual(out2, 0.36, places=4)

        # Direct raw (alpha=1.0) should respond immediately
        direct_pipeline = SteeringPipeline(
            steering_deadzone=0.0,
            steering_sensitivity=1.0,
            steering_curve_exponent=1.0,
            steering_ema_alpha=1.0,
        )
        direct_out, _ = direct_pipeline.process_raw(0.80)
        self.assertAlmostEqual(direct_out, 0.80, places=4)

    def test_dead_zone(self):
        """Feature 2: Test configurable steering dead zone and threshold detection."""
        pipeline = SteeringPipeline(
            steering_deadzone=0.08,
            steering_sensitivity=1.0,
            steering_curve_exponent=1.0,
            steering_ema_alpha=1.0,
        )

        # Values within [-0.08, 0.08] should yield 0.0 and set deadzone_active=True
        out_zero, diag_zero = pipeline.process_raw(0.05)
        self.assertEqual(out_zero, 0.0)
        self.assertTrue(diag_zero.deadzone_active)

        out_neg_zero, diag_neg_zero = pipeline.process_raw(-0.07)
        self.assertEqual(out_neg_zero, 0.0)
        self.assertTrue(diag_neg_zero.deadzone_active)

        # Value outside deadzone (0.54) should be rescaled: (0.54 - 0.08) / (1.0 - 0.08) = 0.46 / 0.92 = 0.50
        out_outside, diag_outside = pipeline.process_raw(0.54)
        self.assertAlmostEqual(out_outside, 0.50, places=4)
        self.assertFalse(diag_outside.deadzone_active)

    def test_sensitivity(self):
        """Feature 3: Test configurable steering sensitivity scaling and clamping."""
        # Low sensitivity = 0.5
        pipe_low = SteeringPipeline(
            steering_deadzone=0.0,
            steering_sensitivity=0.50,
            steering_curve_exponent=1.0,
            steering_ema_alpha=1.0,
        )
        out_low, _ = pipe_low.process_raw(0.80)
        self.assertAlmostEqual(out_low, 0.40, places=4)

        # High sensitivity = 2.0
        pipe_high = SteeringPipeline(
            steering_deadzone=0.0,
            steering_sensitivity=2.0,
            steering_curve_exponent=1.0,
            steering_ema_alpha=1.0,
        )
        out_high, _ = pipe_high.process_raw(0.40)
        self.assertAlmostEqual(out_high, 0.80, places=4)

        # Clamping when sensitivity * raw exceeds 1.0
        out_clamp, _ = pipe_high.process_raw(0.80)
        self.assertEqual(out_clamp, 1.0)

    def test_steering_curve(self):
        """Feature 4: Test nonlinear steering curve response (cubic vs linear)."""
        # Cubic curve (p=3.0)
        cubic_pipeline = SteeringPipeline(
            steering_deadzone=0.0,
            steering_sensitivity=1.0,
            steering_curve_exponent=3.0,
            steering_ema_alpha=1.0,
        )

        # Near center: 0.20 ^ 3 = 0.008 (very gentle)
        out_gentle, diag_gentle = cubic_pipeline.process_raw(0.20)
        self.assertAlmostEqual(out_gentle, 0.008, places=4)
        self.assertAlmostEqual(diag_gentle.curve_output, 0.008, places=4)

        # Near extreme: 0.90 ^ 3 = 0.729 (steep rise)
        out_steep, diag_steep = cubic_pipeline.process_raw(0.90)
        self.assertAlmostEqual(out_steep, 0.729, places=4)

        # Negative direction: (-0.50)^3 = -0.125
        out_neg, _ = cubic_pipeline.process_raw(-0.50)
        self.assertAlmostEqual(out_neg, -0.125, places=4)

    def test_max_steering_angle_clamp(self):
        """Feature 5: Test maximum hand rotation angle normalization and clamping."""
        pipeline = SteeringPipeline(
            max_steering_angle=30.0,
            steering_deadzone=0.0,
            steering_sensitivity=1.0,
            steering_curve_exponent=1.0,
            steering_ema_alpha=1.0,
        )

        # 15 degrees tilt -> 15/30 = 0.50
        out_half, diag_half = pipeline.process_angle(15.0)
        self.assertAlmostEqual(out_half, 0.50, places=4)
        self.assertAlmostEqual(diag_half.raw_steering, 0.50, places=4)

        # 45 degrees tilt (exceeds max 30) -> clamped to 1.0
        out_over, diag_over = pipeline.process_angle(45.0)
        self.assertEqual(out_over, 1.0)
        self.assertEqual(diag_over.raw_steering, 1.0)

        # -60 degrees tilt -> clamped to -1.0
        out_neg_over, diag_neg_over = pipeline.process_angle(-60.0)
        self.assertEqual(out_neg_over, -1.0)
        self.assertEqual(diag_neg_over.raw_steering, -1.0)

    def test_center_offset_compensation_diagnostics(self):
        """Test center offset compensation produces 0.0 adjusted angle and normalized output when holding calibrated center."""
        from calibration.calibration_data import CalibrationData
        pipeline = SteeringPipeline(
            max_steering_angle=30.0,
            steering_deadzone=0.0,
            steering_sensitivity=1.0,
            steering_curve_exponent=1.0,
            steering_ema_alpha=1.0,
            calibration_data=CalibrationData(center_angle=-0.30, left_limit=-30.30, right_limit=29.70),
        )

        # Raw angle -0.30 (natural center) -> Adjusted angle 0.0 -> Normalized output 0.0
        out_center, diag_center = pipeline.process_angle(-0.30)
        self.assertEqual(out_center, 0.0)
        self.assertEqual(diag_center.raw_sensor_angle, -0.30)
        self.assertEqual(diag_center.adjusted_steering_angle, 0.0)

    def test_auto_center(self):
        """Feature 6: Test smooth auto-centering decay without instant snapping."""
        pipeline = SteeringPipeline(
            steering_deadzone=0.0,
            steering_sensitivity=1.0,
            steering_curve_exponent=1.0,
            steering_ema_alpha=0.50,
            steering_auto_center_rate=0.50,
        )

        # Step 1: Turn wheel to 1.0
        pipeline.process_raw(1.0)
        # Step 2: Push to 1.0 again to reach 0.75
        pipeline.process_raw(1.0)
        start_val = pipeline.filtered_steering
        self.assertGreater(start_val, 0.50)

        # Step 3: Return hand to center (raw 0.0)
        decay1, _ = pipeline.process_raw(0.0)
        self.assertLess(decay1, start_val)
        self.assertGreater(decay1, 0.0)  # Does NOT instantly snap to 0.0

        # Step 4: Continue 0.0 raw input -> decays further smoothly
        decay2, _ = pipeline.process_raw(0.0)
        self.assertLess(decay2, decay1)
        self.assertGreater(decay2, 0.0)

        # Eventually decays to exact 0.0
        for _ in range(20):
            pipeline.process_raw(0.0)
        self.assertEqual(pipeline.filtered_steering, 0.0)


if __name__ == "__main__":
    unittest.main()
