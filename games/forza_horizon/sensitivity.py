"""
gesturedrive.games.forza_horizon.sensitivity
==============================================
ForzaSensitivityCurve: non-linear steering response for Forza Horizon 5.

Purpose
-------
Forza Horizon 5 has relatively sensitive steering physics. A raw linear
mapping from gesture angle to left-stick-x feels twitchy at small angles
and under-responsive at large angles. A cubic curve gives:
  - Fine control near center (small movements → small steering)
  - Full lock reachable with large deliberate movements

Curve: f(x) = x³  (simple cubic, no external dependencies)

The specific curve formula should be tuned during QA playtesting.
The ``steering_curve_type`` field in the InputProfile tells the InputMapper
which curve function to apply.
"""

from __future__ import annotations


class ForzaSensitivityCurve:
    """
    Non-linear steering sensitivity curve for Forza Horizon 5.

    All methods are static; this class acts as a namespace for curve functions.
    The InputMapper selects the appropriate method by checking the
    ``steering_curve_type`` field on the active InputProfile.
    """

    @staticmethod
    def cubic(value: float) -> float:
        """
        Apply a cubic response curve: f(x) = x³.

        Parameters
        ----------
        value:
            Input steering value in [-1.0, 1.0].

        Returns
        -------
        float
            Curved steering value in [-1.0, 1.0].
        """
        raise NotImplementedError

    @staticmethod
    def linear(value: float) -> float:
        """
        Pass-through linear curve: f(x) = x.

        Used as a baseline for testing and comparison.
        """
        return value

    @staticmethod
    def exponential(value: float, exponent: float = 2.5) -> float:
        """
        Signed exponential curve: f(x) = sign(x) * |x|^exponent.

        Parameters
        ----------
        value:
            Input steering value in [-1.0, 1.0].
        exponent:
            Curve sharpness. Values > 1.0 create a softer center response.
        """
        raise NotImplementedError
