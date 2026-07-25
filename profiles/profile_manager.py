"""
gesturedrive.profiles.profile_manager
========================================
ProfileManager: active profile access, CRUD, and EventBus integration.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from core.event_bus import EventBus
from core.events import CalibrationCompleteEvent, ProfileChangedEvent
from profiles.profile import UserProfile
from profiles.storage import ProfileStorage

logger = logging.getLogger(__name__)

_SOURCE_ID = "profiles.profile_manager"
_DEFAULT_PROFILE_NAME = "default"


class ProfileManager:
    """
    Manages the set of user profiles and the currently active profile.

    Parameters
    ----------
    storage:
        ProfileStorage for persistence.
    event_bus:
        EventBus. ProfileChangedEvent is published when the active profile
        switches. CalibrationCompleteEvent is subscribed to auto-save new
        calibration data.

    Responsibilities
    ----------------
    - Load the last-used profile on startup.
    - Create a default profile if none exist.
    - Switch active profiles and notify the rest of the system.
    - Listen for CalibrationCompleteEvent and update the active profile.
    """

    def __init__(self, storage: ProfileStorage, event_bus: EventBus) -> None:
        self._storage = storage
        self._bus = event_bus
        self._active: Optional[UserProfile] = None

    def register(self) -> None:
        """Subscribe to CalibrationCompleteEvent. Call once at startup."""
        self._bus.subscribe(CalibrationCompleteEvent, self._on_calibration_complete)

    def load(self, name: str = _DEFAULT_PROFILE_NAME) -> None:
        """
        Load and activate the named profile.

        If the profile does not exist, create a default one and save it.
        Publishes ProfileChangedEvent after loading.
        """
        raise NotImplementedError

    def switch(self, name: str) -> None:
        """
        Switch to a different profile by name.

        Saves the current profile first (to preserve last_used_at).
        Publishes ProfileChangedEvent.

        Raises
        ------
        FileNotFoundError
            If no profile with ``name`` exists.
        """
        raise NotImplementedError

    def create(self, name: str) -> UserProfile:
        """
        Create a new profile with the given name and persist it.

        Raises
        ------
        ValueError
            If a profile with ``name`` already exists.
        """
        raise NotImplementedError

    def delete(self, name: str) -> None:
        """
        Delete a profile by name.

        Raises
        ------
        ValueError
            If attempting to delete the currently active profile.
        """
        raise NotImplementedError

    def list_names(self) -> List[str]:
        """Return all available profile names."""
        return self._storage.list_names()

    @property
    def active(self) -> Optional[UserProfile]:
        """The currently active UserProfile."""
        return self._active

    def _on_calibration_complete(self, event: CalibrationCompleteEvent) -> None:
        """Update the active profile's CalibrationProfile and save to disk."""
        raise NotImplementedError
