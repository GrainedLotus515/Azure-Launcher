"""Game installation detection and validation."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class GameDiscovery:
    """Handles detection and validation of MHW installation."""

    # Common Steam library paths on Linux
    LINUX_STEAM_PATHS = [
        Path.home() / ".local/share/Steam/steamapps/common/Monster Hunter World",
        Path.home() / ".steam/steam/steamapps/common/Monster Hunter World",
        Path.home()
        / ".var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/Monster Hunter World",  # Flatpak
    ]

    # Expected subdirectories in MHW installation
    EXPECTED_DIRS = ["nativePC"]
    EXPECTED_FILES = ["MonsterHunterWorld.exe"]

    @classmethod
    def auto_detect(cls) -> Optional[Path]:
        """Attempt to auto-detect MHW installation directory.

        Returns:
            Path to MHW directory if found, None otherwise.
        """
        # First try known paths
        for steam_path in cls.LINUX_STEAM_PATHS:
            if cls.validate_game_directory(steam_path):
                logger.info(f"Auto-detected MHW installation at: {steam_path}")
                return steam_path

        # If not found, search for MonsterHunterWorld.exe
        logger.info("Standard paths not found, searching for executable...")
        search_paths = cls.find_all_installations()
        if search_paths:
            logger.info(f"Auto-detected MHW installation at: {search_paths[0]}")
            return search_paths[0]

        logger.warning("Could not auto-detect MHW installation")
        return None

    @classmethod
    def validate_game_directory(cls, path: Path) -> bool:
        """Validate that a path is a valid MHW installation.

        Args:
            path: Path to validate.

        Returns:
            True if path appears to be a valid MHW installation.
        """
        if not path.exists():
            logger.debug(f"Path does not exist: {path}")
            return False

        if not path.is_dir():
            logger.debug(f"Path is not a directory: {path}")
            return False

        # Check for expected subdirectories
        for expected_dir in cls.EXPECTED_DIRS:
            dir_path = path / expected_dir
            if not dir_path.exists() or not dir_path.is_dir():
                logger.debug(f"Missing expected directory: {expected_dir}")
                return False

        # On Linux, the .exe might not exist (Proton), so make this optional
        exe_exists = any((path / exe).exists() for exe in cls.EXPECTED_FILES)
        if not exe_exists:
            logger.debug("MonsterHunterWorld.exe not found (may be normal on Linux/Proton)")

        logger.info(f"Validated MHW directory: {path}")
        return True

    @classmethod
    def get_native_pc_path(cls, game_dir: Path) -> Path:
        """Get the nativePC directory path.

        This is where most mods are installed.

        Args:
            game_dir: Root MHW installation directory.

        Returns:
            Path to nativePC directory.
        """
        return game_dir / "nativePC"

    @classmethod
    def search_steam_libraries(cls) -> list[Path]:
        """Search for additional Steam library folders.

        Parses Steam's libraryfolders.vdf to find all Steam library locations.

        Returns:
            List of potential MHW installation paths.
        """
        potential_paths = []

        # Default Steam config locations
        steam_config_paths = [
            Path.home() / ".local/share/Steam/config/libraryfolders.vdf",
            Path.home() / ".steam/steam/config/libraryfolders.vdf",
        ]

        for config_path in steam_config_paths:
            if not config_path.exists():
                continue

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Simple VDF parsing - look for "path" entries
                for line in content.split("\n"):
                    if '"path"' in line.lower():
                        # Extract path between quotes
                        parts = line.split('"')
                        if len(parts) >= 4:
                            library_path = Path(parts[3])
                            mhw_path = library_path / "steamapps/common/Monster Hunter World"
                            if mhw_path.exists():
                                potential_paths.append(mhw_path)
            except Exception as e:
                logger.warning(f"Error parsing Steam library folders: {e}")

        return potential_paths

    @classmethod
    def find_all_installations(cls) -> list[Path]:
        """Find all possible MHW installations.

        Returns:
            List of validated MHW installation paths.
        """
        candidates = list(cls.LINUX_STEAM_PATHS)
        candidates.extend(cls.search_steam_libraries())

        # Also search by executable file
        candidates.extend(cls._search_by_executable())

        # Deduplicate and validate
        valid_paths = []
        seen = set()

        for path in candidates:
            if path in seen:
                continue
            seen.add(path)

            if cls.validate_game_directory(path):
                valid_paths.append(path)

        return valid_paths

    @classmethod
    def _search_by_executable(cls) -> list[Path]:
        """Search for MHW by finding the executable file.

        Returns:
            List of potential MHW installation directories.
        """
        import subprocess

        potential_paths = []

        # Search common Steam locations for MonsterHunterWorld.exe
        search_dirs = [
            Path.home() / ".local/share/Steam/steamapps/common",
            Path.home() / ".steam/steam/steamapps/common",
        ]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            try:
                # Use find command to search for the executable
                result = subprocess.run(
                    ["find", str(search_dir), "-name", "MonsterHunterWorld.exe", "-type", "f"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0 and result.stdout:
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            exe_path = Path(line)
                            # The parent directory is the game directory
                            game_dir = exe_path.parent
                            potential_paths.append(game_dir)
                            logger.debug(f"Found executable at: {exe_path}")

            except (subprocess.TimeoutExpired, Exception) as e:
                logger.debug(f"Error searching for executable in {search_dir}: {e}")

        return potential_paths
