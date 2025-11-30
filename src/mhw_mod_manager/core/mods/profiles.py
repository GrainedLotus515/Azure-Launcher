"""Profile management for organizing mod configurations."""

import json
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from ..config import get_data_dir
from ..models import Profile, ProfileModEntry

logger = logging.getLogger(__name__)


class ProfileManager:
    """Manages mod profiles."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """Initialize the profile manager.

        Args:
            data_dir: Directory to store profile data. If None, uses default.
        """
        self.data_dir = data_dir or get_data_dir()
        self.profiles_file = self.data_dir / "profiles.json"
        self._profiles: dict[UUID, Profile] = {}
        self._loaded = False

    def load(self) -> None:
        """Load profiles from persistent storage."""
        if self._loaded:
            return

        if not self.profiles_file.exists():
            logger.info("No existing profiles found, creating default profile")
            self._create_default_profile()
            self._loaded = True
            return

        try:
            with open(self.profiles_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._profiles = {}
            for profile_data in data.get("profiles", []):
                profile = Profile(**profile_data)
                self._profiles[profile.id] = profile

            logger.info(f"Loaded {len(self._profiles)} profiles")
            self._loaded = True

        except Exception as e:
            logger.error(f"Error loading profiles: {e}")
            self._create_default_profile()
            self._loaded = True

    def save(self) -> None:
        """Save profiles to persistent storage."""
        if not self._loaded:
            logger.warning("Attempting to save before loading, loading first")
            self.load()

        try:
            data = {
                "profiles": [profile.model_dump(mode="json") for profile in self._profiles.values()]
            }

            self.data_dir.mkdir(parents=True, exist_ok=True)

            with open(self.profiles_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._profiles)} profiles")

        except Exception as e:
            logger.error(f"Error saving profiles: {e}")

    def create(self, name: str, description: Optional[str] = None) -> Profile:
        """Create a new profile.

        Args:
            name: Profile name.
            description: Optional description.

        Returns:
            Newly created profile.
        """
        if not self._loaded:
            self.load()

        profile = Profile(name=name, description=description)
        self._profiles[profile.id] = profile
        self.save()

        logger.info(f"Created profile: {name} ({profile.id})")
        return profile

    def get(self, profile_id: UUID) -> Optional[Profile]:
        """Get a profile by ID.

        Args:
            profile_id: Profile UUID.

        Returns:
            Profile if found, None otherwise.
        """
        if not self._loaded:
            self.load()

        return self._profiles.get(profile_id)

    def get_all(self) -> list[Profile]:
        """Get all profiles.

        Returns:
            List of all profiles.
        """
        if not self._loaded:
            self.load()

        return list(self._profiles.values())

    def update(self, profile: Profile) -> None:
        """Update an existing profile.

        Args:
            profile: Profile with updated data.
        """
        if not self._loaded:
            self.load()

        if profile.id in self._profiles:
            self._profiles[profile.id] = profile
            self.save()
            logger.debug(f"Updated profile: {profile.name} ({profile.id})")
        else:
            logger.warning(f"Attempted to update non-existent profile: {profile.id}")

    def delete(self, profile_id: UUID) -> bool:
        """Delete a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            True if deleted, False if not found.
        """
        if not self._loaded:
            self.load()

        if profile_id in self._profiles:
            profile = self._profiles[profile_id]
            del self._profiles[profile_id]
            self.save()
            logger.info(f"Deleted profile: {profile.name} ({profile_id})")
            return True

        logger.warning(f"Attempted to delete non-existent profile: {profile_id}")
        return False

    def rename(self, profile_id: UUID, new_name: str) -> bool:
        """Rename a profile.

        Args:
            profile_id: Profile UUID.
            new_name: New profile name.

        Returns:
            True if renamed, False if not found.
        """
        if not self._loaded:
            self.load()

        profile = self._profiles.get(profile_id)
        if profile:
            profile.name = new_name
            self.save()
            logger.info(f"Renamed profile {profile_id} to '{new_name}'")
            return True

        return False

    def get_default_profile(self) -> Profile:
        """Get the default profile, creating if necessary.

        Returns:
            Default profile.
        """
        if not self._loaded:
            self.load()

        # Look for a profile named "Default"
        for profile in self._profiles.values():
            if profile.name == "Default":
                return profile

        # Create default profile if not found
        return self._create_default_profile()

    def _create_default_profile(self) -> Profile:
        """Create the default profile.

        Returns:
            Newly created default profile.
        """
        profile = Profile(name="Default", description="Default mod configuration")
        self._profiles[profile.id] = profile
        self._loaded = True  # Mark as loaded before saving to avoid recursion
        self.save()
        return profile
