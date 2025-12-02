"""Mod repository - manages the collection of installed mods."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from ..config import get_data_dir
from ..models import Mod

logger = logging.getLogger(__name__)


class ModRepository:
    """Manages the collection of installed mods."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """Initialize the mod repository.

        Args:
            data_dir: Directory to store mod metadata. If None, uses default.
        """
        self.data_dir = data_dir or get_data_dir()
        self.mods_db_file = self.data_dir / "mods.json"
        self._mods: dict[UUID, Mod] = {}
        self._loaded = False

    def load(self) -> None:
        """Load mods from persistent storage."""
        if self._loaded:
            return

        if not self.mods_db_file.exists():
            logger.info("No existing mods database found, starting fresh")
            self._mods = {}
            self._loaded = True
            return

        try:
            with open(self.mods_db_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._mods = {}
            for mod_data in data.get("mods", []):
                # Convert path strings back to Path objects
                if "staging_path" in mod_data:
                    mod_data["staging_path"] = Path(mod_data["staging_path"])
                if "archive_path" in mod_data and mod_data["archive_path"]:
                    mod_data["archive_path"] = Path(mod_data["archive_path"])
                if "deployed_files" in mod_data:
                    mod_data["deployed_files"] = [Path(p) for p in mod_data["deployed_files"]]

                # Convert datetime strings back to datetime objects (Nexus metadata)
                if "nexus_uploaded_at" in mod_data and mod_data["nexus_uploaded_at"]:
                    try:
                        mod_data["nexus_uploaded_at"] = datetime.fromisoformat(
                            mod_data["nexus_uploaded_at"]
                        )
                    except (ValueError, TypeError):
                        mod_data["nexus_uploaded_at"] = None

                # Ensure backwards compatibility - new fields default to None
                # These fields may not exist in older databases
                mod_data.setdefault("nexus_mod_id", None)
                mod_data.setdefault("nexus_file_id", None)
                mod_data.setdefault("nexus_uploaded_at", None)

                mod = Mod(**mod_data)
                self._mods[mod.id] = mod

            logger.info(f"Loaded {len(self._mods)} mods from database")
            self._loaded = True

        except Exception as e:
            logger.error(f"Error loading mods database: {e}")
            self._mods = {}
            self._loaded = True

    def save(self) -> None:
        """Save mods to persistent storage."""
        if not self._loaded:
            logger.warning("Attempting to save before loading, loading first")
            self.load()

        try:
            data = {"mods": [mod.model_dump(mode="json") for mod in self._mods.values()]}

            self.data_dir.mkdir(parents=True, exist_ok=True)

            with open(self.mods_db_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._mods)} mods to database")

        except Exception as e:
            logger.error(f"Error saving mods database: {e}")

    def add(self, mod: Mod) -> None:
        """Add a new mod to the repository.

        Args:
            mod: Mod to add.
        """
        if not self._loaded:
            self.load()

        self._mods[mod.id] = mod
        self.save()
        logger.info(f"Added mod: {mod.name} ({mod.id})")

    def get(self, mod_id: UUID) -> Optional[Mod]:
        """Get a mod by ID.

        Args:
            mod_id: Mod UUID.

        Returns:
            Mod if found, None otherwise.
        """
        if not self._loaded:
            self.load()

        return self._mods.get(mod_id)

    def get_all(self) -> list[Mod]:
        """Get all mods.

        Returns:
            List of all mods.
        """
        if not self._loaded:
            self.load()

        return list(self._mods.values())

    def remove(self, mod_id: UUID) -> bool:
        """Remove a mod from the repository.

        Args:
            mod_id: Mod UUID.

        Returns:
            True if mod was removed, False if not found.
        """
        if not self._loaded:
            self.load()

        if mod_id in self._mods:
            mod = self._mods[mod_id]
            del self._mods[mod_id]
            self.save()
            logger.info(f"Removed mod: {mod.name} ({mod_id})")
            return True

        logger.warning(f"Attempted to remove non-existent mod: {mod_id}")
        return False

    def update(self, mod: Mod) -> None:
        """Update an existing mod.

        Args:
            mod: Mod with updated data.
        """
        if not self._loaded:
            self.load()

        if mod.id in self._mods:
            self._mods[mod.id] = mod
            self.save()
            logger.debug(f"Updated mod: {mod.name} ({mod.id})")
        else:
            logger.warning(f"Attempted to update non-existent mod: {mod.id}")

    def search(self, query: str) -> list[Mod]:
        """Search mods by name, author, or tags.

        Args:
            query: Search query string.

        Returns:
            List of matching mods.
        """
        if not self._loaded:
            self.load()

        query_lower = query.lower()
        results = []

        for mod in self._mods.values():
            if (
                query_lower in mod.name.lower()
                or (mod.author and query_lower in mod.author.lower())
                or any(query_lower in tag.lower() for tag in mod.tags)
            ):
                results.append(mod)

        return results

    def get_by_name(self, name: str) -> Optional[Mod]:
        """Get a mod by exact name match.

        Args:
            name: Mod name.

        Returns:
            Mod if found, None otherwise.
        """
        if not self._loaded:
            self.load()

        for mod in self._mods.values():
            if mod.name == name:
                return mod

        return None
