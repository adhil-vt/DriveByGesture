"""
gesturedrive.profiles.profile_manager
========================================
ProfileManager: single entry point for all profile CRUD operations.

Replaces the old stub that depended on the removed EventBus architecture.
This implementation uses ProfileStorage and DriveProfile directly, and
integrates with CalibrationManager via a simple callback.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, List, Optional

from core.resources import get_active_profile_path
from profiles.profile import DriveProfile
from profiles.storage import ProfileStorage

logger = logging.getLogger(__name__)

_DEFAULT_NAME = "Default"


def _get_active_profile_state_file() -> Path:
    return get_active_profile_path()


class ProfileManager:
    """
    Manages the complete lifecycle of DriveByGesture profiles.

    Responsibilities
    ----------------
    - Ensure at least one valid profile always exists.
    - Load the last-used profile on startup.
    - Create / rename / duplicate / delete profiles.
    - Import and export profile files.
    - Notify the rest of the application when the active profile changes.

    Parameters
    ----------
    storage_dir: Optional[Path]
        Directory for profile JSON files. Defaults to profiles/user/.
    on_profile_changed: Optional[Callable]
        Callback invoked as ``on_profile_changed(profile: DriveProfile)``
        whenever the active profile switches.
    """

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        on_profile_changed: Optional[Callable[[DriveProfile], None]] = None,
    ) -> None:
        self._storage = ProfileStorage(storage_dir)
        self._on_profile_changed = on_profile_changed
        self._active: Optional[DriveProfile] = None

        self._ensure_default_exists()
        self._load_last_active()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def active(self) -> Optional[DriveProfile]:
        """The currently active DriveProfile."""
        return self._active

    @property
    def active_profile(self) -> Optional[DriveProfile]:
        """Alias for active DriveProfile property."""
        return self._active

    @property
    def active_name(self) -> str:
        """Name of the active profile, or 'Default' if none loaded."""
        return self._active.name if self._active else _DEFAULT_NAME

    # ── Listing ───────────────────────────────────────────────────────────────

    def list_names(self) -> List[str]:
        """Return all available profile names sorted alphabetically."""
        return self._storage.list_names()

    def list_profiles(self) -> List[DriveProfile]:
        """Return all profiles as DriveProfile objects."""
        result = []
        for name in self.list_names():
            p = self._storage.load(name)
            if p is not None:
                result.append(p)
        return result

    # ── Activation ────────────────────────────────────────────────────────────

    def set_active(self, name: str) -> DriveProfile:
        """
        Load and activate a profile by name.

        Saves the current profile first to capture any in-memory edits,
        then loads the requested profile and fires the changed callback.

        Raises
        ------
        FileNotFoundError
            If no profile with ``name`` exists.
        """
        if self._active is not None:
            try:
                self._storage.save(self._active)
            except Exception as exc:
                logger.warning("ProfileManager: could not auto-save current profile: %s", exc)

        profile = self._storage.load(name)
        if profile is None:
            raise FileNotFoundError(f"Profile '{name}' not found.")

        self._active = profile
        self._persist_active_name(name)
        logger.info("ProfileManager: activated profile '%s'.", name)
        self._fire_changed()
        return profile

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(self, name: str, description: str = "", game_name: str = "") -> DriveProfile:
        """
        Create a new empty profile and persist it.

        Raises
        ------
        ValueError
            If a profile with ``name`` already exists.
        """
        name = name.strip()
        if not name:
            raise ValueError("Profile name cannot be empty.")
        if self._storage.exists(name):
            raise ValueError(f"A profile named '{name}' already exists.")

        from profiles.profile import ProfileMetadata
        profile = DriveProfile(
            metadata=ProfileMetadata(name=name, description=description, game_name=game_name)
        )
        self._storage.save(profile)
        logger.info("ProfileManager: created profile '%s'.", name)
        return profile

    def duplicate(self, source_name: str, new_name: str) -> DriveProfile:
        """
        Duplicate an existing profile under a new name.

        Raises
        ------
        FileNotFoundError
            If the source profile does not exist.
        ValueError
            If a profile with new_name already exists.
        """
        new_name = new_name.strip()
        src = self._storage.load(source_name)
        if src is None:
            raise FileNotFoundError(f"Source profile '{source_name}' not found.")
        if self._storage.exists(new_name):
            raise ValueError(f"A profile named '{new_name}' already exists.")

        from profiles.profile import ProfileMetadata
        import dataclasses
        new_meta = ProfileMetadata(
            name=new_name,
            description=src.metadata.description,
            game_name=src.metadata.game_name,
            author=src.metadata.author,
        )
        dup = DriveProfile(
            metadata=new_meta,
            calibration=dict(src.calibration) if src.calibration else None,
            steering=dict(src.steering),
            camera=dict(src.camera),
            controller=dict(src.controller),
            general=dict(getattr(src, "general", {})),
            desktop=dict(src.desktop),
        )
        self._storage.save(dup)
        logger.info("ProfileManager: duplicated '%s' → '%s'.", source_name, new_name)
        return dup

    def rename(self, old_name: str, new_name: str) -> DriveProfile:
        """
        Rename a profile. The old file is deleted; the new file is saved.

        Raises
        ------
        FileNotFoundError
            If the source profile does not exist.
        ValueError
            If a profile with new_name already exists.
        """
        new_name = new_name.strip()
        profile = self._storage.load(old_name)
        if profile is None:
            raise FileNotFoundError(f"Profile '{old_name}' not found.")
        if self._storage.exists(new_name) and new_name != old_name:
            raise ValueError(f"A profile named '{new_name}' already exists.")

        profile.metadata.name = new_name
        profile.metadata.touch()
        self._storage.save(profile)
        if old_name != new_name:
            try:
                self._storage.delete(old_name)
            except FileNotFoundError:
                pass

        if self._active and self._active.name == old_name:
            self._active = profile
            self._persist_active_name(new_name)

        logger.info("ProfileManager: renamed '%s' → '%s'.", old_name, new_name)
        return profile

    def delete(self, name: str) -> None:
        """
        Delete a profile by name.

        If the deleted profile was active, automatically switches to Default.
        Always ensures at least one profile exists.

        Raises
        ------
        ValueError
            If attempting to delete the only remaining profile.
        """
        names = self.list_names()
        if len(names) <= 1:
            raise ValueError("Cannot delete the last remaining profile. Create another profile first.")

        was_active = (self._active is not None and self._active.name == name)
        if was_active:
            self._active = None  # Prevent set_active from re-saving deleted profile

        self._storage.delete(name)
        logger.info("ProfileManager: deleted profile '%s'.", name)

        if was_active:
            remaining = self.list_names()
            fallback = _DEFAULT_NAME if _DEFAULT_NAME in remaining else remaining[0]
            self.set_active(fallback)

    def save_active(self) -> None:
        """Persist the current in-memory active profile to disk."""
        if self._active is not None:
            self._storage.save(self._active)

    def restore_default(self, name: str) -> DriveProfile:
        """
        Reset all settings in profile ``name`` to factory fresh default settings
        while preserving its identity/name and description.
        """
        profile = self._storage.load(name)
        if profile is None:
            raise FileNotFoundError(f"Profile '{name}' not found.")

        fresh = DriveProfile.create_default()
        fresh.metadata.name = profile.metadata.name
        fresh.metadata.description = profile.metadata.description
        fresh.metadata.game_name = profile.metadata.game_name
        fresh.metadata.author = profile.metadata.author
        fresh.metadata.created_at = profile.metadata.created_at
        fresh.metadata.touch()

        self._storage.save(fresh)
        if self._active and self._active.name == name:
            self._active = fresh
            self._fire_changed()

        logger.info("ProfileManager: restored profile '%s' to factory defaults.", name)
        return fresh

    # ── Calibration integration ───────────────────────────────────────────────

    def update_calibration(self, calibration_data) -> None:
        """
        Embed updated CalibrationData into the active profile and save.

        Called by MainWindow when CalibrationManager saves new calibration.
        """
        if self._active is None:
            return
        self._active.set_calibration_data(calibration_data)
        self._storage.save(self._active)
        logger.info("ProfileManager: updated calibration in active profile '%s'.", self.active_name)

    # ── Import / Export ───────────────────────────────────────────────────────

    def export_profile(self, name: str, dest_path: Path) -> Path:
        """
        Export a profile JSON file to an arbitrary path.

        Raises
        ------
        FileNotFoundError
            If the profile does not exist.
        """
        return self._storage.export_to(name, dest_path)

    def import_profile(self, src_path: Path) -> DriveProfile:
        """
        Import a profile JSON from an external file.

        Validates the file before saving. If a profile with the same name
        already exists, appends ' (Imported)' to avoid collision.

        Returns the imported DriveProfile.

        Raises
        ------
        ValueError
            If the file is missing, unreadable, or not a valid profile JSON.
        """
        profile = self._storage.import_from(Path(src_path))

        # Deduplicate names
        candidate_name = profile.name
        if self._storage.exists(candidate_name):
            candidate_name = f"{candidate_name} (Imported)"
            profile.metadata.name = candidate_name

        self._storage.save(profile)
        logger.info("ProfileManager: imported profile '%s'.", profile.name)
        return profile

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _ensure_default_exists(self) -> None:
        """Create the Default profile if no profiles exist at all."""
        if not self._storage.list_names():
            default = DriveProfile.create_default()
            # Try to embed existing calibration from legacy file
            try:
                from calibration.calibration_storage import CalibrationStorage
                legacy = CalibrationStorage().load()
                if legacy is not None:
                    default.set_calibration_data(legacy)
                    logger.info("ProfileManager: migrated legacy calibration into Default profile.")
            except Exception:
                pass
            self._storage.save(default)
            logger.info("ProfileManager: created initial Default profile.")

    def _load_last_active(self) -> None:
        """Load the last active profile from the state file, falling back to first available."""
        last = self._read_active_name()
        if last and self._storage.exists(last):
            profile = self._storage.load(last)
            if profile is not None:
                self._active = profile
                logger.info("ProfileManager: restored last active profile '%s'.", last)
                return

        # Fallback: load first available profile
        names = self.list_names()
        if names:
            profile = self._storage.load(names[0])
            self._active = profile
            logger.info("ProfileManager: loaded first available profile '%s'.", names[0] if names else "?")

    def _persist_active_name(self, name: str) -> None:
        """Write the active profile name to the state file."""
        try:
            state_file = _get_active_profile_state_file()
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(name, encoding="utf-8")
        except OSError as exc:
            logger.warning("ProfileManager: could not persist active profile name: %s", exc)

    def _read_active_name(self) -> Optional[str]:
        """Read the active profile name from the state file."""
        try:
            state_file = _get_active_profile_state_file()
            if state_file.exists():
                return state_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass
        return None

    def _fire_changed(self) -> None:
        """Invoke on_profile_changed callback if set."""
        if self._on_profile_changed and self._active is not None:
            try:
                self._on_profile_changed(self._active)
            except Exception as exc:
                logger.error("ProfileManager: on_profile_changed callback error: %s", exc)
