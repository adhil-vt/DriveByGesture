"""
gesturedrive.tracking.hand_selection
====================================
Deterministic primary hand selection policy based on user configuration and track identity.
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence

from core.models import Handedness
from tracking.hand_state import HandState

logger = logging.getLogger(__name__)


def select_primary_hand_index(
    hands: Sequence[HandState],
    preferred_hand: str = "right",
) -> Optional[int]:
    """
    Deterministically select the index of the primary control hand from a sequence of detected hands.

    Selection Policy:
    1. If no hands are present -> returns None.
    2. If exactly one hand is present -> returns 0 (immediate single-hand control).
    3. If multiple hands are present:
       a. Prefer the hand matching `preferred_hand` (e.g. RIGHT or LEFT).
          If multiple matching hands exist, select the one with the lowest stable `hand_id`.
       b. If no matching hand exists for the preference -> fallback deterministically
          to the hand with the lowest stable `hand_id`.

    Parameters
    ----------
    hands:
        Sequence of detected ``HandState`` domain objects.
    preferred_hand:
        Preferred handedness string (e.g., "right", "left", "RIGHT", "LEFT").

    Returns
    -------
    Optional[int]
        Index of the selected primary hand in ``hands``, or None if ``hands`` is empty.
    """
    if not hands:
        return None

    if len(hands) == 1:
        return 0

    pref_str = str(preferred_hand).strip().upper()
    target_handedness = Handedness.RIGHT if pref_str == "RIGHT" else (
        Handedness.LEFT if pref_str == "LEFT" else None
    )

    if target_handedness is not None:
        matching_indices = [
            (i, h) for i, h in enumerate(hands) if h.handedness == target_handedness
        ]
        if matching_indices:
            # Sort matching by lowest hand_id
            matching_indices.sort(key=lambda item: getattr(item[1], "hand_id", 0))
            return matching_indices[0][0]

    # Fallback to lowest hand_id among all hands
    all_indexed = list(enumerate(hands))
    all_indexed.sort(key=lambda item: getattr(item[1], "hand_id", 0))
    return all_indexed[0][0]


def select_primary_hand(
    hands: Sequence[HandState],
    preferred_hand: str = "right",
) -> Optional[HandState]:
    """
    Deterministically select the primary control hand object from a sequence of detected hands.

    Parameters
    ----------
    hands:
        Sequence of detected ``HandState`` domain objects.
    preferred_hand:
        Preferred handedness string (e.g., "right", "left").

    Returns
    -------
    Optional[HandState]
        The selected primary HandState, or None if ``hands`` is empty.
    """
    idx = select_primary_hand_index(hands, preferred_hand)
    if idx is None:
        return None
    return hands[idx]
