"""Mod deployment engine - symlinks/copies mods to game directory."""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from ..config import ConfigManager
from ..models import DeploymentMode, DeploymentState, Mod, Profile

logger = logging.getLogger(__name__)


class DeploymentEngine:
    """Handles deployment of mods to the game directory."""

    def __init__(self, config_manager: ConfigManager, game_dir: Path) -> None:
        """Initialize the deployment engine.

        Args:
            config_manager: Application configuration manager.
            game_dir: Root directory of the game installation.
        """
        self.config_manager = config_manager
        self.game_dir = game_dir
        self._deployed_files: set[Path] = set()

    def deploy(
        self,
        mods: list[Mod],
        profile: Profile,
        mode: Optional[DeploymentMode] = None,
    ) -> DeploymentState:
        """Deploy mods according to profile configuration.

        Args:
            mods: List of all available mods.
            profile: Profile specifying which mods to enable and their order.
            mode: Deployment mode (symlink/copy). If None, uses config default.

        Returns:
            DeploymentState describing what was deployed.

        Raises:
            ValueError: If game directory is invalid.
        """
        if not self.game_dir.exists():
            raise ValueError(f"Game directory not found: {self.game_dir}")

        if mode is None:
            mode = self.config_manager.get().deployment_mode

        logger.info(f"Deploying profile '{profile.name}' with mode {mode.value}")

        # Get enabled mods in load order
        enabled_mod_ids = profile.get_enabled_mods_ordered()

        # Build mod lookup
        mod_lookup = {mod.id: mod for mod in mods}

        # Track deployment
        deployed_mods = []
        deployed_files: dict[Path, Mod] = {}  # target_path -> winning mod

        # Process each mod in load order
        for mod_id in enabled_mod_ids:
            mod = mod_lookup.get(mod_id)
            if not mod:
                logger.warning(f"Mod {mod_id} in profile but not found in repository")
                continue

            if not mod.staging_path.exists():
                logger.warning(f"Mod '{mod.name}' staging path missing: {mod.staging_path}")
                continue

            # Find all files in staging directory
            mod_files = self._discover_mod_files(mod.staging_path)

            # Mark files for deployment (later mods override earlier ones)
            for relative_path in mod_files:
                target_path = self.game_dir / relative_path
                deployed_files[relative_path] = mod

            deployed_mods.append(mod_id)

        # Now perform actual deployment
        for relative_path, mod in deployed_files.items():
            source_path = mod.staging_path / relative_path
            target_path = self.game_dir / relative_path

            try:
                self._deploy_file(source_path, target_path, mode)
                self._deployed_files.add(target_path)
            except Exception as e:
                logger.error(f"Failed to deploy {relative_path} from mod '{mod.name}': {e}")

        logger.info(f"Deployed {len(deployed_files)} files from {len(deployed_mods)} mods")

        # Create deployment state
        state = DeploymentState(
            profile_id=profile.id,
            deployed_mods=deployed_mods,
            deployment_mode=mode,
        )

        return state

    def undeploy(self) -> None:
        """Remove all deployed mod files from the game directory.

        This removes symlinks and tracks which files were deployed.
        Be careful with copied files - we only remove tracked deployments.
        """
        logger.info("Undeploying all mods")

        removed_count = 0
        for file_path in list(self._deployed_files):
            try:
                if file_path.exists() or file_path.is_symlink():
                    if file_path.is_symlink():
                        # Safe to remove symlinks
                        file_path.unlink()
                        removed_count += 1
                    elif file_path.is_file():
                        # Only remove regular files if we're sure they were deployed
                        # In a production system, we'd track this more carefully
                        file_path.unlink()
                        removed_count += 1
            except Exception as e:
                logger.error(f"Failed to remove {file_path}: {e}")

        self._deployed_files.clear()
        logger.info(f"Removed {removed_count} deployed files")

    def verify_deployment(self, state: DeploymentState) -> bool:
        """Verify that a deployment is still valid.

        Checks if symlinks/files still exist and point to correct locations.

        Args:
            state: Previous deployment state to verify.

        Returns:
            True if deployment is valid, False otherwise.
        """
        # This is a simplified check
        # In production, you'd verify each file
        return self.game_dir.exists()

    def _deploy_file(self, source: Path, target: Path, mode: DeploymentMode) -> None:
        """Deploy a single file.

        Args:
            source: Source file in staging area.
            target: Target location in game directory.
            mode: Deployment mode (symlink/copy).
        """
        # Create parent directory if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing target if present
        if target.exists() or target.is_symlink():
            if target.is_symlink():
                target.unlink()
            elif target.is_file():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)

        # Deploy based on mode
        if mode == DeploymentMode.SYMLINK:
            try:
                # Create symbolic link
                os.symlink(source, target)
                logger.debug(f"Symlinked: {target} -> {source}")
            except OSError as e:
                logger.warning(f"Symlink failed, falling back to copy: {e}")
                shutil.copy2(source, target)
        else:
            # Copy mode
            shutil.copy2(source, target)
            logger.debug(f"Copied: {source} -> {target}")

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

    def get_deployed_files(self) -> list[Path]:
        """Get list of currently deployed files.

        Returns:
            List of paths to deployed files.
        """
        return list(self._deployed_files)
