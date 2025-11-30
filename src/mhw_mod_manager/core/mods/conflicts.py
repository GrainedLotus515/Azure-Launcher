"""Conflict detection between mods."""

import logging
from pathlib import Path
from uuid import UUID

from ..models import ConflictReport, FileConflict, Mod, Profile

logger = logging.getLogger(__name__)


class ConflictDetector:
    """Detects file conflicts between mods."""

    def analyze(self, mods: list[Mod], profile: Profile) -> ConflictReport:
        """Analyze a profile for conflicts between enabled mods.

        Args:
            mods: List of all available mods.
            profile: Profile to analyze.

        Returns:
            ConflictReport detailing all conflicts.
        """
        logger.info(f"Analyzing conflicts for profile '{profile.name}'")

        # Get enabled mods in load order
        enabled_mod_ids = profile.get_enabled_mods_ordered()

        # Build mod lookup
        mod_lookup = {mod.id: mod for mod in mods}

        # Track which mods deploy to each file path
        file_to_mods: dict[Path, list[UUID]] = {}

        # Process each mod in load order
        for mod_id in enabled_mod_ids:
            mod = mod_lookup.get(mod_id)
            if not mod:
                logger.warning(f"Mod {mod_id} in profile but not found")
                continue

            if not mod.staging_path.exists():
                logger.warning(f"Mod '{mod.name}' staging path missing")
                continue

            # Find all files in this mod
            mod_files = self._discover_mod_files(mod.staging_path)

            # Track file deployments
            for relative_path in mod_files:
                if relative_path not in file_to_mods:
                    file_to_mods[relative_path] = []
                file_to_mods[relative_path].append(mod_id)

        # Identify conflicts (files deployed by multiple mods)
        conflicts = []
        for file_path, mod_ids in file_to_mods.items():
            if len(mod_ids) > 1:
                # Conflict detected
                # Winner is the last mod in load order (last in the list)
                conflict = FileConflict(
                    target_path=file_path,
                    conflicting_mods=mod_ids,
                    winner_mod_id=mod_ids[-1],
                )
                conflicts.append(conflict)

        logger.info(f"Found {len(conflicts)} file conflicts")

        return ConflictReport(
            profile_id=profile.id,
            conflicts=conflicts,
        )

    def _discover_mod_files(self, staging_path: Path) -> list[Path]:
        """Discover all files in a mod's staging directory.

        Args:
            staging_path: Path to mod's staging directory.

        Returns:
            List of relative paths to files.
        """
        files = []

        for item in staging_path.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(staging_path)
                files.append(relative_path)

        return files
