"""
gesturedrive.actions.action_engine
===================================
ActionEngine: Converts recognized gestures and hand tracking states into abstract ActionState snapshots.
"""

from __future__ import annotations

import math
import logging
from typing import List, Optional, Sequence

from analysis.finger_state import HandAnalysis
from gestures.gesture_result import GestureResult
from actions.action import Action, ActionType
from actions.action_state import ActionState
from actions.config import ActionEngineConfig
from actions.steering_pipeline import SteeringDiagnostics, SteeringPipeline

logger = logging.getLogger(__name__)


class ActionEngine:
    """
    Action Engine service: maps recognized gestures to platform-independent abstract actions,
    and normalizes hand tilt into steering values via SteeringPipeline.

    Parameters
    ----------
    config: Optional[ActionEngineConfig]
        Configuration options for steering limits, deadzone, sensitivity, and gesture mappings.
    """

    def __init__(self, config: Optional[ActionEngineConfig] = None) -> None:
        self.config = config or ActionEngineConfig()
        self.steering_pipeline = SteeringPipeline(
            max_steering_angle=self.config.max_steering_angle,
            steering_deadzone=self.config.steering_deadzone,
            steering_sensitivity=getattr(self.config, "steering_sensitivity", 1.0),
            steering_curve_exponent=getattr(self.config, "steering_curve_exponent", 1.0),
            steering_ema_alpha=getattr(self.config, "steering_ema_alpha", 1.0),
            steering_auto_center_rate=getattr(self.config, "steering_auto_center_rate", 0.15),
        )

    def process(
        self,
        gesture_results: Sequence[GestureResult],
        hand_analyses: Optional[Sequence[HandAnalysis]] = None,
    ) -> ActionState:
        """
        Process current frame gesture results and hand analyses into an ActionState.

        Parameters
        ----------
        gesture_results: Sequence[GestureResult]
            Stabilized gesture results from GestureManager.
        hand_analyses: Optional[Sequence[HandAnalysis]]
            Analyzed finger states and hand states from HandAnalyzer (used for steering calculation).

        Returns
        -------
        ActionState
            Aggregated abstract actions and steering diagnostics for the current frame.
        """
        active_actions: List[Action] = []
        is_accel = False
        is_brake = False
        is_handbrake = False

        mappings = self.config.gesture_mappings

        for res in gesture_results:
            if not res or not res.detected or res.gesture_name == "Unknown":
                continue

            action_type = (
                mappings.get(res.gesture_name)
                or mappings.get(res.gesture_name.upper())
                or mappings.get(res.gesture_name.upper().replace(" ", "_"))
            )

            if action_type == ActionType.ACCELERATOR:
                is_accel = True
                active_actions.append(Action(ActionType.ACCELERATOR, value=1.0, confidence=res.confidence))
            elif action_type == ActionType.BRAKE:
                is_brake = True
                active_actions.append(Action(ActionType.BRAKE, value=1.0, confidence=res.confidence))
            elif action_type == ActionType.HANDBRAKE:
                is_handbrake = True
                active_actions.append(Action(ActionType.HANDBRAKE, value=1.0, confidence=res.confidence))
            elif action_type is not None:
                active_actions.append(Action(action_type, value=1.0, confidence=res.confidence))

        # Calculate steering through SteeringPipeline
        steering_val, diag = self.calculate_steering_with_diagnostics(hand_analyses)
        if abs(steering_val) > 0.0:
            active_actions.append(Action(ActionType.STEERING, value=steering_val, confidence=1.0))

        return ActionState(
            accelerator=is_accel,
            brake=is_brake,
            handbrake=is_handbrake,
            steering=steering_val,
            active_actions=active_actions,
            raw_steering=diag.raw_steering,
            steering_deadzone_active=diag.deadzone_active,
            steering_sensitivity=diag.sensitivity,
            steering_curve_output=diag.curve_output,
            raw_sensor_angle=diag.raw_sensor_angle,
            adjusted_steering_angle=diag.adjusted_steering_angle,
        )

    def calculate_steering(self, hand_analyses: Optional[Sequence[HandAnalysis]] = None) -> float:
        """
        Calculate normalized filtered steering value in range [-1.0, 1.0] from hand tilt posture.
        """
        val, _ = self.calculate_steering_with_diagnostics(hand_analyses)
        return val

    def calculate_steering_with_diagnostics(
        self, hand_analyses: Optional[Sequence[HandAnalysis]] = None
    ) -> tuple[float, SteeringDiagnostics]:
        """
        Calculate normalized filtered steering value and complete SteeringDiagnostics.
        """
        if not hand_analyses:
            return self.steering_pipeline.process_raw(0.0)

        target_analysis = hand_analyses[0]
        for ha in hand_analyses:
            if hasattr(ha, "hand_state") and hasattr(ha.hand_state, "handedness"):
                h_str = getattr(ha.hand_state.handedness, "name", str(ha.hand_state.handedness)).upper()
                if h_str == "RIGHT":
                    target_analysis = ha
                    break

        state = getattr(target_analysis, "hand_state", None)
        if not state or not hasattr(state, "landmarks") or not state.landmarks or len(state.landmarks) < 21:
            return self.steering_pipeline.process_raw(0.0)

        lms = state.landmarks
        wrist = lms[0]
        middle_mcp = lms[9]

        # Physical user coordinate system (Physical LEFT -> negative angle/steering, Physical RIGHT -> positive angle/steering)
        dx = wrist.x - middle_mcp.x
        dy = middle_mcp.y - wrist.y

        # In image space, y points down. Vector pointing up is (dx, -dy).
        angle_rad = math.atan2(dx, -dy)
        angle_deg = math.degrees(angle_rad)

        return self.steering_pipeline.process_angle(angle_deg)

