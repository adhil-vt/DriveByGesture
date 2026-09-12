"""
gesturedrive.profiles.storage
================================
ProfileStorage: JSON persistence for DriveProfile objects.

Storage layout
--------------
    profiles/user/<name>.json

Each file is a fully self-contained DriveProfile JSON document.
Files are named after the profile (spaces → underscores, lowercase).
The legacy profiles/default_calibration.json is NOT touched here.

Security note
-------------
Profile files contain only user preference data — no credentials.
They may be freely copied between machines.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from core.resources import get_user_profile_storage_dir, get_user_profiles_dir
from profiles.profile import DriveProfile

logger = logging.getLogger(__name__)


def _get_default_storage_dir() -> Path:
    return get_user_profile_storage_dir()


def _profile_path(storage_dir: Path, name: str) -> Path:
    """Return the .json file path for a given profile name."""
    safe = name.replace("/", "_").replace("\\", "_")
    return storage_dir / f"{safe}.json"


def validate_profile_dict(data: Any) -> None:
    """Validate that a loaded dictionary meets DriveProfile schema requirements."""
    if not isinstance(data, dict):
        raise ValueError("Invalid profile structure: root content must be a JSON object.")

    name = data.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        raise ValueError("Invalid profile schema: missing or empty 'name' field.")

    for sec in ("steering", "camera", "controller", "general", "desktop"):
        val = data.get(sec)
        if val is not None and not isinstance(val, dict):
            raise ValueError(f"Invalid profile schema: section '{sec}' must be a JSON object.")


class ProfileStorage:
    """
    Reads and writes DriveProfile objects to the local filesystem.

    Parameters
    ----------
    storage_dir:
        Directory where profile JSON files are stored.
        Defaults to %LOCALAPPDATA%\\DriveByGesture\\profiles\\user.
        Created automatically if it does not exist.
    """

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        if storage_dir is not None:
            p = Path(storage_dir)
            if not p.is_absolute():
                p = get_user_profiles_dir() / p
            self._dir = p
        else:
            self._dir = _get_default_storage_dir()
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def save(self, profile: DriveProfile) -> Path:
        """
        Serialize and write ``profile`` to disk.

        The file is named after profile.name within storage_dir.

        Returns
        -------
        Path
            Absolute path of the saved JSON file.

        Raises
        ------
        OSError
            If the file cannot be written.
        """
        path = _profile_path(self._dir, profile.name)
        profile.metadata.touch()
        data = profile.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("ProfileStorage: saved profile '%s' → %s", profile.name, path)
        return path

    def load(self, name: str) -> Optional[DriveProfile]:
        """
        Load a DriveProfile by name from disk.

        Returns None if the file does not exist or is corrupted.
        Never raises.
        """
        path = _profile_path(self._dir, name)
        if not path.exists():
            logger.debug("ProfileStorage: profile '%s' not found at %s.", name, path)
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            validate_profile_dict(data)
            profile = DriveProfile.from_dict(data)
            logger.info("ProfileStorage: loaded profile '%s'.", name)
            return profile
        except Exception as exc:
            logger.error("ProfileStorage: failed to load profile '%s': %s", name, exc)
            return None

    def delete(self, name: str) -> None:
        """
        Delete the profile file for ``name``.

        Raises
        ------
        FileNotFoundError
            If no profile with ``name`` exists on disk.
        """
        path = _profile_path(self._dir, name)
        if not path.exists():
            raise FileNotFoundError(f"Profile '{name}' not found at {path}.")
        path.unlink()
        logger.info("ProfileStorage: deleted profile '%s'.", name)

    def list_names(self) -> List[str]:
        """Return the names of all saved profiles sorted alphabetically."""
        names = []
        for p in sorted(self._dir.glob("*.json")):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                name = data.get("name", p.stem)
                names.append(name)
            except Exception:
                names.append(p.stem)
        return names

    def exists(self, name: str) -> bool:
        """Return True if a profile with this name exists on disk."""
        return _profile_path(self._dir, name).exists()

    # ── Import / Export ───────────────────────────────────────────────────────

    def export_to(self, name: str, dest_path: Path) -> Path:
        """
        Copy a profile JSON file to an arbitrary destination path.

        Returns
        -------
        Path
            The destination path.

        Raises
        ------
        FileNotFoundError
            If the profile does not exist.
        """
        src = _profile_path(self._dir, name)
        if not src.exists():
            raise FileNotFoundError(f"Profile '{name}' not found.")
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_path)
        logger.info("ProfileStorage: exported '%s' → %s", name, dest_path)
        return dest_path

    def import_from(self, src_path: Path) -> DriveProfile:
        """
        Validate and import a profile JSON from an external file.

        Returns the loaded DriveProfile on success.

        Raises
        ------
        ValueError
            If the file is missing, unreadable, or not a valid DriveProfile JSON.
        """
        src_path = Path(src_path)
        if not src_path.exists():
            raise ValueError(f"Import source not found: {src_path}")
        try:
            with open(src_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            validate_profile_dict(data)
            profile = DriveProfile.from_dict(data)
            logger.info("ProfileStorage: imported profile '%s' from %s.", profile.name, src_path)
            return profile
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"Failed to parse profile file: {exc}") from exc
