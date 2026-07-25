"""
gesturedrive.games.forza_horizon.input_profile
================================================
ForzaInputProfile: Forza Horizon 5 axis/button binding configuration.

Forza Horizon 5 default controller mapping
-------------------------------------------
Left Stick X    → Steering  (full left = -1.0, full right = +1.0)
Right Trigger   → Throttle  [0.0, 1.0]
Left Trigger    → Brake     [0.0, 1.0]
A Button        → Handbrake
X Button        → Horn

Deadzone notes
--------------
Forza has its own in-game deadzone settings; this profile applies a
software deadzone BEFORE the value reaches the virtual controller to
avoid the "creeping" effect when the hand is near neutral.
"""

from __future__ import annotations

from core.models import GestureAxisBinding, GestureButtonBinding, InputProfile


def build_forza_input_profile() -> InputProfile:
    """
    Construct and return the Forza Horizon 5 InputProfile.

    Returns
    -------
    InputProfile
        Fully configured profile with axis bindings, button bindings,
        and the steering curve type identifier.
    """
    return InputProfile(
        game_id="forza_horizon",
        axis_bindings=[
            GestureAxisBinding(
                gesture_name="steering",
                axis_name="left_stick_x",
                scale=1.0,
                inverted=False,
                deadzone=0.05,
            ),
            GestureAxisBinding(
                gesture_name="throttle",
                axis_name="right_trigger",
                scale=1.0,
                inverted=False,
                deadzone=0.05,
            ),
            GestureAxisBinding(
                gesture_name="brake",
                axis_name="left_trigger",
                scale=1.0,
                inverted=False,
                deadzone=0.05,
            ),
        ],
        button_bindings=[
            GestureButtonBinding(gesture_name="handbrake", button_name="a"),
            GestureButtonBinding(gesture_name="horn", button_name="x"),
        ],
        steering_curve_type="forza_cubic",
    )
