"""Mod installation from archives and folders."""

import hashlib
import logging
import shutil
import zipfile
from pathlib import Path
from typing import Optional
from uuid import uuid4

from ..config import ConfigManager
from ..models import Mod

logger = logging.getLogger(__name__)


class ModInstaller:
    """Handles installation of mods from various sources."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize the mod installer.

        Args:
            config_manager: Application configuration manager.
        """
        self.config_manager = config_manager

    def install_from_zip(
        self,
        archive_path: Path,
        name: Optional[str] = None,
        root_folder: Optional[str] = None,
    ) -> Mod:
        """Install a mod from a ZIP archive.

        Args:
            archive_path: Path to the ZIP file.
            name: Mod name (defaults to archive filename).
            root_folder: Folder within archive that contains mod files.
                        If None, attempts auto-detection.

        Returns:
            Newly created Mod instance.

        Raises:
            ValueError: If archive is invalid or mod structure cannot be determined.
        """
        if not archive_path.exists():
            raise ValueError(f"Archive not found: {archive_path}")

        if not zipfile.is_zipfile(archive_path):
            raise ValueError(f"Not a valid ZIP file: {archive_path}")

        # Determine mod name
        if name is None:
            name = archive_path.stem

        # Create staging directory for this mod
        mod_id = uuid4()
        config = self.config_manager.get()
        staging_path = config.staging_directory / str(mod_id)
        staging_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Installing mod '{name}' from {archive_path}")

        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                # Get list of files in archive
                file_list = zf.namelist()

                # Detect root folder if not specified
                if root_folder is None:
                    root_folder = self._detect_root_folder(file_list)

                # Extract files
                extracted_files = []
                for file_name in file_list:
                    if root_folder and not file_name.startswith(root_folder):
                        continue

                    # Calculate target path (strip root folder if present)
                    if root_folder:
                        target_name = file_name[len(root_folder) :].lstrip("/")
                    else:
                        target_name = file_name

                    if not target_name or target_name.endswith("/"):
                        continue

                    target_path = staging_path / target_name
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    with zf.open(file_name) as source:
                        with open(target_path, "wb") as dest:
                            shutil.copyfileobj(source, dest)

                    extracted_files.append(Path(target_name))

                logger.info(f"Extracted {len(extracted_files)} files")

            # Calculate checksum
            checksum = self._calculate_checksum(archive_path)

            # Optionally copy archive to downloads
            archive_copy = None
            if config.keep_archives:
                archive_copy = config.downloads_directory / archive_path.name
                archive_copy.parent.mkdir(parents=True, exist_ok=True)
                if not archive_copy.exists():
                    shutil.copy2(archive_path, archive_copy)

            # Create Mod instance
            mod = Mod(
                id=mod_id,
                name=name,
                staging_path=staging_path,
                deployed_files=[],
                archive_path=archive_copy,
                archive_checksum=checksum,
            )

            logger.info(f"Successfully installed mod '{name}' ({mod_id})")
            return mod

        except Exception as e:
            # Cleanup on failure
            if staging_path.exists():
                shutil.rmtree(staging_path)
            logger.error(f"Failed to install mod: {e}")
            raise

    def install_from_folder(
        self,
        source_folder: Path,
        name: Optional[str] = None,
        copy: bool = True,
    ) -> Mod:
        """Install a mod from an existing folder.

        Args:
            source_folder: Path to folder containing mod files.
            name: Mod name (defaults to folder name).
            copy: If True, copy files. If False, just reference them.

        Returns:
            Newly created Mod instance.

        Raises:
            ValueError: If source folder is invalid.
        """
        if not source_folder.exists():
            raise ValueError(f"Source folder not found: {source_folder}")

        if not source_folder.is_dir():
            raise ValueError(f"Not a directory: {source_folder}")

        # Determine mod name
        if name is None:
            name = source_folder.name

        # Create staging directory
        mod_id = uuid4()
        config = self.config_manager.get()
        staging_path = config.staging_directory / str(mod_id)

        logger.info(f"Installing mod '{name}' from folder {source_folder}")

        try:
            if copy:
                # Copy entire folder
                shutil.copytree(source_folder, staging_path)
                logger.info(f"Copied folder to {staging_path}")
            else:
                # Create staging directory but reference original
                staging_path.mkdir(parents=True, exist_ok=True)
                # Could implement symlinks here if needed
                shutil.copytree(source_folder, staging_path)

            # Create Mod instance
            mod = Mod(
                id=mod_id,
                name=name,
                staging_path=staging_path,
                deployed_files=[],
                source=str(source_folder),
            )

            logger.info(f"Successfully installed mod '{name}' ({mod_id})")
            return mod

        except Exception as e:
            # Cleanup on failure
            if staging_path.exists():
                shutil.rmtree(staging_path)
            logger.error(f"Failed to install mod: {e}")
            raise

    def uninstall(self, mod: Mod, remove_archive: bool = False) -> None:
        """Uninstall a mod, removing its staging directory.

        Args:
            mod: Mod to uninstall.
            remove_archive: If True, also delete the archive file.
        """
        logger.info(f"Uninstalling mod '{mod.name}' ({mod.id})")

        # Remove staging directory
        if mod.staging_path.exists():
            shutil.rmtree(mod.staging_path)
            logger.debug(f"Removed staging directory: {mod.staging_path}")

        # Optionally remove archive
        if remove_archive and mod.archive_path and mod.archive_path.exists():
            mod.archive_path.unlink()
            logger.debug(f"Removed archive: {mod.archive_path}")

    @staticmethod
    def _detect_root_folder(file_list: list[str]) -> Optional[str]:
        """Detect the root folder in an archive containing mod files.

        Looks for common MHW mod structure (e.g., nativePC folder).

        Args:
            file_list: List of file paths in the archive.

        Returns:
            Root folder path if detected, None if files are at archive root.
        """
        # Look for nativePC folder (common in MHW mods)
        for file_path in file_list:
            if "nativePC/" in file_path or "nativePC\\" in file_path:
                # Find the parent of nativePC
                parts = file_path.replace("\\", "/").split("/")
                if "nativePC" in parts:
                    idx = parts.index("nativePC")
                    if idx > 0:
                        # There's a root folder before nativePC
                        return "/".join(parts[:idx]) + "/"
                    else:
                        # nativePC is at root
                        return None

        # Check if all files are in a single top-level directory
        top_level_dirs = set()
        for file_path in file_list:
            parts = file_path.replace("\\", "/").split("/")
            if len(parts) > 1:
                top_level_dirs.add(parts[0])

        if len(top_level_dirs) == 1:
            # All files in one top-level directory
            return list(top_level_dirs)[0] + "/"

        # Files are at root level
        return None

    @staticmethod
    def _calculate_checksum(file_path: Path) -> str:
        """Calculate SHA256 checksum of a file.

        Args:
            file_path: Path to file.

        Returns:
            Hex digest of checksum.
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()
