"""NXM protocol handler registration for Linux."""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class NXMProtocolHandler:
    """Handles NXM protocol registration on Linux."""

    @staticmethod
    def is_registered() -> bool:
        """Check if NXM protocol is registered.

        Returns:
            True if registered.
        """
        try:
            result = subprocess.run(
                ["xdg-mime", "query", "default", "x-scheme-handler/nxm"],
                capture_output=True,
                text=True,
                check=False,
            )
            return "mhw-mod-manager" in result.stdout.lower()
        except Exception as e:
            logger.warning(f"Failed to check NXM registration: {e}")
            return False

    @staticmethod
    def register() -> bool:
        """Register NXM protocol handler.

        Returns:
            True if successful.
        """
        try:
            # Get the executable path
            if getattr(sys, "frozen", False):
                # Running as bundled executable
                exe_path = sys.executable
            else:
                # Running as script - use entry point
                exe_path = shutil.which("mhw-mod-manager")
                if not exe_path:
                    logger.error("mhw-mod-manager executable not found in PATH")
                    return False

            # Create .desktop file
            desktop_file_content = f"""[Desktop Entry]
Type=Application
Name=MHW Mod Manager
Comment=Monster Hunter World Mod Manager
Exec={exe_path} --nxm-link %u
Icon=mhw-mod-manager
Terminal=false
Categories=Game;Utility;
MimeType=x-scheme-handler/nxm;
NoDisplay=true
"""

            # Determine desktop file location
            xdg_data_home = os.environ.get("XDG_DATA_HOME")
            if not xdg_data_home:
                xdg_data_home = Path.home() / ".local" / "share"
            else:
                xdg_data_home = Path(xdg_data_home)

            applications_dir = xdg_data_home / "applications"
            applications_dir.mkdir(parents=True, exist_ok=True)

            desktop_file_path = applications_dir / "mhw-mod-manager-nxm.desktop"

            # Write desktop file
            with open(desktop_file_path, "w") as f:
                f.write(desktop_file_content)

            # Make it executable
            desktop_file_path.chmod(0o755)

            # Register with xdg-mime
            subprocess.run(
                ["xdg-mime", "default", "mhw-mod-manager-nxm.desktop", "x-scheme-handler/nxm"],
                check=True,
            )

            # Update desktop database
            subprocess.run(
                ["update-desktop-database", str(applications_dir)],
                check=False,  # Don't fail if this doesn't work
            )

            logger.info("NXM protocol handler registered successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to register NXM protocol handler: {e}")
            return False

    @staticmethod
    def unregister() -> bool:
        """Unregister NXM protocol handler.

        Returns:
            True if successful.
        """
        try:
            # Remove desktop file
            xdg_data_home = os.environ.get("XDG_DATA_HOME")
            if not xdg_data_home:
                xdg_data_home = Path.home() / ".local" / "share"
            else:
                xdg_data_home = Path(xdg_data_home)

            desktop_file_path = xdg_data_home / "applications" / "mhw-mod-manager-nxm.desktop"
            if desktop_file_path.exists():
                desktop_file_path.unlink()

            logger.info("NXM protocol handler unregistered")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister NXM protocol handler: {e}")
            return False


def parse_nxm_link(nxm_url: str) -> Optional[dict[str, str]]:
    """Parse an NXM protocol link.

    Args:
        nxm_url: NXM URL string.

    Returns:
        Dictionary with parsed components or None if invalid.

    Example:
        >>> parse_nxm_link("nxm://monsterhunterworld/mods/123/files/456?key=abc&expires=123")
        {'game': 'monsterhunterworld', 'mod_id': '123', 'file_id': '456', 'key': 'abc', ...}
    """
    from urllib.parse import parse_qs, urlparse

    try:
        parsed = urlparse(nxm_url)

        if parsed.scheme != "nxm":
            return None

        # Parse path: /mods/{mod_id}/files/{file_id}
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 4 or path_parts[0] != "mods" or path_parts[2] != "files":
            return None

        # Parse query parameters
        query_params = parse_qs(parsed.query)

        result = {
            "game": parsed.netloc,
            "mod_id": path_parts[1],
            "file_id": path_parts[3],
            "key": query_params.get("key", [None])[0],
            "expires": query_params.get("expires", [None])[0],
            "user_id": query_params.get("user_id", [None])[0],
        }

        return result

    except Exception as e:
        logger.error(f"Failed to parse NXM link: {e}")
        return None
