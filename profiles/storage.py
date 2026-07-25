"""
gesturedrive.profiles.storage
================================
ProfileStorage: JSON-based persistence for UserProfile objects.

Storage location
----------------
Profiles are stored as individual JSON files:
    config/user/profiles/<profile_name>.json

Format
------
A ProfileStorage file is a flat JSON object with fields matching
UserProfile + nested CalibrationProfile.

Security note
-------------
Profile files contain only user preference data — no credentials.
They may be freely copied between machines.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

from profiles.profile import UserProfile

logger = logging.getLogger(__name__)


class ProfileStorage:
    """
    Reads and writes UserProfile objects to the local filesystem.

    Parameters
    ----------
    storage_dir:
        Directory where profile JSON files are stored.
        Created automatically if it does not exist.
    """

    def __init__(self, storage_dir: Path) -> None:
        self._dir = storage_dir

    def save(self, profile: UserProfile) -> None:
        """
        Serialize and write ``profile`` to disk.

        The file is named ``<profile.name>.json`` within ``storage_dir``.

        Raises
        ------
        OSError
            If the file cannot be written.
        """
        raise NotImplementedError

    def load(self, name: str) -> Optional[UserProfile]:
        """
        Load a UserProfile by name from disk.

        Returns
        -------
        UserProfile
            The deserialized profile.
        None
            If no profile with ``name`` exists on disk.
        """
        raise NotImplementedError

    def list_names(self) -> List[str]:
        """Return the names of all saved profiles."""
        raise NotImplementedError

    def delete(self, name: str) -> None:
        """
        Delete the profile file for ``name``.

        Raises
        ------
        FileNotFoundError
            If no profile with ``name`` exists.
        """
        raise NotImplementedError
