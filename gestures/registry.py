"""
gesturedrive.gestures.registry
==============================
GestureRegistry: central management system for registering, unregistering,
enabling, disabling, and listing gesture recognizers.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Union

from gestures.base import Gesture

logger = logging.getLogger(__name__)


class GestureRegistry:
    """
    Central registry for storing and managing gesture implementations.

    Responsibilities
    ----------------
    - Register new gestures while preventing duplicate names.
    - Unregister existing gestures by name or instance.
    - Enable and disable individual or all registered gestures.
    - Provide access to all registered gestures.

    Note: The registry does not perform gesture recognition itself.
    """

    def __init__(self) -> None:
        self._gestures: Dict[str, Gesture] = {}

    def register(self, gesture: Gesture) -> None:
        """
        Register a new gesture instance.

        Parameters
        ----------
        gesture: Gesture
            The gesture instance to register.

        Raises
        ------
        ValueError
            If a gesture with the same unique name is already registered.
        """
        name = gesture.name
        if name in self._gestures:
            raise ValueError(
                f"Gesture '{name}' is already registered with type '{type(self._gestures[name]).__name__}'."
            )
        self._gestures[name] = gesture
        logger.debug(
            "Registered gesture: '%s' (priority=%d, enabled=%s)",
            name,
            gesture.priority,
            gesture.enabled,
        )

    def unregister(self, gesture_or_name: Union[Gesture, str]) -> None:
        """
        Unregister a gesture by instance or unique name.

        Parameters
        ----------
        gesture_or_name: Union[Gesture, str]
            The gesture instance or name of the gesture to remove.

        Raises
        ------
        KeyError
            If the specified gesture is not found in the registry.
        """
        name = (
            gesture_or_name.name
            if isinstance(gesture_or_name, Gesture)
            else gesture_or_name
        )
        if name not in self._gestures:
            raise KeyError(f"Cannot unregister: Gesture '{name}' is not registered.")
        del self._gestures[name]
        logger.debug("Unregistered gesture: '%s'", name)

    def get(self, gesture_name: str) -> Optional[Gesture]:
        """
        Retrieve a registered gesture by its unique name.

        Parameters
        ----------
        gesture_name: str
            Unique name of the gesture.

        Returns
        -------
        Optional[Gesture]
            The Gesture instance if found, or None.
        """
        return self._gestures.get(gesture_name)

    def get_all(self) -> List[Gesture]:
        """
        Return a list of all registered gestures.

        Returns
        -------
        List[Gesture]
            List of registered gesture instances in registration order.
        """
        return list(self._gestures.values())

    def enable(self, gesture_name: str) -> None:
        """
        Enable a registered gesture by name.

        Parameters
        ----------
        gesture_name: str
            Unique name of the gesture to enable.

        Raises
        ------
        KeyError
            If gesture_name is not registered.
        """
        gesture = self.get(gesture_name)
        if gesture is None:
            raise KeyError(f"Cannot enable: Gesture '{gesture_name}' is not registered.")
        gesture.enabled = True
        logger.debug("Enabled gesture: '%s'", gesture_name)

    def disable(self, gesture_name: str) -> None:
        """
        Disable a registered gesture by name.

        Parameters
        ----------
        gesture_name: str
            Unique name of the gesture to disable.

        Raises
        ------
        KeyError
            If gesture_name is not registered.
        """
        gesture = self.get(gesture_name)
        if gesture is None:
            raise KeyError(f"Cannot disable: Gesture '{gesture_name}' is not registered.")
        gesture.enabled = False
        logger.debug("Disabled gesture: '%s'", gesture_name)

    def enable_all(self) -> None:
        """Enable all registered gestures."""
        for gesture in self._gestures.values():
            gesture.enabled = True
        logger.debug("Enabled all registered gestures.")

    def disable_all(self) -> None:
        """Disable all registered gestures."""
        for gesture in self._gestures.values():
            gesture.enabled = False
        logger.debug("Disabled all registered gestures.")

    def clear(self) -> None:
        """Clear all registered gestures."""
        self._gestures.clear()
        logger.debug("Cleared all gestures from registry.")

    def __len__(self) -> int:
        return len(self._gestures)

    def __contains__(self, gesture_name: str) -> bool:
        return gesture_name in self._gestures

    def __repr__(self) -> str:
        return f"<GestureRegistry(count={len(self._gestures)}, gestures={list(self._gestures.keys())})>"
