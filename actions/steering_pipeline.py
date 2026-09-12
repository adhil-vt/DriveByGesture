"""
gesturedrive.actions.steering_pipeline
=======================================
SteeringPipeline: Complete Intelligent Steering Processing Pipeline.

Pipeline Stages
---------------
1. Max Angle Normalization & Clamping:
   Normalizes tilt angle (degrees) relative to max_steering_angle into [-1.0, 1.0].
   Angles beyond max_steering_angle are clamped to [-1.0, 1.0].
2. Dead Zone Filter:
   Small hand movements within [-deadzone, +deadzone] output 0.0.
   Outside deadzone, range is re-scaled linearly from [deadzone, 1.0] -> [0.0, 1.0].
   Sets deadzone_active boolean flag.
3. Sensitivity Scaling:
   Scales response by steering_sensitivity (e.g. 0.5, 1.0, 1.5, 2.0).
   Clamped to [-1.0, 1.0].
4. Steering Curve:
   Applies a non-linear steering curve f(x) = sign(x) * |x|^p (default p=3.0 cubic curve).
   Near center: very gentle steering. Near extremes: steering increases faster.
5. EMA Filter & Auto Center:
   Smooths steering using an Exponential Moving Average (EMA).
   When hand returns to center or hand is not present (target = 0.0), steering returns
   smoothly to center (auto-center) using smoothing rate instead of snapping.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class SteeringDiagnostics:
    """Diagnostic metrics snapshot for steering system HUD rendering."""
    raw_steering: float = 0.0
    filtered_steering: float = 0.0
    deadzone_active: bool = False
    sensitivity: float = 1.0
    curve_output: float = 0.0
    raw_sensor_angle: float = 0.0
    adjusted_steering_angle: float = 0.0


class SteeringPipeline:
    """
    Complete steering pipeline processor.

    Parameters
    ----------
    max_steering_angle: float
        Maximum hand tilt rotation angle in degrees (e.g. 30.0, 35.0, 45.0).
    steering_deadzone: float
        Dead zone threshold in range [0.0, 1.0] (e.g. 0.05 or 0.08).
    steering_sensitivity: float
        Sensitivity multiplier (e.g. 0.5, 1.0, 1.5, 2.0).
    steering_curve_exponent: float
        Exponent for non-linear steering response (e.g. 3.0 for cubic curve).
    steering_ema_alpha: float
        EMA smoothing factor in range (0.0, 1.0].
    steering_auto_center_rate: float
        Smoothing rate when returning to zero/center (defaults to steering_ema_alpha if not set).
    """

    def __init__(
        self,
        max_steering_angle: float = 30.0,
        steering_deadzone: float = 0.05,
        steering_sensitivity: float = 1.0,
        steering_curve_exponent: float = 3.0,
        steering_ema_alpha: float = 0.15,
        steering_auto_center_rate: Optional[float] = None,
        steering_inversion: bool = False,
        calibration_data: Optional[Any] = None,
    ) -> None:
        self.max_steering_angle = max_steering_angle
        self.steering_deadzone = steering_deadzone
        self.steering_sensitivity = steering_sensitivity
        self.steering_curve_exponent = steering_curve_exponent
        self.steering_ema_alpha = steering_ema_alpha
        self.steering_auto_center_rate = (
            steering_auto_center_rate
            if steering_auto_center_rate is not None
            else steering_ema_alpha
        )
        self.steering_inversion = steering_inversion
        self.calibration_data = calibration_data

        self._filtered_steering: float = 0.0
        self._last_diagnostics: SteeringDiagnostics = SteeringDiagnostics(
            sensitivity=steering_sensitivity
        )

    def set_calibration(self, calibration_data: Optional[Any]) -> None:
        """Set or update active CalibrationData for user-range normalization."""
        self.calibration_data = calibration_data

    @property
    def filtered_steering(self) -> float:
        return self._filtered_steering

    @property
    def diagnostics(self) -> SteeringDiagnostics:
        return self._last_diagnostics

    def reset(self, initial_value: float = 0.0) -> None:
        """Reset the internal EMA filter state to initial_value."""
        self._filtered_steering = float(initial_value)
        self._last_diagnostics = SteeringDiagnostics(
            raw_steering=initial_value,
            filtered_steering=initial_value,
            deadzone_active=(abs(initial_value) <= self.steering_deadzone),
            sensitivity=self.steering_sensitivity,
            curve_output=initial_value,
        )

    def process_angle(self, angle_deg: float) -> Tuple[float, SteeringDiagnostics]:
        """
        Process hand tilt angle (degrees) through full steering pipeline using calibration if available.

        Returns
        -------
        Tuple[float, SteeringDiagnostics]
            Filtered steering value in range [-1.0, 1.0] and complete diagnostics.
        """
        cal = self.calibration_data
        raw_sensor_angle = float(angle_deg)
        if cal is not None and hasattr(cal, "center_angle") and hasattr(cal, "left_limit") and hasattr(cal, "right_limit"):
            center = cal.center_angle
            left_lim = cal.left_limit
            right_lim = cal.right_limit
            delta = angle_deg - center
            adjusted_steering_angle = delta

            if delta < 0.0:
                left_span = abs(center - left_lim)
                if left_span <= 0.001:
                    left_span = max(0.001, self.max_steering_angle)
                raw_norm = max(-1.0, min(0.0, delta / left_span))
            elif delta > 0.0:
                right_span = abs(right_lim - center)
                if right_span <= 0.001:
                    right_span = max(0.001, self.max_steering_angle)
                raw_norm = max(0.0, min(1.0, delta / right_span))
            else:
                raw_norm = 0.0
        else:
            adjusted_steering_angle = angle_deg
            max_angle = max(0.001, self.max_steering_angle)
            raw_norm = max(-1.0, min(1.0, angle_deg / max_angle))

        if self.steering_inversion:
            raw_norm = -raw_norm

        return self.process_raw(raw_norm, raw_sensor_angle=raw_sensor_angle, adjusted_steering_angle=adjusted_steering_angle)

    def process_raw(
        self,
        raw_steering: float,
        raw_sensor_angle: float = 0.0,
        adjusted_steering_angle: float = 0.0,
    ) -> Tuple[float, SteeringDiagnostics]:
        """
        Process normalized raw steering input in range [-1.0, 1.0] through pipeline.

        Returns
        -------
        Tuple[float, SteeringDiagnostics]
            Filtered steering value in range [-1.0, 1.0] and complete diagnostics.
        """
        # Clamp raw steering
        raw = max(-1.0, min(1.0, raw_steering))

        # 1. Dead Zone Filter & linear rescaling
        dz = self.steering_deadzone
        abs_raw = abs(raw)
        if abs_raw <= dz:
            post_dz = 0.0
            deadzone_active = True
        else:
            deadzone_active = False
            sign = 1.0 if raw > 0.0 else -1.0
            post_dz = sign * (abs_raw - dz) / (1.0 - dz)

        # 2. Sensitivity Scaling
        post_sens = max(-1.0, min(1.0, post_dz * self.steering_sensitivity))

        # 3. Steering Curve (Nonlinear cubic/exponent response)
        exp = self.steering_curve_exponent
        abs_sens = abs(post_sens)
        sign_sens = 1.0 if post_sens > 0.0 else (-1.0 if post_sens < 0.0 else 0.0)
        curve_output = sign_sens * (abs_sens ** exp)
        curve_output = max(-1.0, min(1.0, curve_output))

        # 4. EMA Filter & Auto Center
        target = curve_output
        if target == 0.0:
            # Auto center smooth decay
            alpha = self.steering_auto_center_rate
        else:
            alpha = self.steering_ema_alpha

        # EMA formula: S_t = S_{t-1} + alpha * (target - S_{t-1})
        new_filtered = self._filtered_steering + alpha * (target - self._filtered_steering)

        # Snap to 0.0 if extremely close to zero to prevent floating point residual drag
        if abs(new_filtered) < 1e-4 and target == 0.0:
            new_filtered = 0.0

        new_filtered = round(max(-1.0, min(1.0, new_filtered)), 4)
        self._filtered_steering = new_filtered

        diag = SteeringDiagnostics(
            raw_steering=round(raw, 4),
            filtered_steering=new_filtered,
            deadzone_active=deadzone_active,
            sensitivity=self.steering_sensitivity,
            curve_output=round(curve_output, 4),
            raw_sensor_angle=round(raw_sensor_angle, 2),
            adjusted_steering_angle=round(adjusted_steering_angle, 2),
        )
        self._last_diagnostics = diag
        return new_filtered, diag
