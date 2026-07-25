"""
gesturedrive.calibration.validators
======================================
CalibrationValidator: validates the completeness and quality of a
CalibrationProfile before it is persisted.

Validation rules (all must pass)
----------------------------------
1. neutral_palm_normal is not None.
2. max_left_angle > 5.0 degrees (user actually tilted left).
3. max_right_angle > 5.0 degrees (user actually tilted right).
4. throttle_open_ratio > throttle_closed_ratio + 0.2 (clear range captured).
5. brake_z_threshold is within a plausible range [-0.5, 0.0].
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from calibration.profile import CalibrationProfile


@dataclass
class ValidationResult:
    """Result of a CalibrationValidator.validate() call."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CalibrationValidator:
    """
    Validates a CalibrationProfile against quality thresholds.

    All thresholds are configurable at construction to support different
    use cases (strict QA vs. lenient first-run).
    """

    def __init__(
        self,
        min_steering_angle: float = 5.0,
        min_throttle_range: float = 0.2,
    ) -> None:
        self._min_steering_angle = min_steering_angle
        self._min_throttle_range = min_throttle_range

    def validate(self, profile: CalibrationProfile) -> ValidationResult:
        """
        Run all validation rules against ``profile``.

        Returns
        -------
        ValidationResult
            ``is_valid=True`` if all rules pass; ``errors`` lists any
            failures with human-readable messages.
        """
        raise NotImplementedError
