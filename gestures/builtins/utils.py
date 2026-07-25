"""
gesturedrive.gestures.builtins.utils
====================================
Helper utilities for built-in gesture recognizers.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence

from analysis.finger_state import FingerState, HandAnalysis


def extract_handedness(hand_analysis: HandAnalysis) -> Optional[str]:
    """Extract handedness string representation from HandAnalysis if available."""
    if hasattr(hand_analysis, "hand_state") and hasattr(
        hand_analysis.hand_state, "handedness"
    ):
        h = hand_analysis.hand_state.handedness
        return h.name if hasattr(h, "name") else str(h)
    return None


def calculate_quality_and_stability(fingers: Sequence[FingerState]) -> float:
    """
    Calculate a combined tracking quality and landmark stability factor in [0.0, 1.0].
    """
    if not fingers:
        return 1.0
    confidences = [max(0.0, min(1.0, f.confidence)) for f in fingers]
    avg_confidence = sum(confidences) / len(confidences)
    min_confidence = min(confidences)

    stability_ratio = min_confidence / (avg_confidence + 1e-6)
    stability_factor = 0.75 + 0.25 * min(1.0, stability_ratio)
    return max(0.0, min(1.0, avg_confidence * stability_factor))


def distance_3d(p1: Any, p2: Any) -> float:
    """Calculate 3D Euclidean distance between two landmark points."""
    dx = getattr(p1, "x", 0.0) - getattr(p2, "x", 0.0)
    dy = getattr(p1, "y", 0.0) - getattr(p2, "y", 0.0)
    dz = getattr(p1, "z", 0.0) - getattr(p2, "z", 0.0)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def calculate_normalized_tip_distance(hand_state: Any) -> Optional[float]:
    """
    Calculate normalized 3D distance between Thumb Tip (landmark 4) and Index Tip (landmark 8)
    relative to hand scale (average of palm length and palm width).
    """
    if not hasattr(hand_state, "landmarks") or not hand_state.landmarks or len(hand_state.landmarks) < 21:
        return None

    lms = hand_state.landmarks
    wrist = lms[0]
    thumb_tip = lms[4]
    index_mcp = lms[5]
    index_tip = lms[8]
    middle_mcp = lms[9]
    pinky_mcp = lms[17]

    palm_len = distance_3d(wrist, middle_mcp)
    palm_width = distance_3d(index_mcp, pinky_mcp)
    scale = max(0.001, (palm_len + palm_width) / 2.0)

    tip_dist = distance_3d(thumb_tip, index_tip)
    return tip_dist / scale


def calculate_pinch_signals(hand_state: Any) -> Optional[Dict[str, float]]:
    """
    Calculate multi-signal 3D geometric metrics for natural Pinch gesture recognition:
    1. Normalized Thumb Tip (4) ↔ Index Tip (8) distance.
    2. Normalized Thumb Tip (4) ↔ Index DIP (7) distance.
    3. Normalized Thumb Tip (4) ↔ Index MCP (5) distance.
    4. Relative direction vector alignment between Thumb tip segment and pinch vector.
    """
    if not hasattr(hand_state, "landmarks") or not hand_state.landmarks or len(hand_state.landmarks) < 21:
        return None

    lms = hand_state.landmarks
    wrist = lms[0]
    thumb_ip = lms[3]
    thumb_tip = lms[4]
    index_mcp = lms[5]
    index_dip = lms[7]
    index_tip = lms[8]
    middle_mcp = lms[9]
    pinky_mcp = lms[17]

    # Hand scale
    palm_len = distance_3d(wrist, middle_mcp)
    palm_width = distance_3d(index_mcp, pinky_mcp)
    scale = max(0.001, (palm_len + palm_width) / 2.0)

    # 1. Tip-to-tip distance
    d_tip_tip = distance_3d(thumb_tip, index_tip) / scale

    # 2. Tip-to-DIP distance
    d_tip_dip = distance_3d(thumb_tip, index_dip) / scale

    # 3. Tip-to-MCP distance
    d_tip_mcp = distance_3d(thumb_tip, index_mcp) / scale

    # 4. Direction vector alignment
    v_thumb_x = thumb_tip.x - thumb_ip.x
    v_thumb_y = thumb_tip.y - thumb_ip.y
    v_thumb_z = thumb_tip.z - thumb_ip.z
    mag_thumb = math.sqrt(v_thumb_x**2 + v_thumb_y**2 + v_thumb_z**2)

    v_pinch_x = index_tip.x - thumb_tip.x
    v_pinch_y = index_tip.y - thumb_tip.y
    v_pinch_z = index_tip.z - thumb_tip.z
    mag_pinch = math.sqrt(v_pinch_x**2 + v_pinch_y**2 + v_pinch_z**2)

    alignment = 0.0
    if mag_thumb > 0 and mag_pinch > 0:
        dot = (v_thumb_x * v_pinch_x + v_thumb_y * v_pinch_y + v_thumb_z * v_pinch_z)
        alignment = dot / (mag_thumb * mag_pinch)

    return {
        "tip_tip_dist": d_tip_tip,
        "tip_dip_dist": d_tip_dip,
        "tip_mcp_dist": d_tip_mcp,
        "direction_alignment": alignment,
    }
